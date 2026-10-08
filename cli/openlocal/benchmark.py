"""Reproducible OpenAI-compatible streaming benchmark runner."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .doctor import Runner, _run

BENCHMARK_VERSION = "1.0"
WORKLOAD_ID = "openlocal-chat-v1"
PROMPT = "Explain in concise terms why reproducible benchmarks need fixed workloads and runtime settings."


class BenchmarkError(RuntimeError):
    """A benchmark could not produce a valid report."""


@dataclass(frozen=True)
class RequestMetrics:
    latency_seconds: float
    ttft_seconds: float
    mean_itl_seconds: float | None
    output_tokens: int
    token_count_source: str


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _sse_payloads(response: Iterable[bytes]) -> Iterable[dict[str, Any]]:
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            value = json.loads(data)
        except json.JSONDecodeError as exc:
            raise BenchmarkError("stream returned invalid JSON") from exc
        if isinstance(value, dict):
            yield value


def run_stream_request(
    base_url: str,
    model: str,
    max_tokens: int,
    timeout: float = 300,
    opener: Callable[..., Any] = urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> RequestMetrics:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0,
        "seed": 42,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = clock()
    content_times: list[float] = []
    usage_tokens: int | None = None
    try:
        with opener(request, timeout=timeout) as response:
            for event in _sse_payloads(response):
                usage = event.get("usage")
                if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
                    usage_tokens = usage["completion_tokens"]
                choices = event.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content") if isinstance(delta, dict) else None
                if content:
                    content_times.append(clock())
    except HTTPError as exc:
        raise BenchmarkError(f"benchmark endpoint returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise BenchmarkError(f"benchmark endpoint is unavailable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BenchmarkError("benchmark request timed out") from exc
    ended = clock()
    if not content_times:
        raise BenchmarkError("stream completed without output content")
    intervals = [later - earlier for earlier, later in pairwise(content_times)]
    output_tokens = usage_tokens if usage_tokens is not None else len(content_times)
    return RequestMetrics(
        latency_seconds=ended - started,
        ttft_seconds=content_times[0] - started,
        mean_itl_seconds=statistics.fmean(intervals) if intervals else None,
        output_tokens=output_tokens,
        token_count_source="api_usage" if usage_tokens is not None else "stream_chunk_fallback",
    )


def _gpu_sample(runner: Runner = _run) -> list[dict[str, float]]:
    result = runner(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    if result.returncode != 0:
        return []
    samples: list[dict[str, float]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            samples.append(
                {
                    "vram_used_mb": float(parts[0]),
                    "gpu_utilization_percent": float(parts[1]),
                }
            )
        except ValueError:
            continue
    return samples


def _monitor_gpu(
    stop: threading.Event, output: list[list[dict[str, float]]], runner: Runner
) -> None:
    while not stop.is_set():
        sample = _gpu_sample(runner)
        if sample:
            output.append(sample)
        stop.wait(0.25)


def run_level(
    base_url: str,
    model: str,
    concurrency: int,
    requests: int,
    max_tokens: int,
    request_fn: Callable[..., RequestMetrics] = run_stream_request,
    gpu_runner: Runner = _run,
) -> dict[str, Any]:
    gpu_samples: list[list[dict[str, float]]] = []
    stop = threading.Event()
    monitor = threading.Thread(
        target=_monitor_gpu, args=(stop, gpu_samples, gpu_runner), daemon=True
    )
    monitor.start()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(request_fn, base_url, model, max_tokens) for _ in range(requests)
            ]
            metrics = [future.result() for future in futures]
    finally:
        stop.set()
        monitor.join(timeout=2)
    wall_seconds = time.perf_counter() - started
    latencies = [item.latency_seconds for item in metrics]
    ttfts = [item.ttft_seconds for item in metrics]
    itls = [item.mean_itl_seconds for item in metrics if item.mean_itl_seconds is not None]
    total_tokens = sum(item.output_tokens for item in metrics)
    flat_gpu = [device for sample in gpu_samples for device in sample]
    return {
        "concurrency": concurrency,
        "requests": requests,
        "wall_seconds": round(wall_seconds, 6),
        "output_tokens": total_tokens,
        "output_tokens_per_second": round(total_tokens / wall_seconds, 3) if wall_seconds else None,
        "requests_per_second": round(requests / wall_seconds, 3) if wall_seconds else None,
        "ttft_seconds": {
            "p50": percentile(ttfts, 0.50),
            "p95": percentile(ttfts, 0.95),
        },
        "itl_seconds": {"p50": percentile(itls, 0.50), "p95": percentile(itls, 0.95)},
        "latency_seconds": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
        },
        "vram_used_mb": {
            "peak": max((item["vram_used_mb"] for item in flat_gpu), default=None),
            "mean": statistics.fmean(item["vram_used_mb"] for item in flat_gpu)
            if flat_gpu
            else None,
        },
        "gpu_utilization_percent": {
            "peak": max((item["gpu_utilization_percent"] for item in flat_gpu), default=None),
            "mean": statistics.fmean(item["gpu_utilization_percent"] for item in flat_gpu)
            if flat_gpu
            else None,
        },
        "token_count_sources": sorted({item.token_count_source for item in metrics}),
    }


def sanitize_hardware(snapshot: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "os",
        "architecture",
        "cpu",
        "ram_gb",
        "gpu",
        "driver",
        "cuda",
        "runtime_path",
    )
    return {key: snapshot.get(key) for key in allowed}


def run_benchmark(
    snapshot: dict[str, Any],
    model: str,
    runtime: dict[str, Any],
    concurrency_levels: list[int],
    requests_per_level: int,
    max_tokens: int,
    base_url: str = "http://127.0.0.1:8000/v1",
    level_fn: Callable[..., dict[str, Any]] = run_level,
) -> dict[str, Any]:
    if not concurrency_levels or any(value <= 0 for value in concurrency_levels):
        raise BenchmarkError("concurrency levels must be positive")
    created = datetime.now(UTC).isoformat()
    level_fn(base_url, model, 1, 1, max_tokens)
    results = [
        level_fn(base_url, model, level, max(requests_per_level, level), max_tokens)
        for level in concurrency_levels
    ]
    valid = [item for item in results if item.get("output_tokens_per_second") is not None]
    recommended = None
    if valid:
        recommended = max(
            valid,
            key=lambda item: (
                item["output_tokens_per_second"] / max(item["ttft_seconds"]["p95"] or 0.001, 0.001)
            ),
        )["concurrency"]
    return {
        "schema_version": "1.0",
        "benchmark_version": BENCHMARK_VERSION,
        "created_at": created,
        "hardware": sanitize_hardware(snapshot),
        "model": {"id": model},
        "runtime": runtime,
        "workload": {
            "id": WORKLOAD_ID,
            "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
            "prompt_content_included": False,
            "temperature": 0,
            "seed": 42,
            "max_tokens": max_tokens,
            "requests_per_level": requests_per_level,
        },
        "results": results,
        "recommended_concurrency": recommended,
        "privacy": {
            "prompt_content": False,
            "hostname": False,
            "username": False,
            "ip_address": False,
        },
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "OpenLocal Benchmark",
        "",
        f"Model                 {report['model']['id']}",
        "",
        "Concurrency   tok/s   TTFT p50   Latency p95",
    ]
    for result in report["results"]:
        lines.append(
            f"{result['concurrency']:<13} {result['output_tokens_per_second']:<7} "
            f"{result['ttft_seconds']['p50']:.3f}s     {result['latency_seconds']['p95']:.3f}s"
        )
    lines.extend(["", f"Recommended concurrency: {report['recommended_concurrency']}"])
    return "\n".join(lines)


def validate_submission(report: dict[str, Any]) -> None:
    forbidden = {"hostname", "username", "ip", "ip_address", "prompt", "prompt_content"}

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.lower()
                if lowered in forbidden and child is not False and child is not None:
                    raise BenchmarkError(f"submission contains forbidden field {path}{key}")
                walk(child, f"{path}{key}.")
        elif isinstance(value, list):
            for child in value:
                walk(child, path)

    walk(report)
    privacy = report.get("privacy")
    if not isinstance(privacy, dict) or any(
        privacy.get(key) is not False
        for key in ("prompt_content", "hostname", "username", "ip_address")
    ):
        raise BenchmarkError("submission privacy declaration is missing or unsafe")


def submit_report(
    url: str,
    report: dict[str, Any],
    timeout: float = 30,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    validate_submission(report)
    request = Request(
        url,
        data=json.dumps(report, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise BenchmarkError(f"submission endpoint returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise BenchmarkError(f"submission endpoint is unavailable: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BenchmarkError(f"invalid submission response: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkError("submission endpoint returned non-object JSON")
    return value

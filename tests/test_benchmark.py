from __future__ import annotations

import json
import unittest

from openlocal.benchmark import (
    BenchmarkError,
    RequestMetrics,
    percentile,
    run_benchmark,
    run_level,
    run_stream_request,
    submit_report,
    validate_submission,
)
from openlocal.doctor import CommandResult


class StreamResponse:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return iter(self.lines)

    def __exit__(self, *args):
        return False


class JsonResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.value).encode("utf-8")


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 0.1
        return self.value


class BenchmarkTests(unittest.TestCase):
    def test_percentile_interpolates(self):
        self.assertEqual(percentile([1, 2, 3], 0.5), 2)
        self.assertAlmostEqual(percentile([1, 3], 0.95), 2.9)
        self.assertIsNone(percentile([], 0.5))

    def test_stream_metrics_use_api_token_count(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"a"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"b"}}]}\n',
            b'data: {"choices":[],"usage":{"completion_tokens":7}}\n',
            b"data: [DONE]\n",
        ]
        result = run_stream_request(
            "http://example/v1",
            "model",
            8,
            opener=lambda request, timeout: StreamResponse(lines),
            clock=Clock(),
        )
        self.assertEqual(result.output_tokens, 7)
        self.assertEqual(result.token_count_source, "api_usage")
        self.assertAlmostEqual(result.ttft_seconds, 0.1)

    def test_level_aggregates_required_metrics(self):
        def request_fn(base_url, model, max_tokens):
            return RequestMetrics(1.0, 0.2, 0.05, 10, "api_usage")

        result = run_level(
            "http://example/v1",
            "model",
            concurrency=2,
            requests=4,
            max_tokens=8,
            request_fn=request_fn,
            gpu_runner=lambda command: CommandResult(0, "1024, 75"),
        )
        self.assertEqual(result["output_tokens"], 40)
        self.assertEqual(result["ttft_seconds"]["p50"], 0.2)
        self.assertEqual(result["vram_used_mb"]["peak"], 1024)

    def test_report_excludes_local_identity_and_prompt(self):
        calls = []

        def level_fn(base_url, model, concurrency, requests, max_tokens):
            calls.append(concurrency)
            return {
                "concurrency": concurrency,
                "requests": requests,
                "output_tokens_per_second": float(concurrency * 10),
                "ttft_seconds": {"p50": 0.2, "p95": float(concurrency)},
                "latency_seconds": {"p50": 1.0, "p95": 1.0},
            }

        snapshot = {
            "os": {"name": "Ubuntu"},
            "architecture": "x86_64",
            "cpu": "CPU",
            "ram_gb": 64,
            "gpu": {"count": 1},
            "driver": "1",
            "cuda": "2",
            "runtime_path": "docker-linux",
            "disk": {"path": "/home/alice/private"},
        }
        report = run_benchmark(snapshot, "model", {}, [1, 2], 2, 8, level_fn=level_fn)
        self.assertEqual(calls, [1, 1, 2])
        self.assertNotIn("disk", report["hardware"])
        self.assertNotIn("prompt", report["workload"])
        validate_submission(report)

    def test_privacy_validation_rejects_identity(self):
        report = {
            "hostname": "private-host",
            "privacy": {
                "prompt_content": False,
                "hostname": False,
                "username": False,
                "ip_address": False,
            },
        }
        with self.assertRaisesRegex(BenchmarkError, "hostname"):
            validate_submission(report)

    def test_submit_posts_validated_json(self):
        report = {
            "privacy": {
                "prompt_content": False,
                "hostname": False,
                "username": False,
                "ip_address": False,
            },
        }
        captured = {}

        def opener(request, timeout):
            captured["method"] = request.method
            captured["body"] = json.loads(request.data)
            return JsonResponse({"id": "9F32A"})

        response = submit_report("https://example.test/benchmarks", report, opener=opener)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(response["id"], "9F32A")


if __name__ == "__main__":
    unittest.main()

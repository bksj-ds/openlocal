"""OpenAI-compatible health and first-token verification."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeTestError(RuntimeError):
    """The inference endpoint did not complete a smoke test."""


OpenUrl = Callable[..., Any]


def request_json(
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 10,
    opener: OpenUrl = urlopen,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SmokeTestError(f"endpoint returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise SmokeTestError(f"endpoint is unavailable: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SmokeTestError(f"invalid or timed-out endpoint response: {exc}") from exc
    if not isinstance(value, dict):
        raise SmokeTestError("endpoint returned a non-object JSON response")
    return value


def first_token(
    base_url: str = "http://127.0.0.1:8000/v1",
    model: str | None = None,
    timeout: float = 120,
    opener: OpenUrl = urlopen,
) -> dict[str, Any]:
    models = request_json(f"{base_url}/models", timeout=timeout, opener=opener)
    entries = models.get("data")
    if not isinstance(entries, list) or not entries:
        raise SmokeTestError("/v1/models returned no models")
    selected = model or entries[0].get("id")
    if not selected:
        raise SmokeTestError("model response did not include an id")
    started = time.perf_counter()
    response = request_json(
        f"{base_url}/chat/completions",
        {
            "model": selected,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "temperature": 0,
            "max_tokens": 8,
        },
        timeout=timeout,
        opener=opener,
    )
    elapsed = time.perf_counter() - started
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SmokeTestError("chat completion returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict) or not (
        message.get("content") or message.get("reasoning_content")
    ):
        raise SmokeTestError("chat completion returned no generated token")
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return {
        "model": selected,
        "elapsed_seconds": round(elapsed, 3),
        "completion_tokens": usage.get("completion_tokens"),
        "success": True,
    }


def wait_for_first_token(
    model: str,
    timeout: float = 1800,
    interval: float = 5,
    base_url: str = "http://127.0.0.1:8000/v1",
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: SmokeTestError | None = None
    while time.monotonic() < deadline:
        try:
            return first_token(base_url=base_url, model=model, timeout=min(120, timeout))
        except SmokeTestError as exc:
            last_error = exc
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise SmokeTestError(f"first-token verification timed out: {last_error}")

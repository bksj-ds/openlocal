from __future__ import annotations

import json
import unittest

from openlocal.smoke import SmokeTestError, first_token, request_json


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.value).encode("utf-8")


class Opener:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith("/models"):
            return Response({"data": [{"id": "example/model"}]})
        return Response(
            {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"completion_tokens": 1},
            }
        )


class SmokeTests(unittest.TestCase):
    def test_first_token_checks_models_and_chat(self):
        opener = Opener()
        result = first_token(opener=opener)
        self.assertTrue(result["success"])
        self.assertEqual(result["model"], "example/model")
        self.assertEqual(result["completion_tokens"], 1)
        self.assertEqual(len(opener.requests), 2)
        payload = json.loads(opener.requests[1].data)
        self.assertEqual(payload["temperature"], 0)

    def test_non_object_json_fails(self):
        def opener(request, timeout):
            return Response([])

        with self.assertRaisesRegex(SmokeTestError, "non-object"):
            request_json("http://example.test", opener=opener)


if __name__ == "__main__":
    unittest.main()

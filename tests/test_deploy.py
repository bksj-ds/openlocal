from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from openlocal.deploy import (
    DeploymentError,
    compose_command,
    read_state,
    render_compose,
    write_deployment,
)

PROFILE = {
    "schema_version": 1,
    "id": "test-profile",
    "hardware": {
        "gpu_vendor": "nvidia",
        "min_vram_gb": 8,
        "min_ram_gb": 16,
        "min_gpu_count": 1,
    },
    "model": {
        "id": "example/model",
        "family": "example",
        "parameters_b": 8,
        "quantization": "awq",
    },
    "backend": {"engine": "vllm", "image": "vllm/vllm-openai:v1.2.3"},
    "runtime": {
        "max_model_len": 16384,
        "gpu_memory_utilization": 0.9,
        "max_num_seqs": 4,
    },
    "estimates": {"vram_gb": 8, "status": "provisional", "basis": "test"},
}


class ComposeTests(unittest.TestCase):
    def test_render_is_loopback_pinned_and_secret_free(self):
        rendered = render_compose(PROFILE)
        document = yaml.safe_load(rendered)
        service = document["services"]["vllm"]
        self.assertEqual(service["image"], "vllm/vllm-openai:v1.2.3")
        self.assertEqual(service["ports"], ["127.0.0.1:8000:8000"])
        self.assertIn("--quantization", service["command"])
        self.assertNotIn("HF_TOKEN", rendered)
        self.assertNotIn("0.0.0.0:8000", rendered)

    def test_ui_is_optional_secure_and_persistent(self):
        document = yaml.safe_load(render_compose(PROFILE, with_ui=True))
        ui = document["services"]["open-webui"]
        self.assertEqual(ui["ports"], ["127.0.0.1:3000:8080"])
        self.assertEqual(ui["environment"]["WEBUI_AUTH"], "true")
        self.assertIn("open-webui-data", document["volumes"])

    def test_atomic_deployment_writes_state_and_compose(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            generated = write_deployment(PROFILE, True, home)
            self.assertTrue(generated.is_file())
            state = read_state(home)
            self.assertEqual(state["profile_id"], "test-profile")
            self.assertTrue(state["with_ui"])
            self.assertEqual(compose_command(["ps"], home)[-1], "ps")

    def test_missing_state_is_actionable(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(DeploymentError, "not installed"),
        ):
            read_state(Path(directory))


if __name__ == "__main__":
    unittest.main()

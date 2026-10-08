from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from openlocal.cli import main
from openlocal.deploy import DeploymentError


class CliTests(unittest.TestCase):
    def test_doctor_json(self):
        snapshot = {"schema_version": "1.1", "status": {"ready": False}}
        output = io.StringIO()
        with (
            patch("openlocal.cli.collect_snapshot", return_value=snapshot),
            contextlib.redirect_stdout(output),
        ):
            result = main(["doctor", "--json"])
        self.assertEqual(result, 0)
        self.assertIn('"schema_version": "1.1"', output.getvalue())

    def test_bench_requires_installed_state(self):
        error = io.StringIO()
        with (
            patch("openlocal.cli.read_state", side_effect=DeploymentError("not installed")),
            contextlib.redirect_stderr(error),
        ):
            result = main(["bench"])
        self.assertEqual(result, 1)
        self.assertIn("not installed", error.getvalue())

    def test_recommend_json(self):
        snapshot = {
            "gpu": {
                "vendor": "nvidia",
                "count": 1,
                "devices": [{"vram_gb": 24, "model": "RTX 4090"}],
            },
            "ram_gb": 64,
            "runtime_path": "docker-linux",
        }
        profile = {
            "schema_version": 1,
            "id": "test-profile",
            "hardware": {
                "gpu_vendor": "nvidia",
                "min_vram_gb": 3,
                "min_ram_gb": 8,
                "min_gpu_count": 1,
            },
            "model": {
                "id": "example/model",
                "family": "example",
                "parameters_b": 1,
                "quantization": "none",
            },
            "backend": {"engine": "vllm", "image": "example:v1"},
            "runtime": {
                "max_model_len": 8192,
                "gpu_memory_utilization": 0.9,
                "max_num_seqs": 1,
            },
            "estimates": {"vram_gb": 3, "status": "provisional", "basis": "test"},
        }
        output = io.StringIO()
        with (
            patch("openlocal.cli.collect_snapshot", return_value=snapshot),
            patch("openlocal.cli.load_profiles", return_value=[profile]),
            contextlib.redirect_stdout(output),
        ):
            result = main(["recommend", "--json"])
        self.assertEqual(result, 0)
        self.assertIn('"profile_id": "test-profile"', output.getvalue())


if __name__ == "__main__":
    unittest.main()

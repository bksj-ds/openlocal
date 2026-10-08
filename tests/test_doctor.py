from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from openlocal.doctor import CommandResult, as_json, collect_snapshot, detect_nvidia_gpus, format_human


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]):
        self.responses = responses

    def __call__(self, command):
        return self.responses.get(tuple(command), CommandResult(127, "", "missing"))


class NvidiaDetectionTests(unittest.TestCase):
    def test_detects_multiple_gpus_and_normalizes_vram(self):
        runner = FakeRunner(
            {
                (
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ): CommandResult(0, "NVIDIA RTX 4090, 24564, 580.10\nNVIDIA A6000, 49140, 580.10"),
            }
        )

        gpus = detect_nvidia_gpus(runner)

        self.assertEqual([gpu.model for gpu in gpus], ["NVIDIA RTX 4090", "NVIDIA A6000"])
        self.assertEqual([gpu.vram_gb for gpu in gpus], [24.0, 48.0])

    def test_missing_or_malformed_output_is_safe(self):
        self.assertEqual(detect_nvidia_gpus(FakeRunner({})), [])
        command = (
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        )
        self.assertEqual(detect_nvidia_gpus(FakeRunner({command: CommandResult(0, "bad,row")})), [])


class SnapshotTests(unittest.TestCase):
    def test_ready_ubuntu_snapshot_and_json_contract(self):
        responses = {
            (
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ): CommandResult(0, "NVIDIA RTX 4090, 24564, 580.10"),
            ("nvidia-smi",): CommandResult(0, "NVIDIA-SMI 580.10 CUDA Version: 13.0"),
            ("docker", "version", "--format", "{{.Server.Version}}|{{.Server.Os}}"): CommandResult(0, "28.4.0|linux"),
            ("docker", "compose", "version", "--short"): CommandResult(0, "2.39.4"),
            ("nvidia-ctk", "--version"): CommandResult(0, "NVIDIA Container Toolkit CLI version 1.18.0"),
        }
        runner = FakeRunner(responses)
        with (
            patch("openlocal.doctor._os_details", return_value=("Ubuntu 24.04.3 LTS", "24.04", None)),
            patch("openlocal.doctor.platform.system", return_value="Linux"),
            patch("openlocal.doctor.platform.machine", return_value="x86_64"),
            patch("openlocal.doctor.platform.processor", return_value="AMD Ryzen 9 7950X"),
            patch("openlocal.doctor._memory_gb", return_value=64.0),
        ):
            snapshot = collect_snapshot(runner)

        self.assertTrue(snapshot["status"]["ready"])
        self.assertEqual(snapshot["gpu"]["count"], 1)
        self.assertEqual(snapshot["cuda"], "13.0")
        self.assertEqual(json.loads(as_json(snapshot))["schema_version"], "1.1")
        self.assertIn("Ready for local inference", format_human(snapshot))

    def test_supported_windows_wsl2_snapshot(self):
        responses = {
            (
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ): CommandResult(0, "NVIDIA RTX 4090, 24564, 580.10"),
            ("nvidia-smi",): CommandResult(0, "NVIDIA-SMI 580.10 CUDA Version: 13.0"),
            ("docker", "version", "--format", "{{.Server.Version}}|{{.Server.Os}}"): CommandResult(0, "29.0.0|linux"),
            ("docker", "compose", "version", "--short"): CommandResult(0, "2.39.4"),
            ("wsl.exe", "--list", "--verbose"): CommandResult(0, "NAME STATE VERSION\n* Ubuntu Stopped 2"),
            ("wsl.exe", "--version"): CommandResult(0, "WSL version: 2.6.1.0"),
        }
        with (
            patch("openlocal.doctor._os_details", return_value=("Windows 11", "10.0.26100", 26100)),
            patch("openlocal.doctor.platform.system", return_value="Windows"),
            patch("openlocal.doctor._memory_gb", return_value=64.0),
        ):
            snapshot = collect_snapshot(FakeRunner(responses))

        self.assertTrue(snapshot["status"]["ready"])
        self.assertEqual(snapshot["runtime_path"], "docker-desktop-wsl2")
        self.assertFalse(snapshot["nvidia_container_toolkit"]["required"])

    def test_unsupported_machine_reports_blockers(self):
        with (
            patch("openlocal.doctor._os_details", return_value=("macOS", "15", None)),
            patch("openlocal.doctor.platform.system", return_value="Darwin"),
            patch("openlocal.doctor._memory_gb", return_value=32.0),
        ):
            snapshot = collect_snapshot(FakeRunner({}))

        self.assertFalse(snapshot["status"]["ready"])
        self.assertEqual(len(snapshot["status"]["blockers"]), 4)


if __name__ == "__main__":
    unittest.main()

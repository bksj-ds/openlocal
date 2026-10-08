"""Read-only host inspection for OpenLocal."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import Callable, Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str]], CommandResult]


@dataclass(frozen=True)
class GPU:
    vendor: str
    model: str
    vram_gb: float
    driver: str | None


def _run(command: Sequence[str]) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=8,
            check=False,
        )
        return CommandResult(
            result.returncode,
            _decode_output(result.stdout).strip(),
            _decode_output(result.stderr).strip(),
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", str(exc))


def _decode_output(value: bytes) -> str:
    """Decode normal UTF-8 output and UTF-16 output emitted by wsl.exe."""
    if not value:
        return ""
    if value.startswith((b"\xff\xfe", b"\xfe\xff")) or value[:80].count(b"\x00") > 8:
        return value.decode("utf-16", errors="replace")
    return value.decode("utf-8", errors="replace")


def _os_details() -> tuple[str, str | None, int | None]:
    if platform.system() == "Windows":
        try:
            build = sys.getwindowsversion().build
        except AttributeError:
            build = None
        name = "Windows 11" if build is not None and build >= 22000 else "Windows 10"
        version = platform.win32_ver()[1] or platform.release() or None
        return name, version, build

    release_file = Path("/etc/os-release")
    if not release_file.exists():
        return platform.system() or "Unknown", platform.release() or None, None
    values: dict[str, str] = {}
    try:
        for raw_line in release_file.read_text(encoding="utf-8").splitlines():
            if "=" not in raw_line or raw_line.lstrip().startswith("#"):
                continue
            key, value = raw_line.split("=", 1)
            values[key] = value.strip().strip('"')
    except OSError:
        return platform.system() or "Unknown", platform.release() or None, None
    return values.get("PRETTY_NAME", values.get("NAME", "Linux")), values.get("VERSION_ID"), None


def _memory_gb() -> float | None:
    if platform.system() == "Linux":
        try:
            first = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()[0]
            return round(int(first.split()[1]) / 1024 / 1024, 1)
        except (OSError, IndexError, ValueError):
            return None
    if platform.system() == "Windows":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.total_physical / 1024**3, 1)
        except (AttributeError, OSError):
            return None
    return None


def _cpu_name(runner: Runner) -> str:
    name = platform.processor().strip()
    if name:
        return name
    if platform.system() == "Linux":
        result = runner(["lscpu"])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.lower().startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip()
    return platform.machine() or "Unknown"


def detect_nvidia_gpus(runner: Runner = _run) -> list[GPU]:
    result = runner(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if result.returncode != 0:
        return []
    gpus: list[GPU] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            memory_gb = round(float(parts[1]) / 1024, 1)
        except ValueError:
            continue
        gpus.append(GPU("nvidia", parts[0], memory_gb, parts[2] or None))
    return gpus


def _cuda_version(runner: Runner) -> str | None:
    result = runner(["nvidia-smi"])
    if result.returncode == 0:
        match = re.search(r"CUDA Version:\s*([0-9.]+)", result.stdout)
        if match:
            return match.group(1)
    result = runner(["nvcc", "--version"])
    if result.returncode == 0:
        match = re.search(r"release\s+([0-9.]+)", result.stdout)
        if match:
            return match.group(1)
    return None


def _version_probe(runner: Runner, command: Sequence[str]) -> tuple[bool, str | None]:
    result = runner(command)
    if result.returncode != 0:
        return False, None
    line = next((item.strip() for item in result.stdout.splitlines() if item.strip()), None)
    return True, line


def _toolkit_probe(runner: Runner) -> tuple[bool, str | None]:
    ok, version = _version_probe(runner, ["nvidia-ctk", "--version"])
    if ok:
        return ok, version
    if platform.system() != "Linux":
        return False, None
    for command in (
        ["dpkg-query", "-W", "-f=${Version}", "nvidia-container-toolkit"],
        ["rpm", "-q", "--qf", "%{VERSION}", "nvidia-container-toolkit"],
    ):
        ok, version = _version_probe(runner, command)
        if ok:
            return ok, version
    return False, None


def _wsl_probe(runner: Runner) -> tuple[bool, str | None]:
    if platform.system() != "Windows":
        return False, None
    status = runner(["wsl.exe", "--list", "--verbose"])
    if status.returncode != 0:
        return False, None
    has_wsl2_distribution = any(
        re.search(r"\s2\s*$", line) is not None for line in status.stdout.splitlines()
    )
    if not has_wsl2_distribution:
        return False, None
    version = runner(["wsl.exe", "--version"])
    match = re.search(r"([0-9]+(?:\.[0-9]+){1,3})", version.stdout)
    return True, match.group(1) if match else None


def _docker_probe(runner: Runner) -> tuple[bool, str | None, str | None]:
    result = runner(
        ["docker", "version", "--format", "{{.Server.Version}}|{{.Server.Os}}"]
    )
    if result.returncode != 0:
        return False, None, None
    parts = [part.strip() for part in result.stdout.split("|", 1)]
    version = parts[0] or None
    server_os = parts[1].lower() if len(parts) == 2 and parts[1] else None
    return True, version, server_os


def collect_snapshot(runner: Runner = _run) -> dict[str, object]:
    system = platform.system()
    os_name, os_version, os_build = _os_details()
    gpus = detect_nvidia_gpus(runner)
    docker_ok, docker_version, docker_server_os = _docker_probe(runner)
    compose_ok, compose_version = _version_probe(runner, ["docker", "compose", "version", "--short"])
    toolkit_ok, toolkit_version = _toolkit_probe(runner)
    wsl_ok, wsl_version = _wsl_probe(runner)
    disk = shutil.disk_usage(Path.cwd())
    linux_supported = system == "Linux" and "Ubuntu" in os_name and os_version in {"22.04", "24.04"}
    windows_supported = system == "Windows" and os_build is not None and os_build >= 19044
    supported_os = linux_supported or windows_supported
    platform_ready = toolkit_ok if linux_supported else wsl_ok and docker_server_os == "linux"
    ready = supported_os and bool(gpus) and docker_ok and compose_ok and platform_ready
    blockers: list[str] = []
    if not supported_os:
        blockers.append("v0.1 supports Ubuntu 22.04/24.04 or Windows 10 21H2+/Windows 11")
    if not gpus:
        blockers.append("no NVIDIA GPU detected")
    if not docker_ok:
        blockers.append("Docker Engine is unavailable")
    if not compose_ok:
        blockers.append("Docker Compose v2 is unavailable")
    if linux_supported and not toolkit_ok:
        blockers.append("NVIDIA Container Toolkit is unavailable")
    if windows_supported and not wsl_ok:
        blockers.append("WSL2 is unavailable or has no version 2 distribution")
    if windows_supported and docker_ok and docker_server_os != "linux":
        blockers.append("Docker Desktop is not using Linux containers")

    return {
        "schema_version": "1.1",
        "os": {"name": os_name, "version": os_version, "build": os_build},
        "architecture": platform.machine() or "unknown",
        "cpu": _cpu_name(runner),
        "ram_gb": _memory_gb(),
        "gpu": {
            "vendor": "nvidia" if gpus else None,
            "count": len(gpus),
            "devices": [asdict(gpu) for gpu in gpus],
            "total_vram_gb": round(sum(gpu.vram_gb for gpu in gpus), 1),
        },
        "driver": gpus[0].driver if gpus else None,
        "cuda": _cuda_version(runner),
        "docker": {
            "available": docker_ok,
            "version": docker_version,
            "server_os": docker_server_os,
        },
        "docker_compose": {"available": compose_ok, "version": compose_version},
        "nvidia_container_toolkit": {
            "available": toolkit_ok,
            "version": toolkit_version,
            "required": linux_supported,
        },
        "wsl": {"available": wsl_ok, "version": wsl_version, "required": windows_supported},
        "runtime_path": (
            "docker-desktop-wsl2"
            if windows_supported
            else "docker-linux"
            if linux_supported
            else None
        ),
        "disk": {
            "path": str(Path.cwd()),
            "free_gb": round(disk.free / 1024**3, 1),
            "total_gb": round(disk.total / 1024**3, 1),
        },
        "status": {"ready": ready, "message": "Ready for local inference" if ready else "Not ready", "blockers": blockers},
    }


def _display(value: object, suffix: str = "") -> str:
    if value is None:
        return "Not detected"
    return f"{value}{suffix}"


def format_human(snapshot: dict[str, object]) -> str:
    os_info = snapshot["os"]
    gpu_info = snapshot["gpu"]
    docker = snapshot["docker"]
    compose = snapshot["docker_compose"]
    toolkit = snapshot["nvidia_container_toolkit"]
    wsl = snapshot["wsl"]
    disk = snapshot["disk"]
    status = snapshot["status"]
    assert isinstance(os_info, dict) and isinstance(gpu_info, dict)
    assert isinstance(docker, dict) and isinstance(compose, dict) and isinstance(toolkit, dict)
    assert isinstance(wsl, dict)
    assert isinstance(disk, dict) and isinstance(status, dict)

    devices = gpu_info.get("devices", [])
    gpu_lines = [
        f"  [{index}] {item['model']} ({item['vram_gb']} GB)"
        for index, item in enumerate(devices)
        if isinstance(item, dict)
    ] or ["  Not detected"]
    lines = [
        "OpenLocal Doctor",
        "",
        f"OS                    {_display(os_info.get('name'))}",
        f"Architecture          {_display(snapshot.get('architecture'))}",
        f"CPU                   {_display(snapshot.get('cpu'))}",
        f"RAM                   {_display(snapshot.get('ram_gb'), ' GB')}",
        "GPU",
        *gpu_lines,
        f"Total VRAM            {_display(gpu_info.get('total_vram_gb'), ' GB')}",
        f"Driver                {_display(snapshot.get('driver'))}",
        f"CUDA                  {_display(snapshot.get('cuda'))}",
        f"Docker                {'OK ' + str(docker.get('version') or '') if docker.get('available') else 'Not available'}".rstrip(),
        f"Docker Compose        {'OK ' + str(compose.get('version') or '') if compose.get('available') else 'Not available'}".rstrip(),
        f"WSL2                  {'OK ' + str(wsl.get('version') or '') if wsl.get('available') else 'Not required' if not wsl.get('required') else 'Not available'}".rstrip(),
        f"NVIDIA Toolkit        {'OK ' + str(toolkit.get('version') or '') if toolkit.get('available') else 'Not required' if not toolkit.get('required') else 'Not available'}".rstrip(),
        f"Runtime path          {_display(snapshot.get('runtime_path'))}",
        f"Disk free             {_display(disk.get('free_gb'), ' GB')}",
        "",
        f"Status                {status.get('message')}",
    ]
    blockers = status.get("blockers", [])
    if blockers:
        lines.extend(["Blockers", *[f"  - {item}" for item in blockers]])
    return "\n".join(lines)


def as_json(snapshot: dict[str, object]) -> str:
    return json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True)

"""Profile loading, validation, and rule-based recommendations."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

import yaml


class ProfileError(ValueError):
    """A profile cannot be loaded or validated."""


@dataclass(frozen=True)
class Recommendation:
    category: str
    profile: dict[str, Any]
    budget_gb: float


REQUIRED_SECTIONS = {
    "hardware": {"gpu_vendor", "min_vram_gb", "min_ram_gb", "min_gpu_count"},
    "model": {"id", "family", "parameters_b", "quantization"},
    "backend": {"engine", "image"},
    "runtime": {"max_model_len", "gpu_memory_utilization", "max_num_seqs"},
    "estimates": {"vram_gb", "status", "basis"},
}


def _profile_directories(explicit: Path | None = None) -> Iterable[Path]:
    if explicit is not None:
        yield explicit
        return
    configured = os.environ.get("OPENLOCAL_PROFILE_DIR")
    if configured:
        yield Path(configured)
    yield Path.cwd() / "profiles" / "models"
    yield Path(__file__).resolve().parents[2] / "profiles" / "models"
    yield Path(sys.prefix) / "share" / "openlocal" / "profiles" / "models"


def validate_profile(profile: object, source: str = "profile") -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ProfileError(f"{source}: root must be a mapping")
    if profile.get("schema_version") != 1:
        raise ProfileError(f"{source}: schema_version must be 1")
    profile_id = profile.get("id")
    if not isinstance(profile_id, str) or not profile_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in profile_id
    ):
        raise ProfileError(f"{source}: id must contain lowercase letters, digits, and hyphens")
    for section, required in REQUIRED_SECTIONS.items():
        value = profile.get(section)
        if not isinstance(value, dict):
            raise ProfileError(f"{source}: {section} must be a mapping")
        missing = sorted(required - value.keys())
        if missing:
            raise ProfileError(f"{source}: {section} is missing {', '.join(missing)}")
    hardware = profile["hardware"]
    runtime = profile["runtime"]
    estimates = profile["estimates"]
    for name, value in (
        ("hardware.min_vram_gb", hardware["min_vram_gb"]),
        ("hardware.min_ram_gb", hardware["min_ram_gb"]),
        ("estimates.vram_gb", estimates["vram_gb"]),
    ):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ProfileError(f"{source}: {name} must be a positive number")
    utilization = runtime["gpu_memory_utilization"]
    if not isinstance(utilization, (int, float)) or not 0 < utilization < 1:
        raise ProfileError(f"{source}: runtime.gpu_memory_utilization must be between 0 and 1")
    if estimates["status"] not in {"provisional", "benchmarked"}:
        raise ProfileError(f"{source}: estimates.status must be provisional or benchmarked")
    return profile


def load_profiles(directory: Path | None = None) -> list[dict[str, Any]]:
    selected: Path | None = None
    for candidate in _profile_directories(directory):
        if candidate.is_dir() and list(candidate.glob("*.yaml")):
            selected = candidate
            break
    if selected is None:
        raise ProfileError("no model profiles found; set OPENLOCAL_PROFILE_DIR")

    profiles: list[dict[str, Any]] = []
    ids: set[str] = set()
    for path in sorted(selected.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ProfileError(f"{path}: cannot read profile: {exc}") from exc
        profile = validate_profile(raw, str(path))
        if profile["id"] in ids:
            raise ProfileError(f"{path}: duplicate profile id {profile['id']}")
        ids.add(profile["id"])
        profiles.append(profile)
    return profiles


def recommend(snapshot: dict[str, Any], profiles: list[dict[str, Any]]) -> list[Recommendation]:
    gpu = snapshot.get("gpu", {})
    devices = gpu.get("devices", []) if isinstance(gpu, dict) else []
    if not devices:
        return []
    largest_vram = max(float(device.get("vram_gb", 0)) for device in devices)
    vendor = gpu.get("vendor")
    ram_gb = float(snapshot.get("ram_gb") or 0)
    gpu_count = int(gpu.get("count") or 0)
    eligible = [
        profile
        for profile in profiles
        if profile["hardware"]["gpu_vendor"] == vendor
        and float(profile["hardware"]["min_vram_gb"]) <= largest_vram
        and float(profile["hardware"]["min_ram_gb"]) <= ram_gb
        and int(profile["hardware"]["min_gpu_count"]) <= gpu_count
    ]
    eligible.sort(key=lambda item: (float(item["model"]["parameters_b"]), float(item["estimates"]["vram_gb"])))
    if not eligible:
        return []

    budgets = (
        ("FAST", max(3.0, largest_vram * 0.45)),
        ("BALANCED", max(3.0, largest_vram * 0.70)),
        ("MAX QUALITY", largest_vram * 0.92),
    )
    recommendations: list[Recommendation] = []
    used: set[str] = set()
    for category, budget in budgets:
        candidates = [
            profile for profile in eligible if float(profile["estimates"]["vram_gb"]) <= budget
        ]
        selected = candidates[-1] if candidates else eligible[0]
        if selected["id"] in used:
            continue
        used.add(selected["id"])
        recommendations.append(Recommendation(category, selected, round(budget, 1)))
    return recommendations


def result_document(snapshot: dict[str, Any], recommendations: list[Recommendation]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "hardware": {
            "gpu": snapshot.get("gpu"),
            "ram_gb": snapshot.get("ram_gb"),
            "runtime_path": snapshot.get("runtime_path"),
        },
        "recommendations": [
            {
                "category": item.category,
                "profile_id": item.profile["id"],
                "memory_budget_gb": item.budget_gb,
                "model": item.profile["model"],
                "backend": item.profile["backend"],
                "runtime": item.profile["runtime"],
                "estimated_vram_gb": item.profile["estimates"]["vram_gb"],
                "estimate_status": item.profile["estimates"]["status"],
            }
            for item in recommendations
        ],
    }


def format_recommendations(snapshot: dict[str, Any], recommendations: list[Recommendation]) -> str:
    gpu = snapshot.get("gpu", {})
    devices = gpu.get("devices", []) if isinstance(gpu, dict) else []
    detected = ", ".join(
        f"{device.get('model')} / {device.get('vram_gb')} GB" for device in devices
    ) or "No GPU detected"
    lines = ["OpenLocal Recommendations", "", f"Detected hardware     {detected}"]
    if not recommendations:
        return "\n".join(lines + ["", "No compatible profile found."])
    lines.extend(["", "Recommended profiles"])
    for item in recommendations:
        profile = item.profile
        lines.extend(
            [
                "",
                item.category,
                f"  Model               {profile['model']['id']}",
                f"  Quantization        {profile['model']['quantization']}",
                f"  Estimated VRAM      {profile['estimates']['vram_gb']} GB ({profile['estimates']['status']})",
                f"  Backend             {profile['backend']['engine']}",
                f"  Max context         {profile['runtime']['max_model_len']}",
                f"  Concurrency         {profile['runtime']['max_num_seqs']}",
                f"  Profile             {profile['id']}",
            ]
        )
    lines.extend(["", "Provisional estimates must be validated with openlocal bench."])
    return "\n".join(lines)


def recommendations_json(snapshot: dict[str, Any], recommendations: list[Recommendation]) -> str:
    return json.dumps(result_document(snapshot, recommendations), indent=2, ensure_ascii=False, sort_keys=True)


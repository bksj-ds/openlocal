"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .doctor import as_json, collect_snapshot, format_human
from .recommend import (
    ProfileError,
    format_recommendations,
    load_profiles,
    recommend,
    recommendations_json,
)


PLANNED_COMMANDS = ("install", "start", "stop", "status", "bench", "update", "logs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openlocal",
        description="Find, run, and benchmark the best local LLM configuration for your hardware.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Inspect hardware and runtime prerequisites")
    doctor.add_argument("--json", action="store_true", dest="json_output", help="Emit stable JSON")

    recommend_parser = subparsers.add_parser(
        "recommend", help="Recommend model/runtime profiles for detected hardware"
    )
    recommend_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Emit stable JSON"
    )
    recommend_parser.add_argument(
        "--profiles", type=str, help="Read model profiles from this directory"
    )

    for command in PLANNED_COMMANDS:
        subparsers.add_parser(command, help=f"Planned for v0.1 (not implemented): {command}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        snapshot = collect_snapshot()
        print(as_json(snapshot) if args.json_output else format_human(snapshot))
        return 0
    if args.command == "recommend":
        snapshot = collect_snapshot()
        try:
            profiles = load_profiles(Path(args.profiles) if args.profiles else None)
        except ProfileError as exc:
            print(f"openlocal recommend: {exc}", file=sys.stderr)
            return 1
        recommendations = recommend(snapshot, profiles)
        print(
            recommendations_json(snapshot, recommendations)
            if args.json_output
            else format_recommendations(snapshot, recommendations)
        )
        return 0 if recommendations else 1
    print(f"openlocal {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

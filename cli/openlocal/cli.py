"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .benchmark import (
    BenchmarkError,
    format_report,
    run_benchmark,
    submit_report,
)
from .deploy import (
    DeploymentError,
    compose_path,
    openlocal_home,
    read_state,
    render_compose,
    run_compose,
    select_profile,
    write_atomic,
    write_deployment,
)
from .doctor import as_json, collect_snapshot, format_human
from .recommend import (
    ProfileError,
    format_recommendations,
    load_profiles,
    profile_compatible,
    recommend,
    recommendations_json,
)
from .smoke import SmokeTestError, wait_for_first_token

PLANNED_COMMANDS: tuple[str, ...] = ()


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

    install = subparsers.add_parser(
        "install", help="Generate and start a recommended vLLM deployment"
    )
    install.add_argument("--profile", help="Install a specific profile id")
    install.add_argument("--profiles", help="Read model profiles from this directory")
    install.add_argument("--ui", action="store_true", help="Add the pinned Open WebUI service")
    install.add_argument("--yes", action="store_true", help="Skip the interactive confirmation")
    install.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Compose without writing or starting services",
    )
    install.add_argument("--timeout", type=int, default=1800, help="First-token timeout in seconds")

    subparsers.add_parser("start", help="Start the installed deployment")
    subparsers.add_parser("stop", help="Stop services without deleting data")
    status = subparsers.add_parser("status", help="Show deployment status")
    status.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit Docker Compose JSON",
    )
    logs = subparsers.add_parser("logs", help="Show service logs")
    logs.add_argument("service", nargs="?", choices=("vllm", "open-webui"))
    logs.add_argument("--follow", action="store_true", help="Follow log output")
    subparsers.add_parser("update", help="Pull pinned images and recreate the deployment")

    bench = subparsers.add_parser("bench", help="Run reproducible streaming benchmarks")
    bench.add_argument("--json", action="store_true", dest="json_output", help="Print report JSON")
    bench.add_argument(
        "--concurrency", default="1,2,4,8,16", help="Comma-separated concurrency levels"
    )
    bench.add_argument("--requests", type=int, default=4, help="Minimum requests per level")
    bench.add_argument(
        "--max-tokens", type=int, default=128, help="Maximum output tokens per request"
    )
    bench.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    bench.add_argument("--output", type=Path, help="Write report to this path")
    bench.add_argument(
        "--submit",
        action="store_true",
        help="Submit the completed report (explicit opt-in)",
    )
    bench.add_argument("--submit-url", default=os.environ.get("OPENLOCAL_SUBMIT_URL"))
    bench.add_argument("--yes", action="store_true", help="Skip submission confirmation")

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
    if args.command == "install":
        snapshot = collect_snapshot()
        try:
            profiles = load_profiles(Path(args.profiles) if args.profiles else None)
            recommended = recommend(snapshot, profiles)
            selected = select_profile(profiles, recommended, args.profile)
            if not profile_compatible(snapshot, selected):
                raise DeploymentError(
                    f"profile {selected['id']} exceeds detected GPU, VRAM, RAM, or GPU-count constraints"
                )
            generated = render_compose(selected, args.ui)
        except (ProfileError, DeploymentError) as exc:
            print(f"openlocal install: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(generated, end="")
            return 0
        status_info = snapshot.get("status", {})
        if not isinstance(status_info, dict) or not status_info.get("ready"):
            blockers = status_info.get("blockers", []) if isinstance(status_info, dict) else []
            print("openlocal install: host is not ready", file=sys.stderr)
            for blocker in blockers:
                print(f"  - {blocker}", file=sys.stderr)
            return 1
        destination = compose_path()
        if not args.yes:
            print(f"Profile: {selected['id']}")
            print(f"Model:   {selected['model']['id']}")
            print(f"Image:   {selected['backend']['image']}")
            print(f"Compose: {destination}")
            if input("Continue? [y/N] ").strip().lower() not in {"y", "yes"}:
                print("Installation cancelled.")
                return 1
        generated_path = write_deployment(selected, args.ui)
        print(f"Generated {generated_path}")
        try:
            result = run_compose(["up", "-d"])
        except DeploymentError as exc:
            print(f"openlocal install: {exc}", file=sys.stderr)
            return 1
        if result.returncode != 0:
            print("openlocal install: Docker Compose failed", file=sys.stderr)
            return result.returncode or 1
        print("Waiting for the OpenAI-compatible endpoint and first token...")
        try:
            verified = wait_for_first_token(selected["model"]["id"], timeout=args.timeout)
        except SmokeTestError as exc:
            print(f"openlocal install: {exc}", file=sys.stderr)
            return 1
        print(f"First token verified in {verified['elapsed_seconds']}s")
        return 0
    if args.command in {"start", "stop", "status", "logs", "update"}:
        try:
            read_state()
            if args.command == "start":
                result = run_compose(["up", "-d"])
            elif args.command == "stop":
                result = run_compose(["stop"])
            elif args.command == "status":
                if args.json_output:
                    result = run_compose(["ps", "--format", "json"], capture=True)
                    if result.stdout:
                        print(result.stdout.strip())
                else:
                    result = run_compose(["ps"])
            elif args.command == "logs":
                command = ["logs"]
                if args.follow:
                    command.append("--follow")
                if args.service:
                    command.append(args.service)
                result = run_compose(command)
            else:
                pull = run_compose(["pull"])
                result = pull if pull.returncode else run_compose(["up", "-d"])
        except DeploymentError as exc:
            print(f"openlocal {args.command}: {exc}", file=sys.stderr)
            return 1
        return result.returncode
    if args.command == "bench":
        try:
            state = read_state()
            profiles = load_profiles()
            profile = next(
                (item for item in profiles if item["id"] == state.get("profile_id")),
                None,
            )
            if profile is None:
                raise BenchmarkError(f"installed profile is unavailable: {state.get('profile_id')}")
            levels = [int(value.strip()) for value in args.concurrency.split(",") if value.strip()]
            if args.requests <= 0 or args.max_tokens <= 0:
                raise BenchmarkError("requests and max-tokens must be positive")
            snapshot = collect_snapshot()
            report = run_benchmark(
                snapshot,
                state["model_id"],
                {
                    "profile_id": profile["id"],
                    "backend": profile["backend"],
                    "settings": profile["runtime"],
                },
                levels,
                args.requests,
                args.max_tokens,
                args.base_url,
            )
        except (DeploymentError, ProfileError, BenchmarkError, ValueError) as exc:
            print(f"openlocal bench: {exc}", file=sys.stderr)
            return 1
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output = args.output or openlocal_home() / "benchmarks" / f"benchmark-{timestamp}.json"
        write_atomic(output, json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(report, indent=2, sort_keys=True)
            if args.json_output
            else format_report(report)
        )
        print(f"Report: {output}", file=sys.stderr if args.json_output else sys.stdout)
        if args.submit:
            if not args.submit_url:
                print(
                    "openlocal bench: --submit requires --submit-url or OPENLOCAL_SUBMIT_URL",
                    file=sys.stderr,
                )
                return 1
            print("The following benchmark data will be uploaded:")
            print(json.dumps(report, indent=2, sort_keys=True))
            print(
                "No prompt content, hostname, username, or IP address is included in the payload."
            )
            if not args.yes and input("Continue? [y/N] ").strip().lower() not in {
                "y",
                "yes",
            }:
                print("Submission cancelled.")
                return 1
            try:
                response = submit_report(args.submit_url, report)
            except BenchmarkError as exc:
                print(f"openlocal bench: {exc}", file=sys.stderr)
                return 1
            print(json.dumps(response, indent=2, sort_keys=True))
        return 0
    print(f"openlocal {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

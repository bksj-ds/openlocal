# CLI contract

The command surface is intentionally fixed before implementation. Commands use human-readable output by default and stable JSON when `--json` is supplied.

## Global behavior

```text
openlocal --version
openlocal <command> --help
```

- Exit `0`: operation completed successfully.
- Exit `1`: operation ran but the requested state was not reached.
- Exit `2`: invalid arguments or unsupported command.
- JSON goes to stdout; diagnostics go to stderr.
- Non-interactive commands never silently upload data or broaden network exposure.

## `openlocal doctor [--json]`

Read-only hardware and dependency inspection. It reports OS, architecture, CPU, RAM, GPUs, aggregate VRAM, driver, CUDA, Docker Engine, Docker Compose, NVIDIA Container Toolkit, and free disk space.

`doctor` must complete when NVIDIA, Docker, or their supporting commands are absent. Readiness is strict only for the v0.1 supported path: Ubuntu 22.04/24.04, NVIDIA GPU, Docker, Compose, and NVIDIA Container Toolkit.

## `openlocal recommend [--json]`

Match detected hardware to versioned profiles and return FAST, BALANCED, and MAX QUALITY options where valid. The response explains why each profile matches and identifies the source of memory estimates.

## `openlocal install [--profile ID] [--ui] [--yes]`

Run `doctor`, resolve a profile, render Compose configuration, preview planned host changes, download the model, start vLLM, and perform a health check. `--ui` adds Open WebUI. It must not expose services outside loopback by default.

## Lifecycle commands

```text
openlocal start
openlocal stop
openlocal status [--json]
openlocal logs [SERVICE]
openlocal update
```

Lifecycle commands operate only on the OpenLocal project and generated files. `stop` preserves model data. Updates preview version changes and never modify user-authored profiles in place.

## `openlocal bench [--json] [--submit]`

Run warm-up plus measured workloads at concurrency 1, 2, 4, 8, and 16. Reports include benchmark and schema versions, timestamps, hardware, model, runtime configuration, workload definition, TTFT, ITL, output tokens/s, total throughput, requests/s, VRAM, GPU utilization, and latency p50/p95.

`--submit` is explicit opt-in. Before submission, the CLI displays the exact payload and confirms that it includes no prompt content, hostname, username, or stored IP address.


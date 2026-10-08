# Installation and operations

## Requirements

Choose one supported host path:

- Ubuntu 22.04/24.04, NVIDIA GPU, Docker Engine, Compose v2, and NVIDIA Container Toolkit.
- Windows 10 build 19044+ or Windows 11, NVIDIA GPU, current WSL2, and Docker Desktop using Linux containers.

Install the CLI and inspect the host:

```bash
python -m pip install -e .
openlocal doctor
openlocal recommend
```

## Preview before changing anything

```bash
openlocal install --dry-run
openlocal install --dry-run --ui
```

The preview is generated from the selected profile. It does not create `~/.openlocal`, pull an image, or contact a model registry.

## Install

```bash
openlocal install
# or
openlocal install --ui
```

OpenLocal displays the selected model, pinned image, and generated path before confirmation. Generated state is stored under `~/.openlocal`; model and optional UI data use Docker named volumes. The API binds to `127.0.0.1:8000`. Open WebUI binds to `127.0.0.1:3000` and keeps authentication enabled.

The command waits for `/v1/models`, sends a deterministic minimal chat request, and succeeds only after a first token is returned. Model output is not written to logs.

## Operations

```bash
openlocal status
openlocal status --json
openlocal logs vllm
openlocal logs --follow vllm
openlocal start
openlocal stop
openlocal update
```

`stop` preserves named volumes. `update` pulls the versions pinned in the generated Compose file; it does not silently move to an unpinned tag.

## Benchmark

```bash
openlocal bench
openlocal bench --concurrency 1,2,4,8,16 --requests 4 --max-tokens 128
openlocal bench --json
```

Reports are written atomically to `~/.openlocal/benchmarks`. Submission is disabled unless `--submit` is explicitly present and a submission URL is configured.

```bash
openlocal bench --submit --submit-url https://YOUR-SERVICE.example/api/benchmarks
```

The exact payload is displayed before confirmation. The payload contains no prompt content, hostname, username, disk path, or IP-address field.


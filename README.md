# OpenLocal

> The easiest way to find, run, and benchmark the best local LLM configuration for your hardware.

OpenLocal detects your hardware, recommends a reproducible model/runtime profile, deploys it securely, and measures its real performance.

> Project status: **pre-alpha**. Hardware detection and rule-based recommendations are implemented. v0.1 targets Ubuntu 22.04/24.04 and Windows 10 21H2+/Windows 11 with an NVIDIA GPU.

[한국어 README](README.ko.md)

## Quick start

Requires Python 3.11 or newer.

```bash
python -m pip install -e .
openlocal doctor
openlocal doctor --json
openlocal recommend
openlocal recommend --json
```

The v0.1 workflow is deliberately small:

```bash
openlocal doctor
openlocal recommend
openlocal install
openlocal start
openlocal stop
openlocal status
openlocal bench
```

`doctor` and `recommend` are implemented. Unimplemented commands fail explicitly instead of pretending to make changes.

## Why OpenLocal?

Local AI is easy to start. Choosing the right configuration is not.

Model size, quantization, context length, concurrency, and runtime flags all compete for the same GPU memory. Benchmarks found online rarely match the exact machine and runtime configuration in front of you. OpenLocal makes the full path reproducible:

```text
hardware -> recommendation -> run -> benchmark
```

The installer is a delivery mechanism. The product is hardware-aware configuration, reproducible benchmarks, and the profile data that connects them.

## Secure by default

- Services bind to `127.0.0.1` by default.
- No telemetry and no automatic benchmark upload.
- Benchmark submission will always be explicit and previewed.
- Container images and runtime inputs are pinned.
- OpenLocal does not request `sudo` unless a documented host operation requires it.
- Secrets never belong in profiles, Compose files, logs, or benchmark reports.

## Current scope

v0.1 targets two host paths with the same Linux-container runtime:

- Ubuntu 22.04/24.04, NVIDIA GPU, Docker Engine, Compose v2, and NVIDIA Container Toolkit.
- Windows 10 21H2+ or Windows 11, NVIDIA GPU, WSL2, and Docker Desktop using Linux containers.

vLLM does not run natively on Windows; OpenLocal uses its officially documented WSL2 route. See [Windows support](docs/WINDOWS.md), [NON_GOALS.md](NON_GOALS.md), and [ROADMAP.md](ROADMAP.md).

## Documentation

- [CLI contract](docs/CLI_SPEC.md)
- [Architecture and data boundaries](docs/ARCHITECTURE.md)
- [Initial issue backlog](docs/ISSUES.md)
- [Contributing](CONTRIBUTING.md)

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q cli
```

No GPU is required for unit tests. GPU integration tests will use a dedicated self-hosted runner later.

## License

MIT. See [LICENSE](LICENSE).

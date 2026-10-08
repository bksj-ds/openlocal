# OpenLocal

> The easiest way to find, run, and benchmark the best local LLM configuration for your hardware.

OpenLocal detects your hardware, recommends a reproducible model/runtime profile, deploys it securely, and measures its real performance.

> Project status: **pre-alpha**. The CLI contract and hardware detection are under active development. Installation support is intentionally limited to Ubuntu 22.04/24.04 with NVIDIA Docker for v0.1.

[한국어 README](README.ko.md)

## Quick start

Requires Python 3.11 or newer.

```bash
python -m pip install -e .
openlocal doctor
openlocal doctor --json
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

Only `doctor` is implemented today. Unimplemented commands fail explicitly instead of pretending to make changes.

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

v0.1 targets one reliable path: Ubuntu 22.04/24.04, an NVIDIA GPU, Docker Engine, Docker Compose, and NVIDIA Container Toolkit. See [NON_GOALS.md](NON_GOALS.md) for what is intentionally excluded and [ROADMAP.md](ROADMAP.md) for release gates.

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

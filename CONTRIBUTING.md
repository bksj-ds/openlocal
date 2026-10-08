# Contributing

OpenLocal welcomes focused contributions to the hardware-to-benchmark path.

## Before starting

1. Choose or open one issue.
2. Confirm that it is inside the current milestone and not listed in `NON_GOALS.md`.
3. Keep one pull request scoped to one problem.

Every issue and pull request must state:

- **Problem**: the user-visible failure or missing capability.
- **Acceptance criteria**: observable completion conditions.
- **Test**: how the behavior is verified without relying on the author's machine.
- **Docs update**: what user or contributor documentation changes.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q cli
```

Use Python 3.11 or newer. Hardware probes must tolerate missing binaries, non-NVIDIA systems, permission failures, timeouts, and malformed command output. Unit tests must not require a GPU or Docker daemon.

## Profiles

Runtime configuration belongs in versioned profiles, not conditional code. A profile contribution must include provenance for its estimates and, once available, a benchmark report produced by OpenLocal.

Profiles and examples must never contain tokens, usernames, hostnames, private paths, or other secrets.

## Security

Generated services bind to loopback unless the user explicitly opts into network exposure. Do not weaken authentication, CORS, host mounts, or container privileges for convenience.


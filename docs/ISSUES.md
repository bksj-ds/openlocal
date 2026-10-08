# Initial issue backlog

These specifications are ready to be copied into GitHub Issues after a remote repository is created. Each issue is independently assignable.

Implementation status: #1 through #10 have initial implementations and unit coverage. Hardware integration validation remains dependent on supported test machines.

## #1 Implement hardware detection

**Problem:** Recommendations need a stable, inspectable hardware snapshot.

**Acceptance criteria:** Detect Linux distribution, architecture, CPU, RAM, NVIDIA GPUs, per-GPU VRAM, disk space, and work without an NVIDIA GPU. Support human and JSON output.

**Test:** Unit tests cover complete, missing-command, malformed-output, and multi-GPU cases without physical hardware.

**Docs update:** Keep `doctor` fields and readiness rules in `docs/CLI_SPEC.md` current.

## #2 Detect NVIDIA GPU VRAM

**Problem:** Model fit cannot be estimated without reliable per-device memory.

**Acceptance criteria:** Parse `nvidia-smi` CSV, preserve each GPU, normalize MiB to GiB, expose total VRAM, and return an empty list when unavailable.

**Test:** Fixtures cover one GPU, multiple GPUs, unusual model names, and command failure.

**Docs update:** Document units and aggregation semantics.

## #3 Detect Docker prerequisites

**Problem:** Installation failures currently happen late and produce poor diagnostics.

**Acceptance criteria:** Distinguish CLI presence from daemon availability; detect Compose v2 and NVIDIA Container Toolkit on Linux; detect WSL2 and Linux-container mode on Windows; report versions when available.

**Test:** Mock successful, missing, permission-denied, and daemon-unreachable outputs.

**Docs update:** Add remediation links for Ubuntu 22.04/24.04 and Windows WSL2/Docker Desktop.

## #4 Define hardware profile schema

**Problem:** Hardware rules must be community-editable and validated outside application code.

**Acceptance criteria:** Versioned schema supports GPU vendor/model matchers, minimum VRAM, GPU count, system RAM, supported OS, and profile provenance. Invalid profiles fail CI with actionable errors.

**Test:** Validate all repository profiles plus positive and negative fixtures.

**Docs update:** Add a profile authoring guide and complete example.

## #5 Implement recommendation engine

**Problem:** Users need a small set of defensible configurations rather than a model catalog.

**Acceptance criteria:** Return FAST, BALANCED, and MAX QUALITY matches; explain each match; never recommend a profile that exceeds detected constraints; support JSON.

**Test:** Table-driven tests cover VRAM tiers at 8, 16, 24, 48, and 80 GB plus boundary values.

**Docs update:** Document rule precedence and estimate limitations.

## #6 Add vLLM Compose template

**Problem:** A matched profile needs a reproducible and secure runtime deployment.

**Acceptance criteria:** Render a pinned vLLM image, loopback-only API port, persistent model cache, NVIDIA device reservation, health check, and profile-derived runtime flags. No secrets are rendered.

**Test:** Snapshot and `docker compose config` validation tests.

**Docs update:** Document generated paths, cache location, and image upgrade policy.

## #7 Add OpenAI compatibility smoke test

**Problem:** Container health does not prove that a model can generate a token.

**Acceptance criteria:** Check `/v1/models`, send a deterministic minimal chat request, record time to first token, redact response content from logs, and return actionable failure categories.

**Test:** Fake-server tests cover success, timeout, invalid JSON, model-not-found, and server error.

**Docs update:** Add troubleshooting for each failure category.

## #8 Add Open WebUI Compose profile

**Problem:** Some users want an optional browser interface without OpenLocal owning a UI.

**Acceptance criteria:** `install --ui` enables a pinned Open WebUI service connected to the local endpoint, persists its data, binds only to loopback, and keeps the API usable without the UI.

**Test:** Compose rendering tests with and without `--ui`.

**Docs update:** Explain ownership, ports, authentication, and removal.

## #9 Implement benchmark runner

**Problem:** Recommendations need measurements produced by a consistent method.

**Acceptance criteria:** Warm up the model; test concurrency 1, 2, 4, 8, and 16; measure TTFT, ITL, output tokens/s, throughput, requests/s, VRAM, GPU utilization, and latency p50/p95; preserve workload metadata.

**Test:** Deterministic fake streaming endpoint plus percentile and token-accounting tests.

**Docs update:** Publish methodology, warm-up policy, and known sources of variance.

## #10 Implement benchmark JSON output

**Problem:** Benchmark results must be comparable, validatable, and later submit-ready.

**Acceptance criteria:** Versioned report schema includes hardware, model, runtime, workload, metrics, tool version, and timestamps; excludes prompt content and local identity; writes atomically; supports stdout.

**Test:** Schema validation, golden report, privacy-field rejection, and interrupted-write tests.

**Docs update:** Document every field, unit, and privacy guarantee.

## P1 follow-up backlog

- **#11 Add RTX 4090 profile** — initial provisional profile added; needs physical benchmark promotion.
- **#12 Add RTX 5090 profile** — initial provisional profile added; needs physical benchmark promotion.
- **#13 Add A6000 profile** — initial provisional profile added; needs physical benchmark promotion.
- **#14 Add install diagnostics** — categorize image-pull, GPU-runtime, model-load, health, and first-token failures.
- **#15 Add uninstall** — remove generated containers/config with an explicit, separate choice for persistent volumes.
- **#16 Add logs command** — implemented for vLLM and Open WebUI.
- **#17 Add update** — implemented for versions pinned in the generated Compose file.
- **#18 Benchmark submission schema** — implemented as versioned report/payload schema.
- **#19 Benchmark result validation** — privacy and required-metric validation implemented; server-side validation remains.
- **#20 README quickstart** — implemented; terminal recording remains a launch asset.

## P2 backlog — do not pull into Week 1

- **#21 Ollama backend**
- **#22 AMD detection and runtime profiles**
- **#23 Apple Silicon detection and runtime profiles**
- **#24 Windows WSL support** — promoted and implemented early by product decision.
- **#25 Model download progress UI**
- **#26 Benchmark permalink service**
- **#27 Community leaderboard**

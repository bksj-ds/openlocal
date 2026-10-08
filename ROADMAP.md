# Roadmap

## Success metric

The primary KPI is the share of users who complete:

```text
install -> first token -> benchmark complete
```

Target: **80% or better** among supported machines.

| Metric | Day 30 | Day 60 | Day 90 |
|---|---:|---:|---:|
| Successful installs | 30 | 150 | 500 |
| GitHub stars | 50 | 200 | 500 |
| Benchmark submissions | 20 | 100 | 300 |
| External contributors | 2 | 10 | 20 |
| Issues and discussions | 10 | 40 | 100 |
| Supported GPU profiles | 3 | 8 | 15 |

## Week 1: one reliable execution path

- Freeze the CLI contract and profile boundary.
- Complete `doctor` on supported and unsupported hosts.
- Add rule-based `recommend` and validated profiles.
- Generate a pinned vLLM Compose deployment.
- Produce the first token through an OpenAI-compatible API.
- Add optional Open WebUI orchestration, status, and logs.

## Week 2: differentiation

- Implement the benchmark engine.
- Measure concurrency 1, 2, 4, 8, and 16.
- Report TTFT, ITL, output tokens/s, throughput, requests/s, VRAM, GPU utilization, and latency p50/p95.
- Produce a machine-readable JSON report.
- Publish the first reproducible RTX 4090 benchmark.
- Cut `v0.1.0-alpha` with `doctor`, `recommend`, `install`, `start`, `stop`, `status`, and `bench`.

## Week 3: alpha hardening

- Recruit 20 testers: 10 Korean and 10 international.
- Track time to first token, step success, error category, and manual intervention.
- Fix installation, diagnostics, security, and documentation issues only. No new features.

## Week 4: launch

- Release v0.1 after the launch gate passes.
- Enable GitHub Discussions for Help, Hardware, Benchmarks, Showcase, and Ideas.
- Build a minimal benchmark leaderboard only after report validation is reliable.
- Lead launch content with benchmark data, not installation claims.

## Public launch gate

- 20 alpha testers
- At least 16 successful installs
- At least 80% end-to-end success
- Median setup time below 15 minutes
- Zero known destructive bugs
- Reproducible benchmark results
- Complete quickstart and security documentation


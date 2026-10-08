# Benchmark methodology v1

OpenLocal benchmarks the same OpenAI-compatible streaming workload across concurrency levels so results retain their runtime context.

## Procedure

1. Record a privacy-filtered hardware snapshot and the installed profile/runtime settings.
2. Run one unmeasured warm-up request.
3. Run measured levels at concurrency 1, 2, 4, 8, and 16 by default.
4. Run at least the configured request count or the concurrency level, whichever is greater.
5. Sample NVIDIA memory use and GPU utilization during every level.
6. Save the versioned report atomically.

The workload uses temperature 0, seed 42, a fixed output limit, and a versioned prompt. Reports store the prompt SHA-256 and workload id, not prompt content.

## Metrics

- **TTFT:** request start to first non-empty streamed content delta.
- **ITL:** mean interval between non-empty content deltas for each request, summarized as p50/p95.
- **Output tokens/s:** API-reported completion tokens divided by level wall time.
- **Requests/s:** completed requests divided by level wall time.
- **Latency:** end-to-end request duration, summarized as p50/p95.
- **VRAM and GPU utilization:** peak and mean values from `nvidia-smi` samples.

When the endpoint omits streamed usage, OpenLocal falls back to counting non-empty stream chunks and records `stream_chunk_fallback`. Such results are not token-accurate and must not be compared as if they used API token counts.

Recommended concurrency maximizes measured throughput relative to p95 TTFT. This is an initial deterministic heuristic, not a universal service-level objective.

## Reproducibility limits

Driver version, image digest/tag, model identity, quantization, context, concurrency, thermals, power limits, and background GPU activity can materially change results. A report without its runtime and hardware sections is invalid.


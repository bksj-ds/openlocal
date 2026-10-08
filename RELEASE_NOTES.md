# Release notes

## 0.1.0-alpha.1

- Added Ubuntu 22.04/24.04 and Windows 10 21H2+/Windows 11 WSL2 hardware diagnostics.
- Added JSON doctor snapshots and NVIDIA VRAM detection.
- Added validated YAML model/runtime profiles and FAST/BALANCED/MAX QUALITY recommendations.
- Added secure, pinned vLLM and optional Open WebUI Compose generation.
- Added install, first-token verification, start, stop, status, logs, and pinned update workflows.
- Added reproducible streaming benchmarks for TTFT, ITL, token throughput, requests/s, latency, VRAM, and GPU utilization.
- Added atomic JSON reports and explicit opt-in benchmark submission with privacy validation.

Known limitation: GPU integration has unit/fake-endpoint coverage but requires supported physical alpha machines for release-gate validation.


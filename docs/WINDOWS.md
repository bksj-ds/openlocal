# Windows support

OpenLocal supports Windows through Linux GPU containers on WSL2. It does not use community Windows-native vLLM forks.

## Supported path

- Windows 10 21H2 (build 19044) or newer, or Windows 11
- NVIDIA GPU and a current Windows NVIDIA driver with WSL CUDA support
- Current WSL2 with at least one version 2 distribution
- Docker Desktop configured to use the WSL2 backend and Linux containers
- Docker Compose v2

Useful checks in PowerShell:

```powershell
wsl --version
wsl --list --verbose
docker version
docker compose version
openlocal doctor
```

The Windows host does not need a separate `nvidia-container-toolkit` command when using Docker Desktop's WSL2 GPU path. Users running Docker Engine directly inside their own WSL distribution do need to configure the toolkit inside that distribution.

## Why WSL2

vLLM's supported GPU operating system is Linux and its official Windows guidance points users to WSL. Docker Desktop exposes NVIDIA GPU compute to Linux containers only through the WSL2 backend. Keeping the runtime inside the same Linux container on Ubuntu and Windows also makes profiles and benchmark methodology comparable.

## Storage guidance

OpenLocal will use a Docker named volume for the model cache by default. This avoids slow model access through `/mnt/c` and prevents machine-specific Windows paths from entering Compose files or benchmark reports.

## References

- [vLLM GPU installation](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
- [Docker Desktop GPU support](https://docs.docker.com/desktop/features/gpu/)
- [Docker Desktop WSL2 backend](https://docs.docker.com/desktop/features/wsl/)
- [Microsoft: Enable NVIDIA CUDA on WSL2](https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl)
- [NVIDIA CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/)

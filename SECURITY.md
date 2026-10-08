# Security policy

OpenLocal is pre-alpha software and does not yet have a stable security-support window.

## Reporting a vulnerability

Do not publish credentials, private benchmark data, or an exploitable vulnerability in a public issue. After the public GitHub repository is created, use GitHub's private vulnerability reporting feature. Until then, contact the repository owner privately.

Include the affected version, operating system, reproduction steps, impact, and any proposed mitigation. Please omit real access tokens, hostnames, usernames, prompts, and model outputs.

## Security invariants

- Generated services bind to `127.0.0.1` by default.
- Network exposure requires an explicit user action and a clear warning.
- No telemetry or automatic benchmark upload.
- Submitted benchmark payloads exclude prompts and local identity.
- Images and dependencies are version-pinned and reviewed before updates.
- Secrets are supplied at runtime and are never rendered into tracked files.
- Host mounts and container privileges are kept to the minimum required.
- Destructive host changes require a preview and explicit confirmation.


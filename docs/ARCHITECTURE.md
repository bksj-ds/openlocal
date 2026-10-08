# Architecture

OpenLocal treats configuration and benchmark provenance as first-class data.

```text
doctor snapshot
      |
      v
profile matcher -> selected hardware/model/runtime profile
      |                         |
      v                         v
Compose renderer          benchmark manifest
      |                         |
      v                         v
OpenAI-compatible API -> measurements -> local JSON report
```

## Boundaries

- **CLI** owns inspection, matching, orchestration, validation, and reporting.
- **Profiles** own hardware constraints and runtime configuration. They are reviewable data, not hidden code branches.
- **vLLM** owns inference. Its OpenAI-compatible API is the v0.1 runtime boundary.
- **Open WebUI** is optional and independently maintained.
- **Benchmark storage** starts as local JSON. Remote submission is a later, explicit operation.

## Lessons retained from `llm-gateway`

The initial design reuses operational lessons, not application-specific files: bind inference ports to loopback, pin container versions, preserve the Hugging Face cache, expose runtime limits as profile data, and validate first-token behavior through the OpenAI-compatible endpoint.

No credentials, machine-specific paths, gateway database services, or private model configuration are copied from the source repository.


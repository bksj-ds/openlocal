# Non-goals for v0.1

OpenLocal is not a general-purpose AI platform. The following features are explicitly outside the v0.1 scope:

- A custom inference engine
- A custom Web UI
- A custom vector database
- RAG
- An agent framework
- MCP
- Image generation
- Speech
- Kubernetes
- Multi-node inference
- SSO
- Billing

Open WebUI may be orchestrated as an optional, independently maintained frontend. vLLM is the first inference backend. Neither becomes OpenLocal-owned product surface.

Proposals in these areas should be deferred until real v0.1 usage shows that they are required for the core loop: hardware detection, recommendation, execution, and benchmarking.


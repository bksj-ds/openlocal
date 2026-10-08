# Model/runtime profiles

Model identity, fit estimates, backend, context, memory utilization, and concurrency belong in validated profiles rather than conditional application code.

Profiles use schema version 1 and are checked by `openlocal recommend`. Memory estimates start as `provisional`; change them to `benchmarked` only with a reproducible OpenLocal report for the same model/runtime configuration.

Override the built-in directory during development with:

```bash
openlocal recommend --profiles ./my-profiles
```

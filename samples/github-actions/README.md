# GitHub Actions samples

Active CI is enabled at [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (lint, pytest, Docker build, no push).

This folder keeps reference copies for forks or custom workflows.

## Local equivalent

```bash
ruff check .
pytest tests/unit -q
pytest tests/integration -q -m integration
docker build -t rada:local .
```

See [docs/runbook-production.md](../../docs/runbook-production.md) for deploy and CI notes.

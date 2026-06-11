# Contributing to RADA

Thank you for your interest in RADA. This project is a showcase-quality risk-aware decision platform.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/unit -m "not gpu and not integration"
ruff check .
```

Requires **Python 3.11+**.

## Branch policy

- Target `develop` for changes; `main` is release-stable.
- Keep commits focused (CI, feature area, docs).

## BYOK / secrets

- Runtime LLM keys via environment variables only (`OPENAI_API_KEY`, etc.).
- Never commit credentials or real API keys.
- Default provider is `mock` for tests and CI.

## Tests

- Unit tests must pass on GitHub Actions free tier (CPU, no GPU).
- Integration and Docker builds: `workflow_dispatch` in `.github/workflows/integration.yml`.

## Pull requests

1. Describe the decision pipeline or subsystem touched.
2. Link vault task ID if applicable (e.g. `IMP-LLM-01-07`).
3. Ensure `ruff check` and unit tests pass.

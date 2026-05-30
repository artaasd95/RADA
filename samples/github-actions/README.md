# GitHub Actions samples (opt-in)

Ready-to-run workflow templates for RADA. **They are not enabled on RADA `main` during MVP.**

## MVP policy

- Production deploy and recovery **must not depend solely on GitHub Actions** (see [docs/runbook.md](../../docs/runbook.md)).
- These files are **samples only** under `samples/github-actions/`.
- No active `.github/workflows/` is committed to `main` until the team explicitly opts in post-MVP.

## Copy-enable steps

1. Copy workflows into the repo root:

   ```bash
   mkdir -p .github/workflows
   cp samples/github-actions/ci.yml .github/workflows/ci.yml
   cp samples/github-actions/lint.yml .github/workflows/lint.yml
   ```

2. Push to a branch and open a PR, or enable on your fork first.

3. Ensure branch protection (if used) lists the `CI` and/or `Lint` checks after the first successful run.

## What each workflow does

| File | Purpose |
|------|---------|
| `ci.yml` | `ruff check`, unit tests, integration smoke (`pytest -m integration`) |
| `lint.yml` | `ruff check` and `ruff format --check` |

Both use Python 3.11 and `pip install -e ".[dev]"` (CI job only).

## Local equivalent

```bash
ruff check .
pytest tests/unit -q
pytest tests/integration -q -m integration
```

Local runs satisfy the same gates without Actions.

# Post-MVP demo guide

Walkthrough for the **data** and **search** layers after core loop shipping. All examples use fixtures or synthetic events — not production markets.

## Prerequisites

```bash
pip install -e ".[dev]"
docker compose up -d
```

## Data layer demo

1. Run the decision loop (in-memory):

```bash
pytest tests/integration/test_data_layer.py -q -m integration
```

2. Batch export reflection artifacts:

```bash
python scripts/export_reflection.py --synthetic-count 5 --output-dir ./tmp/export-demo
```

Outputs:

- `tmp/export-demo/exports/reflection/<batch>.jsonl`
- `tmp/export-demo/feedback/outgoing/<batch>.jsonl`

3. Pipeline config smoke:

```bash
pytest tests/unit/test_rada_pipeline_config.py -q
```

## Search layer demo

```bash
python examples/search_demo.py
python scripts/benchmark_search.py
pytest tests/unit/test_search_eval.py tests/unit/test_risk_selection.py -q
```

Enable search in the decision path:

```bash
set RADA_SEARCH_ENABLED=true
pytest tests/integration/test_search_decision_integration.py -q -m integration
```

## Streamlit dashboard (optional)

```bash
pip install streamlit
streamlit run apps/streamlit/dashboard.py
```

The dashboard reads in-process metrics and displays synthetic P&L / decision counters for local demos.

## Monitoring overlay

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Scrape `http://localhost:8000/metrics` (app must be running via uvicorn).

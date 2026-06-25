# BYOK Reasoning Pipeline — Initial Test Results

**Date:** 2026-06-25  
**Scope:** Inference and usage pipeline only (no training)  
**Model:** `gpt-oss-20b`  
**Endpoint:** OpenAI-compatible FreeLLM (`freellmapi.txt`)

---

## Summary

| Metric | Value |
|--------|-------|
| Tests run | 7 |
| Passed | 7 |
| Failed | 0 |
| Skipped | 0 |
| Total elapsed | 15.55 s |
| Overall | **PASS** |

Machine-readable report: `byok_pipeline_test_report.json`  
Re-run command: `python scripts/test_byok_pipeline.py`

---

## Configuration

| Setting | Value |
|---------|-------|
| LLM config | `configs/llm_freellm.yaml` |
| Provider | `custom` (OpenAI-compatible HTTP adapter) |
| Base URL | `http://127.0.0.1:3001` |
| API key env var | `FREELLM_API_KEY` |
| Credentials file | `freellmapi.txt` (not committed) |
| Reasoner mode | `byok` / `real` |
| Python env | `torchgpu` (Python 3.13.9) |

**Note:** `base_url` must omit the `/v1` suffix. The adapter appends `/v1/chat/completions` internally.

```yaml
# configs/llm_freellm.yaml
provider: custom
model_id: gpt-oss-20b
base_url: http://127.0.0.1:3001
api_key_env: FREELLM_API_KEY
```

---

## Test Results

### 1. LLM provider direct completion

- **Status:** PASS
- **Backend:** `custom`
- **Latency:** ~2567 ms
- **Tokens:** prompt=317, completion=121
- **Verifies:** YAML config load, API key resolution, HTTP call to FreeLLM endpoint

### 2. Reasoning prompt assembly

- **Status:** PASS
- **Prompt size:** 210 characters
- **Verifies:** `build_reasoning_prompt()` includes verified numerical context and market symbol

### 3. RealReasoner inference

- **Status:** PASS
- **Model trace:** `custom:gpt-oss-20b`
- **Rationale length:** ~962 characters
- **Faithfulness score:** 0.8 (non-mock provider)
- **Verifies:** BYOK reasoner produces a real LLM rationale from a `MarketEvent`

### 4. Decision loop end-to-end

- **Status:** PASS
- **Sample event:** BTCUSD @ 67250.5, volume 2.4
- **Decision ID:** `79b82c48-1860-462a-8b82-0978bde7f076`
- **Direction:** HOLD
- **Verifies:** calc → reason → risk gate → persist through `DecisionLoop`

### 5. Bootstrap once

- **Status:** PASS
- **Decision ID:** `ef45c6c0-b4fd-4ec8-a058-451b52cb7990`
- **Verifies:** Synthetic event bus → single decision via `run_bootstrap_once()`

### 6. FastAPI `/ingest`

- **Status:** PASS
- **Decision ID:** `f207595f-1183-4a71-a012-7467dd687d0e`
- **Direction:** HOLD
- **Verifies:** HTTP ingest through full app lifespan (decision loop, reflection enqueue, metrics)

### 7. Metrics endpoint

- **Status:** PASS
- **Response size:** 882 bytes
- **Verifies:** `/metrics` returns Prometheus-style RADA metrics

---

## Pipeline Verified

```
MarketEvent
  → build_reasoning_prompt()     [verified context protected]
  → CustomAdapter.complete()     [gpt-oss-20b @ FreeLLM]
  → RealReasoner.reason()        [DecisionTrace]
  → DecisionLoop.process_one()   [calc + risk gate + persist]
  → ReflectionLoop.enqueue()     [/ingest path]
  → /metrics                     [observability]
```

---

## Issues Found During Initial Run

| Issue | Impact | Resolution |
|-------|--------|------------|
| `InMemoryEventBus` missing `close()` | `bootstrap_once` failed | Added no-op `close()` in `src/rada/data/bus.py` |
| `/ingest` returned `flagged: bool` | FastAPI response validation error | Coerced to `"true"` / `"false"` strings in `src/rada/main.py` |

---

## Reproduce

```powershell
conda activate torchgpu
cd g:\repositories\RADA

# Set key from freellmapi.txt
$env:FREELLM_API_KEY="<your-key>"

python scripts/test_byok_pipeline.py
```

### Run the API with BYOK

```powershell
$env:FREELLM_API_KEY="<your-key>"
$env:RADA_REASONER_MODE="byok"
$env:RADA_LLM_CONFIG_PATH="configs/llm_freellm.yaml"
uvicorn rada.main:app --reload
```

---

## Out of Scope (not tested)

- Training / reflection fine-tuning (`reflection_train.py`, Unsloth)
- GPU adapter loading
- Ollama local fallback (endpoint at `localhost:11434` was not running; BYOK primary path used)
- LiteLLM cloud fallback (`configs/llm_cloud.yaml`)

---

## Artifacts

| File | Description |
|------|-------------|
| `byok-pipeline-initial-results.md` | This document |
| `byok_pipeline_test_report.json` | JSON test report |
| `scripts/test_byok_pipeline.py` | Repeatable pipeline test script |
| `configs/llm_freellm.yaml` | BYOK provider config |

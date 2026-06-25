#!/usr/bin/env python3
"""End-to-end BYOK reasoning pipeline test (inference only, no training)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_ROOT))

# Optional asyncpg mock for stores that import it transitively
try:
    import asyncpg_mock  # noqa: F401

    sys.modules.setdefault("asyncpg", asyncpg_mock)
except ImportError:
    pass

from fastapi.testclient import TestClient

from rada.adapters.real_reasoner import RealReasoner
from rada.core.decision_loop import DecisionLoop, HoldPolicy, PassThroughRiskOptimizer
from rada.core.reasoner_loop import ReasonerLoop
from rada.core.search_loop import SearchLoop
from rada.data.storage import InMemoryDecisionStore
from rada.llm_integration.factory import create_llm_provider
from rada.llm_integration.prompts import build_reasoning_prompt
from rada.main import RuntimeSettings, app, build_decision_loop, build_reasoner, run_bootstrap_once
from rada.schemas import MarketEvent

CONFIG_PATH = REPO_ROOT / "configs" / "llm_freellm.yaml"
MODEL_ID = "gpt-oss-20b"
SAMPLE_EVENT = MarketEvent(
    symbol="BTCUSD",
    price=67250.5,
    volume=2.4,
    timestamp=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
)


def _ok(name: str, detail: str = "") -> dict:
    return {"name": name, "status": "PASS", "detail": detail}


def _fail(name: str, detail: str) -> dict:
    return {"name": name, "status": "FAIL", "detail": detail}


def _skip(name: str, detail: str) -> dict:
    return {"name": name, "status": "SKIP", "detail": detail}


async def test_llm_provider_direct() -> dict:
    name = "llm_provider_direct"
    if not os.environ.get("FREELLM_API_KEY"):
        return _skip(name, "FREELLM_API_KEY not set")
    provider = create_llm_provider(CONFIG_PATH)
    try:
        completion = await provider.complete(
            "Respond with one short sentence about market risk.",
            MODEL_ID,
            max_tokens=64,
        )
        if completion.backend_id != "custom":
            return _fail(name, f"expected custom backend, got {completion.backend_id}")
        if not completion.text.strip():
            return _fail(name, "empty completion text")
        if completion.model_id != MODEL_ID:
            return _fail(name, f"model mismatch: {completion.model_id}")
        return _ok(
            name,
            f"latency={completion.latency_ms:.0f}ms tokens={completion.token_usage}",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))
    finally:
        if hasattr(provider, "aclose"):
            await provider.aclose()


async def test_reasoning_prompt() -> dict:
    name = "reasoning_prompt_assembly"
    try:
        from rada.llm_integration.config import LLMConfig
        import yaml

        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        config = LLMConfig.model_validate(raw)
        ctx = build_reasoning_prompt(
            symbol=SAMPLE_EVENT.symbol,
            price=SAMPLE_EVENT.price,
            verified_context={"price": SAMPLE_EVENT.price, "volume": SAMPLE_EVENT.volume},
            model_id=MODEL_ID,
            config=config,
        )
        if "verified_context" not in ctx.text.lower() and "67250" not in ctx.text:
            return _fail(name, "verified context missing from assembled prompt")
        if SAMPLE_EVENT.symbol not in ctx.text:
            return _fail(name, "symbol missing from prompt")
        return _ok(name, f"prompt_chars={len(ctx.text)}")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


async def test_real_reasoner() -> dict:
    name = "real_reasoner_inference"
    if not os.environ.get("FREELLM_API_KEY"):
        return _skip(name, "FREELLM_API_KEY not set")
    try:
        reasoner = RealReasoner.from_config_paths(CONFIG_PATH)
        trace = await reasoner.reason(SAMPLE_EVENT)
        if "mock" in trace.model_name:
            return _fail(name, f"unexpected mock model: {trace.model_name}")
        if not trace.rationale.strip():
            return _fail(name, "empty rationale")
        if trace.faithfulness_score < 0.5:
            return _fail(name, f"low faithfulness: {trace.faithfulness_score}")
        return _ok(
            name,
            f"model={trace.model_name} rationale_len={len(trace.rationale)}",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


async def test_decision_loop() -> dict:
    name = "decision_loop_e2e"
    if not os.environ.get("FREELLM_API_KEY"):
        return _skip(name, "FREELLM_API_KEY not set")
    try:
        settings = RuntimeSettings(
            reasoner_mode="byok",
            llm_config_path=str(CONFIG_PATH),
            data_store_mode="inmemory",
            event_bus_mode="inmemory",
        )
        store = InMemoryDecisionStore()
        loop = build_decision_loop(store, settings=settings)
        decision = await loop.process_one(SAMPLE_EVENT)
        if not decision.decision_id:
            return _fail(name, "missing decision_id")
        if not decision.trace.rationale.strip():
            return _fail(name, "missing trace rationale")
        if decision.proposed_action is None:
            return _fail(name, "missing proposed_action")
        return _ok(
            name,
            f"decision_id={decision.decision_id} direction={decision.proposed_action.direction.value}",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


async def test_bootstrap_once() -> dict:
    name = "bootstrap_once_byok"
    if not os.environ.get("FREELLM_API_KEY"):
        return _skip(name, "FREELLM_API_KEY not set")
    try:
        settings = RuntimeSettings(
            reasoner_mode="byok",
            llm_config_path=str(CONFIG_PATH),
            data_store_mode="inmemory",
            event_bus_mode="inmemory",
        )
        decision = await run_bootstrap_once(event_count=1, settings=settings)
        return _ok(name, f"decision_id={decision.decision_id}")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


def test_fastapi_ingest() -> dict:
    name = "fastapi_ingest_byok"
    if not os.environ.get("FREELLM_API_KEY"):
        return _skip(name, "FREELLM_API_KEY not set")
    os.environ["RADA_REASONER_MODE"] = "byok"
    os.environ["RADA_LLM_CONFIG_PATH"] = str(CONFIG_PATH)
    os.environ["RADA_DATA_STORE_MODE"] = "inmemory"
    os.environ["RADA_EVENT_BUS_MODE"] = "inmemory"
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            if health.status_code != 200:
                return _fail(name, f"/health returned {health.status_code}")

            payload = {
                "symbol": SAMPLE_EVENT.symbol,
                "price": SAMPLE_EVENT.price,
                "volume": SAMPLE_EVENT.volume,
                "timestamp": SAMPLE_EVENT.timestamp.isoformat(),
            }
            resp = client.post("/ingest", json=payload)
            if resp.status_code != 200:
                return _fail(name, f"/ingest returned {resp.status_code}: {resp.text}")
            body = resp.json()
            if "decision_id" not in body:
                return _fail(name, f"missing decision_id in {body}")
            return _ok(name, f"decision_id={body['decision_id']} direction={body.get('direction')}")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


def test_metrics_endpoint() -> dict:
    name = "metrics_endpoint"
    try:
        with TestClient(app) as client:
            resp = client.get("/metrics")
            if resp.status_code != 200:
                return _fail(name, f"status={resp.status_code}")
            if "rada" not in resp.text.lower():
                return _fail(name, "no rada metrics in body")
            return _ok(name, f"bytes={len(resp.content)}")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, str(exc))


async def main() -> int:
    print("=" * 80)
    print("RADA BYOK REASONING PIPELINE TEST")
    print("=" * 80)
    print(f"Config: {CONFIG_PATH}")
    print(f"Model:  {MODEL_ID}")
    print(f"API key set: {bool(os.environ.get('FREELLM_API_KEY'))}")
    print()

    started = time.perf_counter()
    results: list[dict] = []

    for coro in (
        test_llm_provider_direct(),
        test_reasoning_prompt(),
        test_real_reasoner(),
        test_decision_loop(),
        test_bootstrap_once(),
    ):
        results.append(await coro)

    results.append(test_fastapi_ingest())
    results.append(test_metrics_endpoint())

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    elapsed = time.perf_counter() - started

    print("Results:")
    for r in results:
        sym = {"PASS": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[r["status"]]
        detail = f" — {r['detail']}" if r.get("detail") else ""
        print(f"  {sym} {r['name']}: {r['status']}{detail}")

    print()
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped ({elapsed:.1f}s)")

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "config": str(CONFIG_PATH),
        "model_id": MODEL_ID,
        "elapsed_seconds": round(elapsed, 2),
        "summary": {"passed": passed, "failed": failed, "skipped": skipped},
        "results": results,
    }
    report_path = REPO_ROOT / "byok_pipeline_test_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {report_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

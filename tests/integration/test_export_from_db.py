from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.core.reflection_loop import stub_outcome
from rada.data.cards import DecisionExportRow
from rada.data.export_batch import export_decisions
from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.schemas import MarketEvent

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_from_inmemory_store_matches_schema(tmp_path: Path) -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    for index in range(3):
        event = MarketEvent(
            symbol="BTCUSD",
            price=1000.0 + index,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, 12, index, tzinfo=UTC),
        )
        await loop.process_one(event)

    decisions = await store.list_decisions(limit=10)
    assert len(decisions) == 3

    decisions = [d.model_copy(update={"outcome": stub_outcome(d)}) for d in decisions]
    summary = export_decisions(decisions, output_dir=tmp_path, batch_id="from-db-test")
    reflection = Path(summary["reflection"])
    lines = reflection.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3

    row = DecisionExportRow.model_validate(json.loads(lines[0]))
    assert row.decision_id
    assert row.trigger_event.symbol == "BTCUSD"
    assert row.metadata.export_batch_id == "from-db-test"
    assert row.metadata.lineage.ingest_source == "action_db"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqlite_store_list_decisions_since_filter(tmp_path: Path) -> None:
    db_path = tmp_path / "export.db"
    store = SQLiteDecisionStore(f"sqlite:///{db_path}")
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    event = MarketEvent(
        symbol="ETHUSD",
        price=3200.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 2, tzinfo=UTC),
    )
    await loop.process_one(event)

    since = datetime(2026, 6, 1, tzinfo=UTC)
    found = await store.list_decisions(since=since)
    assert len(found) == 1


@pytest.mark.integration
def test_export_cli_from_db_with_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "cli.db"
    import os

    env = {
        **dict(os.environ),
        "RADA_DATA_STORE_MODE": "sqlite",
        "RADA_SQLITE_URL": f"sqlite:///{db_path}",
    }
    seed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio; from datetime import UTC, datetime; "
                "from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, "
                "PassThroughRiskOptimizer; from rada.data.storage import SQLiteDecisionStore; "
                "from rada.schemas import MarketEvent; "
                f"async def main():\n"
                f"  store = SQLiteDecisionStore('sqlite:///{db_path.as_posix()}');\n"
                "  loop = DecisionLoop(reasoner=NoOpReasoner(), policy=HoldPolicy(), "
                "risk_optimizer=PassThroughRiskOptimizer(), data_store=store);\n"
                "  await loop.process_one(MarketEvent(symbol='SYN', price=1.0, volume=1.0, "
                "timestamp=datetime(2026,6,3,tzinfo=UTC)));\n"
                "asyncio.run(main())"
            ),
        ],
        cwd=_REPO_ROOT,
        env={**env, "PYTHONPATH": str(_REPO_ROOT / "src")},
        check=True,
        capture_output=True,
        text=True,
    )
    assert seed.returncode == 0

    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "export_reflection.py"),
            "--from-db",
            "--output-dir",
            str(out_dir),
            "--batch-id",
            "cli-batch",
        ],
        cwd=_REPO_ROOT,
        env={**env, "PYTHONPATH": str(_REPO_ROOT / "src")},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    reflection = out_dir / "exports" / "reflection" / "cli-batch.jsonl"
    assert reflection.exists()

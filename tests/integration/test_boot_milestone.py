from pathlib import Path

import pytest

from rada.data.storage import SQLiteDecisionStore
from rada.main import RuntimeSettings, run_bootstrap_once


@pytest.mark.integration
@pytest.mark.asyncio
async def test_boot_to_one_persisted_decision(tmp_path: Path) -> None:
    db_file = tmp_path / "rada-milestone.db"
    settings = RuntimeSettings(
        event_bus_mode="inmemory",
        sqlite_url=f"sqlite:///{db_file.as_posix()}",
    )

    decision = await run_bootstrap_once(event_count=1, settings=settings)
    store = SQLiteDecisionStore(settings.sqlite_url)
    restored = await store.get_decision(decision.decision_id)

    assert decision.decision_id
    assert restored is not None
    assert restored.decision_id == decision.decision_id

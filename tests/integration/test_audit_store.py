from __future__ import annotations

import sqlite3

import pytest

from rada.audit.schemas import AuditEvent, AuditEventType
from rada.audit.store import AuditStore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_store_append_only_on_fresh_db(tmp_path) -> None:
    db = str(tmp_path / "fresh.db")
    store = AuditStore(db_path=db)
    await store.append(
        AuditEvent(event_type=AuditEventType.DECISION, decision_id="d1", payload_after={"ok": True})
    )
    events = await store.list_for_decision("d1")
    assert len(events) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_store_rejects_delete_on_existing_db(tmp_path) -> None:
    db = str(tmp_path / "existing.db")
    store = AuditStore(db_path=db)
    await store.ensure_ready()
    await store.append(AuditEvent(event_type=AuditEventType.CALC, decision_id="d2"))

    def _try_delete() -> None:
        with sqlite3.connect(db) as conn:
            conn.execute("DELETE FROM audit_events")

    with pytest.raises(sqlite3.OperationalError, match="append-only"):
        _try_delete()

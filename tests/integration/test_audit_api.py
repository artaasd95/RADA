from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from rada.audit.schemas import AuditEvent, AuditEventType
from rada.audit.store import AuditStore
from rada.main import app


@pytest.mark.integration
def test_audit_decision_chain_reconstructable(tmp_path) -> None:
    db = str(tmp_path / "audit.db")
    store = AuditStore(db_path=db)
    decision_id = "dec-test-001"

    async def _seed():
        await store.append(
            AuditEvent(
                decision_id=decision_id,
                event_type=AuditEventType.CALC,
                payload_after={"cvar": 0.03},
            )
        )
        await store.append(
            AuditEvent(
                decision_id=decision_id,
                event_type=AuditEventType.DECISION,
                payload_after={"direction": "HOLD"},
            )
        )

    import asyncio

    asyncio.run(_seed())

    app.state.audit_store = store
    client = TestClient(app)
    resp = client.get(f"/audit/decision/{decision_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["events"]) == 2
    types = {e["event_type"] for e in body["events"]}
    assert types == {"CALC", "DECISION"}


@pytest.mark.integration
def test_audit_export_ndjson(tmp_path) -> None:
    db = str(tmp_path / "audit2.db")
    store = AuditStore(db_path=db)

    async def _seed():
        await store.append(
            AuditEvent(
                event_type=AuditEventType.RISK_GATE,
                timestamp=datetime(2026, 6, 1, tzinfo=UTC),
            )
        )

    import asyncio

    asyncio.run(_seed())
    app.state.audit_store = store
    client = TestClient(app)
    resp = client.get("/audit/export?from=2026-06-01T00:00:00Z")
    assert resp.status_code == 200
    lines = [ln for ln in resp.text.strip().splitlines() if ln]
    assert len(lines) >= 1

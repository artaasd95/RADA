from __future__ import annotations

import time

import pytest

from rada.audit.schemas import AuditEventType
from rada.audit.writer import AuditWriter


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audit_writer_hot_path_overhead_under_budget(tmp_path) -> None:
    from rada.audit.store import AuditStore

    writer = AuditWriter(store=AuditStore(db_path=str(tmp_path / "perf.db")))
    writer.start()

    # simulate hot-path emit only (no await)
    start = time.perf_counter()
    for _ in range(100):
        writer.emit(AuditEventType.CALC, decision_id="d1", payload_after={"v": 1})
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_emit_ms = elapsed_ms / 100
    assert per_emit_ms < 5.0, f"per emit {per_emit_ms:.3f}ms exceeds 5ms budget"

    await writer.stop()

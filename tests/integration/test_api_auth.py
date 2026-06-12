from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rada.audit.store import AuditStore
from rada.feedback.store import FeedbackStore
from rada.main import app


@pytest.mark.integration
def test_audit_requires_api_key_in_production(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("RADA_ENV", "production")
    monkeypatch.setenv("RADA_API_KEY", "secret-key")
    store = AuditStore(db_path=str(tmp_path / "audit.db"))
    app.state.audit_store = store
    client = TestClient(app)

    denied = client.get("/audit/export")
    assert denied.status_code == 401

    allowed = client.get("/audit/export", headers={"X-API-Key": "secret-key"})
    assert allowed.status_code == 200


@pytest.mark.integration
def test_feedback_submit_requires_api_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("RADA_ENV", "production")
    monkeypatch.setenv("RADA_API_KEY", "secret-key")
    app.state.feedback_store = FeedbackStore(db_path=str(tmp_path / "fb.db"))
    client = TestClient(app)

    payload = {
        "decision_id": "dec-auth",
        "action": "FLAG",
        "note": "test",
        "reviewer": "tester",
    }
    denied = client.post("/feedback/submit", json=payload)
    assert denied.status_code == 401

    allowed = client.post(
        "/feedback/submit",
        json=payload,
        headers={"X-API-Key": "secret-key"},
    )
    assert allowed.status_code == 200

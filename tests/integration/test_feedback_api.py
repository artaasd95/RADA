from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rada.feedback.store import FeedbackStore
from rada.main import app


@pytest.mark.integration
def test_feedback_submit_and_pending(tmp_path) -> None:
    store = FeedbackStore(db_path=str(tmp_path / "fb.db"))
    app.state.feedback_store = store
    client = TestClient(app)

    payload = {
        "decision_id": "dec-100",
        "action": "FLAG",
        "note": "CVaR breach review",
        "reviewer": "tester",
    }
    resp = client.post("/feedback/submit", json=payload)
    assert resp.status_code == 200

    pending = client.get("/feedback/pending")
    assert pending.status_code == 200
    items = pending.json()["pending"]
    assert any(i["decision_id"] == "dec-100" for i in items)

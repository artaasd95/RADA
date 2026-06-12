"""RADA dashboard with metrics and human review queue."""

from __future__ import annotations

import json
import os

import httpx
import streamlit as st

from rada.utils.metrics import get_metrics_snapshot

API_URL = os.getenv("RADA_API_URL", "http://localhost:8000")
API_KEY = os.getenv("RADA_API_KEY", "")


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def _submit(*, client_action: str, decision_id: str, note: str) -> None:
    payload = {
        "decision_id": decision_id,
        "action": client_action,
        "note": note or f"{client_action} via Streamlit",
        "reviewer": "streamlit",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{API_URL}/feedback/submit",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
        st.success(f"{client_action} submitted for {decision_id}")
    except httpx.HTTPError as exc:
        st.error(str(exc))


st.set_page_config(page_title="RADA", layout="wide")
st.title("RADA — review dashboard")

tab_metrics, tab_review = st.tabs(["Metrics", "Review Queue"])

with tab_metrics:
    snapshot = get_metrics_snapshot()
    st.subheader("In-process metrics")
    st.json(snapshot)
    st.caption("Process events via `POST /ingest` to move counters.")

with tab_review:
    st.subheader("Flagged decisions")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_URL}/feedback/pending", headers=_headers())
            response.raise_for_status()
            try:
                pending = response.json().get("pending", [])
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON from feedback API: {exc}")
                pending = []
    except httpx.HTTPError as exc:
        st.error(f"Cannot reach feedback API at {API_URL}: {exc}")
        pending = []

    if not pending:
        st.info("No flagged decisions. Auto-flag rules: CVaR breach, low LLM confidence.")
    for item in pending:
        with st.expander(f"{item['decision_id']} — {item['action']}"):
            st.write(item.get("note", ""))
            note = st.text_input("Reviewer note", key=f"note-{item['feedback_id']}")
            col1, col2 = st.columns(2)
            if col1.button("Approve", key=f"approve-{item['feedback_id']}"):
                _submit(client_action="APPROVE", decision_id=item["decision_id"], note=note)
            if col2.button("Reject", key=f"reject-{item['feedback_id']}"):
                _submit(client_action="REJECT", decision_id=item["decision_id"], note=note)

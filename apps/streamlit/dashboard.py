"""Lightweight Streamlit dashboard for API smoke tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx
import streamlit as st

API_URL = os.getenv("RADA_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("RADA_API_KEY", "")


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def _api_get(path: str) -> dict:
    with httpx.Client(timeout=12.0) as client:
        response = client.get(f"{API_URL}{path}", headers=_headers())
        response.raise_for_status()
        return response.json()


def _api_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=12.0) as client:
        response = client.post(f"{API_URL}{path}", json=payload, headers=_headers())
        response.raise_for_status()
        return response.json()


st.set_page_config(page_title="RADA Test Dashboard", layout="wide")
st.title("RADA Test Dashboard")
st.caption("Lightweight panel for smoke-testing API health, ingest, and review flows.")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.subheader("Environment")
    st.write(f"API URL: {API_URL}")
    st.write(f"API Key: {'configured' if API_KEY else 'not set'}")

with col_b:
    st.subheader("Health")
    if st.button("Check /health", use_container_width=True):
        try:
            health = _api_get("/health")
            st.success(f"Healthy: {health.get('status', 'unknown')}")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

with col_c:
    st.subheader("Bootstrap")
    if st.button("Run /bootstrap-demo", use_container_width=True):
        try:
            result = _api_post("/bootstrap-demo", {})
            st.success(f"Decision: {result.get('decision_id', 'n/a')}")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

st.divider()

st.subheader("Quick Ingest")
input_cols = st.columns(3)
symbol = input_cols[0].text_input("Symbol", value="BTCUSD")
price = input_cols[1].number_input("Price", value=62000.0, min_value=0.01, step=100.0)
volume = input_cols[2].number_input("Volume", value=1.0, min_value=0.0001, step=0.1)

if st.button("POST /ingest", use_container_width=True):
    payload = {
        "symbol": symbol.upper().strip(),
        "price": float(price),
        "volume": float(volume),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    try:
        result = _api_post("/ingest", payload)
        st.success(
            f"Decision: {result.get('decision_id', 'n/a')} | "
            f"Direction: {result.get('direction', 'n/a')} | "
            f"Flagged: {result.get('flagged', False)}"
        )
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))

st.divider()

st.subheader("Pending Review Queue")
if st.button("Refresh /feedback/pending"):
    st.rerun()

try:
    pending = _api_get("/feedback/pending").get("pending", [])
except Exception as exc:  # noqa: BLE001
    st.error(f"Cannot load pending queue: {exc}")
    pending = []

if not pending:
    st.info("No pending feedback items.")
else:
    for item in pending:
        with st.expander(f"{item.get('decision_id', 'unknown')} | {item.get('action', 'n/a')}"):
            st.write(item.get("note", ""))
            note = st.text_input(
                "Reviewer note",
                key=f"note-{item.get('feedback_id', item.get('decision_id', 'x'))}",
            )
            action_cols = st.columns(2)
            if action_cols[0].button("Approve", key=f"approve-{item.get('feedback_id', 'x')}"):
                try:
                    _api_post(
                        "/feedback/submit",
                        {
                            "decision_id": item["decision_id"],
                            "action": "APPROVE",
                            "note": note or "Approved from Streamlit test dashboard",
                            "reviewer": "streamlit-test",
                        },
                    )
                    st.success("Approve submitted")
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

            if action_cols[1].button("Reject", key=f"reject-{item.get('feedback_id', 'x')}"):
                try:
                    _api_post(
                        "/feedback/submit",
                        {
                            "decision_id": item["decision_id"],
                            "action": "REJECT",
                            "note": note or "Rejected from Streamlit test dashboard",
                            "reviewer": "streamlit-test",
                        },
                    )
                    st.success("Reject submitted")
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

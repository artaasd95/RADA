"""Minimal Streamlit dashboard for local post-MVP demos."""

from __future__ import annotations

import streamlit as st

from rada.utils.metrics import get_metrics_snapshot

st.set_page_config(page_title="RADA Demo", layout="wide")
st.title("RADA — data & search demo dashboard")

snapshot = get_metrics_snapshot()
st.subheader("In-process metrics")
st.json(snapshot)

st.caption(
    "Synthetic demo only. Run `uvicorn rada.main:app` and process events to move counters."
)

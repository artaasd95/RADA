# Human-in-the-loop validation

Expert review queue for flagged decisions.

## Feedback API

Requires `X-API-Key` when `RADA_API_KEY` is set.

- `POST /feedback/submit` — submit approve/reject/flag/annotate (server assigns `feedback_id` and timestamp)
- `GET /feedback/pending` — list deduplicated pending FLAG items

Example submit body:

```json
{
  "decision_id": "dec-100",
  "action": "APPROVE",
  "note": "Reviewed manually",
  "reviewer": "operator"
}
```

## Streamlit

```bash
streamlit run apps/streamlit/dashboard.py
```

Set `RADA_API_URL` and optional `RADA_API_KEY` for authenticated deployments.

Auto-flagging triggers on CVaR threshold breaches, low LLM confidence, and anomaly scores. Approved feedback flows into the reflection loop.

# Human-in-the-loop validation

Expert review queue for flagged decisions.

## Feedback API

- `POST /feedback/submit`
- `GET /feedback/pending`
- `POST /feedback/{id}/approve`

## Streamlit

```bash
streamlit run apps/streamlit/dashboard.py
```

Auto-flagging triggers on CVaR threshold breaches, low LLM confidence, and anomaly scores. Approved feedback flows into the reflection loop.

# Human feedback migration

Runtime DDL is applied by `rada.feedback.store.FeedbackStore.ensure_ready()`.

Table: `human_feedback` (append-only, DELETE blocked by trigger).

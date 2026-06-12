"""Auto-flag rules for human review queue."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rada.feedback.schemas import FeedbackAction, HumanFeedback
from rada.schemas import Decision


def should_auto_flag(decision: Decision, *, cvar_limit: float = 0.05) -> tuple[bool, str]:
    """Return (flag, reason) for CVaR breach or low LLM confidence."""
    cvar = decision.trace.verified_context.get("cvar")
    if cvar is None:
        cvar = decision.trace.synthetic_context.get("cvar")
    if cvar is not None and cvar > cvar_limit:
        return True, f"CVaR breach: {cvar:.4f} > {cvar_limit}"

    score = decision.trace.faithfulness_score
    if score is not None and score < 0.7:
        return True, f"Low LLM confidence: {score:.2f} < 0.70"

    cvar_impact = decision.proposed_action.cvar_impact
    if cvar_impact is not None and cvar_impact > cvar_limit:
        return True, f"Action CVaR impact {cvar_impact:.4f} exceeds limit"

    return False, ""


def build_flag_feedback(decision: Decision, reason: str) -> HumanFeedback:
    return HumanFeedback(
        feedback_id=str(uuid4()),
        decision_id=decision.decision_id,
        action=FeedbackAction.FLAG,
        note=reason,
        timestamp=datetime.now(tz=UTC),
        reviewer="auto-flag",
    )

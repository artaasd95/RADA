"""YAML-backed policy profile registry."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from rada.interfaces import BasePolicy
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction

_PROFILES_DIR = Path(__file__).resolve().parents[3] / "configs" / "policies"


class PolicyProfile(BaseModel):
    """Risk thresholds and sizing for a named policy profile."""

    name: str
    cvar_max: float = Field(gt=0)
    drawdown_max: float = Field(gt=0, le=1)
    size_scaling: float = Field(gt=0, le=2)


def load_profile(name: str) -> PolicyProfile:
    path = _PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"policy profile not found: {name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PolicyProfile.model_validate(data)


class RiskGatedPolicy(BasePolicy):
    """Wraps a base policy and enforces profile thresholds (breach → HOLD)."""

    def __init__(self, inner: BasePolicy, profile: PolicyProfile) -> None:
        self._inner = inner
        self._profile = profile

    @property
    def profile(self) -> PolicyProfile:
        return self._profile

    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        action = await self._inner.propose(event, trace)
        cvar = action.cvar_impact if action.cvar_impact is not None else 0.0
        if cvar > self._profile.cvar_max:
            return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=cvar)
        scaled_size = action.size * self._profile.size_scaling
        if scaled_size <= 0 and action.direction != ActionDirection.HOLD:
            return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=cvar)
        return action.model_copy(
            update={
                "size": scaled_size,
                "risk_adjusted_size": scaled_size,
            }
        )


def get_risk_gate(profile: PolicyProfile, inner: BasePolicy) -> RiskGatedPolicy:
    return RiskGatedPolicy(inner, profile)

"""Uncertainty quantification stubs for action-size control."""

from __future__ import annotations


def interval_action_size_stub(
    *,
    action_size: float,
    confidence: float = 0.9,
    calibration_error: float = 0.1,
) -> dict[str, float | str]:
    """Return a simple interval estimate around the proposed action size."""
    bounded_confidence = min(max(confidence, 0.5), 0.99)
    bounded_calibration = min(max(calibration_error, 0.0), 0.5)

    interval_width = (1.0 - bounded_confidence) + bounded_calibration
    lower = max(action_size * (1.0 - interval_width), 0.0)
    upper = max(action_size * (1.0 + interval_width), lower)

    return {
        "method": "interval_stub",
        "confidence": round(bounded_confidence, 6),
        "lower": round(lower, 6),
        "upper": round(upper, 6),
    }


def attach_interval_to_action(
    action_payload: dict[str, object],
    *,
    confidence: float = 0.9,
    calibration_error: float = 0.1,
) -> dict[str, object]:
    """Attach interval metadata to a JSON action payload."""
    equilibrium = action_payload.get("equilibrium_action")
    if not isinstance(equilibrium, dict):
        raise ValueError("action_payload must contain equilibrium_action object")

    raw_size = equilibrium.get("size", 0.0)
    size = float(raw_size)

    enriched = dict(action_payload)
    enriched["uncertainty"] = interval_action_size_stub(
        action_size=size,
        confidence=confidence,
        calibration_error=calibration_error,
    )
    return enriched
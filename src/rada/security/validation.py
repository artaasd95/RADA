"""Shared input validation helpers."""

from __future__ import annotations

import re
from pathlib import Path

SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_safe_id(value: str, *, field: str = "id") -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        msg = f"invalid {field}: must match {SAFE_ID_PATTERN.pattern}"
        raise ValueError(msg)
    return value


def resolve_within_root(root: Path, *parts: str) -> Path:
    """Resolve a path and ensure it stays within root."""
    candidate = (root / Path(*parts)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in candidate.parents and candidate != root_resolved:
        msg = f"path escapes root: {candidate}"
        raise ValueError(msg)
    return candidate

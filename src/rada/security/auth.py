"""API key authentication dependency."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _api_key_required() -> bool:
    env = os.getenv("RADA_ENV", "dev").lower().strip()
    if env in {"dev", "development", "test"}:
        configured = os.getenv("RADA_API_KEY", "").strip()
        return bool(configured)
    return True


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Validate X-API-Key when required by environment."""
    expected = os.getenv("RADA_API_KEY", "").strip()
    if not _api_key_required():
        return
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RADA_API_KEY is not configured",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

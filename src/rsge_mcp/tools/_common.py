"""Shared helpers for tool modules."""

from __future__ import annotations

from typing import Any


def compact(data: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with ``None`` values dropped (don't send empty fields)."""
    return {key: value for key, value in data.items() if value is not None}

"""Unwrap the rs.ge ``{DATA, STATUS}`` response envelope.

The API always returns HTTP 200 and wraps the payload as
``{"DATA": ..., "STATUS": {"ID": int, "TEXT": str}}``. ``ID == 0`` is success.
Some public endpoints (e.g. xdata ``RSPublicInfo``) return a bare list with no
envelope — those pass through unchanged. Keys are case-sensitive in the docs, but a
few endpoints deviate (``Data`` vs ``DATA``); we match exact-first, fall back to a
case-insensitive lookup, and log a warning so deviations are discovered, not hidden.
"""

from __future__ import annotations

from typing import Any

from ..errors import error_for
from ..logging import get_logger

log = get_logger("envelope")


def _find(obj: dict[str, Any], name: str) -> tuple[str, Any] | None:
    """Find ``name`` in ``obj``, exact match first then case-insensitive."""
    if name in obj:
        return name, obj[name]
    lowered = name.lower()
    for key, value in obj.items():
        if key.lower() == lowered:
            return key, value
    return None


def unwrap(payload: Any) -> Any:
    """Return ``DATA`` on success, raise ``RsgeEnvelopeError`` on a non-zero status.

    Pass through payloads that have no recognizable envelope.
    """
    if not isinstance(payload, dict):
        return payload

    status_kv = _find(payload, "STATUS")
    if status_kv is None or not isinstance(status_kv[1], dict):
        return payload
    status_key, status = status_kv
    if status_key != "STATUS":
        log.warning("envelope STATUS key had unexpected case: %r", status_key)

    id_kv = _find(status, "ID")
    status_id = int(id_kv[1]) if id_kv is not None else 0

    if status_id != 0:
        text_kv = _find(status, "TEXT")
        text = str(text_kv[1]) if text_kv and text_kv[1] is not None else ""
        raise error_for(status_id, text)

    data_kv = _find(payload, "DATA")
    if data_kv is None:
        return None
    if data_kv[0] != "DATA":
        log.warning("envelope DATA key had unexpected case: %r", data_kv[0])
    return data_kv[1]

"""Logging setup.

The stdio MCP transport owns stdout — anything written there that is not the MCP
protocol breaks the client connection. So every log record goes to stderr.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False
_ROOT_NAME = "rsge_mcp"


def setup_logging(level: int | None = None) -> None:
    """Configure the package logger to write to stderr. Idempotent.

    The level defaults to ``RSGE_LOG_LEVEL`` (DEBUG/INFO/WARNING/ERROR, case-insensitive)
    or INFO. Set DEBUG to see per-request transport logs when diagnosing a failing tool.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    if level is None:
        raw = (os.environ.get("RSGE_LOG_LEVEL") or "INFO").strip().upper()
        level = logging.getLevelNamesMapping().get(raw, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the package root."""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")

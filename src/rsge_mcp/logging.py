"""Logging setup.

The stdio MCP transport owns stdout — anything written there that is not the MCP
protocol breaks the client connection. So every log record goes to stderr.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_ROOT_NAME = "rsge_mcp"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the package logger to write to stderr. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return
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

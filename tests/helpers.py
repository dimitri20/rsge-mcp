"""Shared test helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from rsge_mcp.config import Settings
from rsge_mcp.context import AppContext, build_context


def env(data: Any, *, sid: int = 0, text: str = "ok") -> dict[str, Any]:
    """Build a rs.ge {DATA, STATUS} envelope."""
    return {"DATA": data, "STATUS": {"ID": sid, "TEXT": text}}


@asynccontextmanager
async def make_ctx(settings: Settings) -> AsyncIterator[AppContext]:
    """Build an AppContext and close its HTTP client afterward."""
    ctx = build_context(settings)
    try:
        yield ctx
    finally:
        await ctx.http.aclose()


class FakeMCP:
    """Captures tools registered via ``@mcp.tool()`` so tests can call them directly."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            self.tools[fn.__name__] = fn
            return fn

        return decorator

"""MCP tool surface. ``register_all`` builds the app context and wires every module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import Settings
from ..context import build_context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_all(mcp: FastMCP, settings: Settings) -> None:
    """Build the shared context and register every tool module (REST + SOAP)."""
    ctx = build_context(settings)
    from . import auth_tools, common, invoice, org, taxpayer_public
    from .soap import ntos_invoice, waybill

    modules = (org, common, invoice, taxpayer_public, auth_tools, waybill, ntos_invoice)
    for module in modules:
        module.register(mcp, ctx)

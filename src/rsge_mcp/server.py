"""FastMCP server construction."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import Settings, load_env_file, load_settings
from .logging import get_logger, setup_logging
from .tools import register_all

log = get_logger("server")


def build_server(settings: Settings | None = None) -> FastMCP:
    """Build the FastMCP server with all tools registered."""
    if settings is None:
        # The .env must load BEFORE logging is configured, or an RSGE_LOG_LEVEL set in
        # the .env (the only config surface for pipx/uvx installs) is silently ignored.
        load_env_file()
    setup_logging()
    settings = settings if settings is not None else load_settings()
    if not settings.has_eapi_creds and not settings.has_soap_creds:
        log.warning("No rs.ge credentials configured; only public tools will work.")
    mcp = FastMCP("rsge")
    register_all(mcp, settings)
    return mcp

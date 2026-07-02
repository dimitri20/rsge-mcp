"""Opt-in LIVE end-to-end MCP smoke: launch the server over stdio like a real client.

Gated by RSGE_RUN_INTEGRATION=1. Uses only the public test account (RSGE_ENV=test) and
read-only tools — plus one write refusal, which must surface as a proper MCP tool error
(isError=True), proving read-only-by-default holds through the full protocol stack.
"""

from __future__ import annotations

import os
import shutil

import pytest

pytestmark = pytest.mark.integration

_RUN = os.environ.get("RSGE_RUN_INTEGRATION") == "1"
_skip = pytest.mark.skipif(not _RUN, reason="set RSGE_RUN_INTEGRATION=1 to run live smoke")


@_skip
@pytest.mark.asyncio
async def test_mcp_stdio_end_to_end() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    binary = shutil.which("rsge-mcp")
    assert binary, "rsge-mcp entry point not on PATH (pip install -e .)"

    params = StdioServerParameters(
        command=binary,
        env={
            **os.environ,
            "RSGE_ENV": "test",
            "RSGE_LOG_LEVEL": "WARNING",
            "RSGE_ALLOW_WRITES": "",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "rsge"

            tools = await session.list_tools()
            assert len(tools.tools) >= 147

            live = await session.call_tool("rsge_get_units", {})
            assert not live.isError and live.content

            refused = await session.call_tool("rsge_cancel_invoice", {"invoice_id": 1})
            assert refused.isError  # read-only guard holds across the protocol boundary
            assert "read-only" in (refused.content[0].text if refused.content else "")

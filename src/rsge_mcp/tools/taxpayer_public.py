"""Public taxpayer info (xdata ``TaxPayer/RSPublicInfo``) — no authentication."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_taxpayer_public_info(ident_code: str) -> Any:
        """Public taxpayer info by 9- or 11-digit identification code.

        No authentication required. Returns status records (registration type, VAT
        payer, liens/sequestration, etc.). Served from xdata.rs.ge.
        """
        return await ctx.rest.post(
            "/TaxPayer/RSPublicInfo",
            {"IdentCode": ident_code},
            auth=False,
            base=ctx.settings.hosts.xdata_base,
        )

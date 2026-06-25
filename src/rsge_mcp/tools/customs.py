"""Customs declaration tools (eAPI ``CustomsDeclarations/*``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_customs_declarations(start_date: str, end_date: str) -> Any:
        """Fetch ASYCUDA customs declarations for a date range (eAPI).

        Returns declaration line items where your TIN is the importer or exporter (customs
        code, regime, registration/assessment numbers, HS code, weights, GEL value, goods
        description, …). Dates are ISO 8601 ('YYYY-MM-DDTHH:MM:SS'); the range must be
        **<= 20 days** (server-enforced). This endpoint uses HTTP GET with a JSON body.
        """
        return await ctx.rest.post(
            "/CustomsDeclarations/GetAsycudaDeclarations",
            {"START_DATE": start_date, "END_DATE": end_date},
            method="GET",
        )

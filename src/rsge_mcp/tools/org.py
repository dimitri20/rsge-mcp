"""Organization / taxpayer lookup tools (eAPI ``Org/*``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_org_info_by_tin(tin: str) -> Any:
        """Look up an organization or person by Georgian tax ID (TIN).

        Returns name, address, and VAT-payer / diplomat flags. Requires eAPI auth.
        rs.ge error messages may be in Georgian.
        """
        return await ctx.rest.post("/Org/GetOrgInfoByTin", {"Tin": tin})

    @mcp.tool()
    async def rsge_get_vat_payer_status(tin: str, vat_date: str) -> Any:
        """Check whether a TIN was a registered VAT payer on a given date.

        `vat_date` format: 'DD-MM-YYYY HH:MM:SS'. Requires eAPI auth.
        """
        return await ctx.rest.post("/Org/GetVatPayerStatus", {"Tin": tin, "VatDate": vat_date})

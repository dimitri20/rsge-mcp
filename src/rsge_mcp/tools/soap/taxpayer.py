"""Cash-register Z-report tools (SOAP ``taxpayerservice``).

Read-only. Unlike WayBillService/ntos, this service names the credentials
``UserName``/``Password`` and they come **first** in the WSDL sequence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...soap.credentials import service_user_or_raise
from ...soap.services import TAXPAYER

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ...context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_z_report_details(start_date: str, end_date: str) -> Any:
        """Detailed cash-register Z-reports for a date range (SOAP taxpayerservice).

        One row per device per Z-report: device serial, report date, receipt count, total
        amount, cash vs non-cash split, and Z number. Dates are ISO 8601
        ('YYYY-MM-DDTHH:MM:SS').
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            TAXPAYER,
            "Get_Z_Report_Details",
            {
                "UserName": su.user,
                "Password": su.password,
                "StartDate": start_date,
                "EndDate": end_date,
            },
        )

    @mcp.tool()
    async def rsge_get_z_report_sum(start_date: str, end_date: str) -> Any:
        """Aggregate cash-register totals (cash + non-cash) for a date range (SOAP).

        Dates are ISO 8601 ('YYYY-MM-DDTHH:MM:SS').
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            TAXPAYER,
            "Get_Z_Report_Sum",
            {
                "UserName": su.user,
                "Password": su.password,
                "StartDate": start_date,
                "EndDate": end_date,
            },
        )

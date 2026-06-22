"""Legacy VAT invoice tools (SOAP ``ntosservice``).

Read-only for now (check service user, fetch invoice, list seller/buyer invoices). All
require SOAP service-user credentials. Parameter order follows the WSDL exactly (note
``su``/``sp`` come LAST here, unlike WayBillService).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...soap.credentials import ServiceUser, service_user_or_raise
from ...soap.services import NTOS
from .._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ...context import AppContext


def _list_params(
    su: ServiceUser, user_id: int, un_id: int, filters: dict[str, Any]
) -> dict[str, Any]:
    """Build the ordered param dict for get_{seller,buyer}_invoices (WSDL order)."""
    params: dict[str, Any] = {"user_id": user_id, "un_id": un_id}
    params.update(compact(filters))
    params["su"] = su.su
    params["sp"] = su.sp
    return params


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_ntos_check_service_user(user_id: int = 0) -> Any:
        """Validate the configured SOAP service-user against ntosservice (VAT invoices).

        Returns the resolved user_id / sua (service-user id).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(NTOS, "chek", {"su": su.su, "sp": su.sp, "user_id": user_id})

    @mcp.tool()
    async def rsge_ntos_get_invoice(invoice_id: int, user_id: int = 0) -> Any:
        """Fetch a VAT invoice via the legacy ntos SOAP service by its id."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_invoice",
            {"user_id": user_id, "invois_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_get_seller_invoices(
        un_id: int,
        user_id: int = 0,
        s_dt: str | None = None,
        e_dt: str | None = None,
        op_s_dt: str | None = None,
        op_e_dt: str | None = None,
        invoice_no: str | None = None,
        sa_ident_no: str | None = None,
        desc: str | None = None,
        doc_mos_nom: str | None = None,
    ) -> Any:
        """List invoices issued BY a seller (`un_id`) via ntos SOAP. Dates ISO 8601."""
        su = service_user_or_raise(ctx.settings)
        params = _list_params(
            su,
            user_id,
            un_id,
            {
                "s_dt": s_dt,
                "e_dt": e_dt,
                "op_s_dt": op_s_dt,
                "op_e_dt": op_e_dt,
                "invoice_no": invoice_no,
                "sa_ident_no": sa_ident_no,
                "desc": desc,
                "doc_mos_nom": doc_mos_nom,
            },
        )
        return await ctx.soap.call(NTOS, "get_seller_invoices", params)

    @mcp.tool()
    async def rsge_ntos_get_buyer_invoices(
        un_id: int,
        user_id: int = 0,
        s_dt: str | None = None,
        e_dt: str | None = None,
        op_s_dt: str | None = None,
        op_e_dt: str | None = None,
        invoice_no: str | None = None,
        sa_ident_no: str | None = None,
        desc: str | None = None,
        doc_mos_nom: str | None = None,
    ) -> Any:
        """List invoices issued TO a buyer (`un_id`) via ntos SOAP. Dates ISO 8601."""
        su = service_user_or_raise(ctx.settings)
        params = _list_params(
            su,
            user_id,
            un_id,
            {
                "s_dt": s_dt,
                "e_dt": e_dt,
                "op_s_dt": op_s_dt,
                "op_e_dt": op_e_dt,
                "invoice_no": invoice_no,
                "sa_ident_no": sa_ident_no,
                "desc": desc,
                "doc_mos_nom": doc_mos_nom,
            },
        )
        return await ctx.soap.call(NTOS, "get_buyer_invoices", params)

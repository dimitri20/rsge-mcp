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

    @mcp.tool()
    async def rsge_ntos_save_invoice(
        invoice_id: int,
        operation_date: str,
        seller_un_id: int,
        buyer_un_id: int,
        overhead_dt: str,
        b_s_user_id: int,
        overhead_no: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Create/save a VAT invoice header (ntos SOAP). WRITE — not auto-retried.

        Add line items afterward with `rsge_ntos_save_invoice_desc` (one call per item).
        Dates (`operation_date`, `overhead_dt`) are ISO 8601. `overhead_no`/`overhead_dt`
        are the waybill (zeddnadebi) number/date, if any.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "user_id": user_id,
            "invois_id": invoice_id,
            "operation_date": operation_date,
            "seller_un_id": seller_un_id,
            "buyer_un_id": buyer_un_id,
        }
        params.update(compact({"overhead_no": overhead_no}))
        params.update(
            {
                "overhead_dt": overhead_dt,
                "b_s_user_id": b_s_user_id,
                "su": su.su,
                "sp": su.sp,
            }
        )
        return await ctx.soap.call(NTOS, "save_invoice", params)

    @mcp.tool()
    async def rsge_ntos_save_invoice_desc(
        invoice_id: int,
        goods_name: str,
        g_number: float,
        full_amount: float,
        drg_amount: float,
        aqcizi_amount: float,
        akciz_id: int,
        g_unit: str | None = None,
        desc_id: int = 0,
        user_id: int = 0,
    ) -> Any:
        """Add (or update) ONE line item on a VAT invoice (ntos SOAP). WRITE — not auto-retried.

        Call once per line item. `desc_id=0` creates a new line; a real id updates it.
        - `g_number`: quantity; `full_amount`: line total; `drg_amount`: VAT amount;
          `aqcizi_amount`: excise amount; `akciz_id`: excise code id (0 if none).
        """
        su = service_user_or_raise(ctx.settings)
        # WSDL order: user_id, id, su, sp, invois_id, goods, g_unit, g_number, full_amount,
        # drg_amount, aqcizi_amount, akciz_id (note su/sp are mid-sequence here).
        params: dict[str, Any] = {
            "user_id": user_id,
            "id": desc_id,
            "su": su.su,
            "sp": su.sp,
            "invois_id": invoice_id,
        }
        params.update(compact({"goods": goods_name, "g_unit": g_unit}))
        params.update(
            {
                "g_number": g_number,
                "full_amount": full_amount,
                "drg_amount": drg_amount,
                "aqcizi_amount": aqcizi_amount,
                "akciz_id": akciz_id,
            }
        )
        return await ctx.soap.call(NTOS, "save_invoice_desc", params)

    @mcp.tool()
    async def rsge_ntos_change_invoice_status(
        invoice_id: int, status: int, user_id: int = 0
    ) -> Any:
        """Change a VAT invoice's status (ntos SOAP). WRITE — not auto-retried.

        `status` is the rs.ge invoice status code (e.g. confirm/reject/cancel).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "change_invoice_status",
            {
                "user_id": user_id,
                "inv_id": invoice_id,
                "status": status,
                "su": su.su,
                "sp": su.sp,
            },
        )

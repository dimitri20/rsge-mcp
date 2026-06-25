"""Legacy VAT invoice tools (SOAP ``ntosservice``).

The full legacy VAT-invoice surface: issue / correct / cancel invoices, line items,
buyer accept/refuse, advance-payment netting, the buyer↔seller request flow, and
identity lookups. All require SOAP service-user credentials. Parameter order follows the
WSDL exactly — ``su``/``sp`` come LAST for most ops but FIRST for the advance-netting
ops, and ``save_invoice_n`` puts ``note`` AFTER ``su``/``sp`` (unlike WayBillService,
where su/sp always lead). Writes pass ``write=True`` and are never auto-retried.
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
        return await ctx.soap.call(NTOS, "save_invoice", params, write=True)

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
        return await ctx.soap.call(NTOS, "save_invoice_desc", params, write=True)

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
            write=True,
        )

    # --- save variants ---
    @mcp.tool()
    async def rsge_ntos_save_invoice_a(
        invoice_id: int,
        operation_date: str,
        seller_un_id: int,
        buyer_un_id: int,
        overhead_dt: str,
        b_s_user_id: int,
        overhead_no: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Create/save an ADVANCE (prepayment) VAT invoice header (ntos SOAP). WRITE — not
        auto-retried.

        Same shape as `rsge_ntos_save_invoice` but issues an advance invoice, which can
        later be netted against a delivery invoice via `rsge_ntos_attach_advance_invoice`.
        Dates ISO 8601.
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
            {"overhead_dt": overhead_dt, "b_s_user_id": b_s_user_id, "su": su.su, "sp": su.sp}
        )
        return await ctx.soap.call(NTOS, "save_invoice_a", params, write=True)

    @mcp.tool()
    async def rsge_ntos_save_invoice_n(
        invoice_id: int,
        operation_date: str,
        seller_un_id: int,
        buyer_un_id: int,
        overhead_dt: str,
        b_s_user_id: int,
        overhead_no: str | None = None,
        note: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Create/save a VAT invoice header WITH a free-text note (ntos SOAP). WRITE — not
        auto-retried.

        Like `rsge_ntos_save_invoice` plus a trailing `note`. WSDL order quirk: `note`
        comes AFTER `su`/`sp`, so it is appended last.
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
            {"overhead_dt": overhead_dt, "b_s_user_id": b_s_user_id, "su": su.su, "sp": su.sp}
        )
        params.update(compact({"note": note}))
        return await ctx.soap.call(NTOS, "save_invoice_n", params, write=True)

    # --- correction & cancel ---
    @mcp.tool()
    async def rsge_ntos_correct_invoice(invoice_id: int, k_type: int, user_id: int = 0) -> Any:
        """Create a CORRECTION (credit/debit note) for a VAT invoice (ntos SOAP `k_invoice`).
        WRITE — not auto-retried. Returns the new correction invoice's id.

        `k_type` selects the correction reason. It is commonly documented as
        1=cancel taxable operation, 2=change operation type, 3=price/compensation reduction,
        4=goods returned — but the WSDL does not enumerate it, so confirm against current
        rs.ge correction documentation before relying on a specific value.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "k_invoice",
            {"user_id": user_id, "inv_id": invoice_id, "k_type": k_type, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_ntos_cancel_invoice(invoice_id: int, user_id: int = 0) -> Any:
        """Cancel/void a VAT invoice (ntos SOAP `g_invoice`). WRITE — not auto-retried.

        This is the dedicated cancel op (distinct from `rsge_ntos_change_invoice_status`).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "g_invoice",
            {"user_id": user_id, "inv_id": invoice_id, "su": su.su, "sp": su.sp},
            write=True,
        )

    # --- line items (read + delete; pairs with save_invoice_desc) ---
    @mcp.tool()
    async def rsge_ntos_get_invoice_desc(invoice_id: int, user_id: int = 0) -> Any:
        """List the line items (descriptions) of a VAT invoice (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_invoice_desc",
            {"user_id": user_id, "invois_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_delete_invoice_desc(invoice_id: int, desc_id: int, user_id: int = 0) -> Any:
        """Delete ONE line item from a VAT invoice (ntos SOAP). WRITE — not auto-retried.

        `desc_id` is the line row id (wire `id`); `invoice_id` is the invoice (wire `inv_id`).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "delete_invoice_desc",
            {"user_id": user_id, "id": desc_id, "inv_id": invoice_id, "su": su.su, "sp": su.sp},
            write=True,
        )

    # --- buyer accept / refuse ---
    @mcp.tool()
    async def rsge_ntos_accept_invoice_status(
        invoice_id: int, status: int, user_id: int = 0
    ) -> Any:
        """BUYER accepts/confirms a received VAT invoice (ntos SOAP `acsept_invoice_status`).
        WRITE — not auto-retried.

        This is the buyer-side accept op; the seller-side equivalent is
        `rsge_ntos_change_invoice_status`. `status` is the rs.ge status code (thinly
        documented in the WSDL — confirm the code for your action).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "acsept_invoice_status",
            {"user_id": user_id, "inv_id": invoice_id, "status": status, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_ntos_refuse_invoice_status(
        invoice_id: int, ref_text: str | None = None, user_id: int = 0
    ) -> Any:
        """BUYER refuses/rejects a received VAT invoice with an optional reason (ntos SOAP
        `ref_invoice_status`). WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"user_id": user_id, "inv_id": invoice_id}
        params.update(compact({"ref_text": ref_text}))
        params.update({"su": su.su, "sp": su.sp})
        return await ctx.soap.call(NTOS, "ref_invoice_status", params, write=True)

    # --- advance / prepayment netting (su/sp come FIRST here) ---
    @mcp.tool()
    async def rsge_ntos_get_attachable_advance_invoices(
        seller_un_id: int,
        operation_date: str,
        buyer_tin: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """List advance invoices eligible to net against a delivery invoice (ntos SOAP).

        Filtered by seller (and optionally buyer TIN) as of `operation_date` (ISO 8601).
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "su": su.su,
            "sp": su.sp,
            "user_id": user_id,
            "seller_un_id": seller_un_id,
        }
        params.update(compact({"buyer_tin": buyer_tin}))
        params["operation_date"] = operation_date
        return await ctx.soap.call(NTOS, "get_attachable_advance_invoices", params)

    @mcp.tool()
    async def rsge_ntos_get_attached_advance_invoices(invoice_id: int, user_id: int = 0) -> Any:
        """List advance invoices already netted into a delivery invoice (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_attached_advance_invoices",
            {"su": su.su, "sp": su.sp, "user_id": user_id, "invoice_id": invoice_id},
        )

    @mcp.tool()
    async def rsge_ntos_attach_advance_invoice(
        invoice_id: int,
        advance_invoice_id: int,
        advance_invoice_drg_amount: float,
        seller_un_id: int,
        buyer_tin: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Net one advance invoice into a delivery invoice for a given VAT (drg) amount
        (ntos SOAP). WRITE — not auto-retried. `advance_invoice_drg_amount` > 0.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "su": su.su,
            "sp": su.sp,
            "user_id": user_id,
            "invoice_id": invoice_id,
            "advance_invoice_id": advance_invoice_id,
            "advance_invoice_drg_amount": advance_invoice_drg_amount,
            "seller_un_id": seller_un_id,
        }
        params.update(compact({"buyer_tin": buyer_tin}))
        return await ctx.soap.call(NTOS, "attach_advance_invoice", params, write=True)

    @mcp.tool()
    async def rsge_ntos_update_advance_invoice(
        invoice_id: int,
        advance_invoice_id: int,
        advance_invoice_drg_amount: float,
        user_id: int = 0,
    ) -> Any:
        """Change the netted (drg) amount on an already-attached advance invoice (ntos SOAP).
        WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "update_advance_invoice",
            {
                "su": su.su,
                "sp": su.sp,
                "user_id": user_id,
                "invoice_id": invoice_id,
                "advance_invoice_id": advance_invoice_id,
                "advance_invoice_drg_amount": advance_invoice_drg_amount,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_ntos_detach_advance_invoices(
        invoice_id: int, advance_invoice_ids: list[int], user_id: int = 0
    ) -> Any:
        """Remove one or more advance invoices from a delivery invoice (ntos SOAP). WRITE —
        not auto-retried.

        `advance_invoice_ids` must be a non-empty list; it serializes to the WSDL
        `AdvanceInvoiceIds` (`<advance_invoices><id>…</id></advance_invoices>`).
        """
        if not advance_invoice_ids:
            raise ValueError("advance_invoice_ids must be a non-empty list")
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "detach_advance_invoices",
            {
                "su": su.su,
                "sp": su.sp,
                "user_id": user_id,
                "invoice_id": invoice_id,
                "advance_invoices": {"id": advance_invoice_ids},
            },
            write=True,
        )

    # --- invoice-request lifecycle (buyer asks seller to issue) ---
    @mcp.tool()
    async def rsge_ntos_save_invoice_request(
        invoice_id: int,
        buyer_un_id: int,
        seller_un_id: int,
        dt: str,
        overhead_no: str | None = None,
        notes: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """BUYER requests a seller to issue an invoice (ntos SOAP). WRITE — not auto-retried.

        `dt` is ISO 8601. (Wire field for the buyer is rs.ge's spelling `bayer_un_id`.)
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "inv_id": invoice_id,
            "user_id": user_id,
            "bayer_un_id": buyer_un_id,
            "seller_un_id": seller_un_id,
        }
        params.update(compact({"overhead_no": overhead_no}))
        params["dt"] = dt
        params.update(compact({"notes": notes}))
        params.update({"su": su.su, "sp": su.sp})
        return await ctx.soap.call(NTOS, "save_invoice_request", params, write=True)

    @mcp.tool()
    async def rsge_ntos_get_invoice_request(invoice_id: int, user_id: int = 0) -> Any:
        """Fetch a single invoice request by invoice id (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_invoice_request",
            {"inv_id": invoice_id, "user_id": user_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_get_invoice_requests(buyer_un_id: int, user_id: int = 0) -> Any:
        """BUYER lists all their invoice requests (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_invoice_requests",
            {"bayer_un_id": buyer_un_id, "user_id": user_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_get_requested_invoices(seller_un_id: int, user_id: int = 0) -> Any:
        """SELLER lists invoice requests addressed to them (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_requested_invoices",
            {"user_id": user_id, "seller_un_id": seller_un_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_accept_invoice_request(
        request_id: int, seller_un_id: int, user_id: int = 0
    ) -> Any:
        """SELLER accepts a buyer's invoice request (ntos SOAP). WRITE — not auto-retried.

        `request_id` is the REQUEST id (wire `id`), not an invoice id.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "acsept_invoice_request_status",
            {
                "id": request_id,
                "user_id": user_id,
                "seller_un_id": seller_un_id,
                "su": su.su,
                "sp": su.sp,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_ntos_del_invoice_request(
        invoice_id: int, buyer_un_id: int, user_id: int = 0
    ) -> Any:
        """Withdraw/delete an invoice request (ntos SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "del_invoice_request",
            {
                "inv_id": invoice_id,
                "user_id": user_id,
                "bayer_un_id": buyer_un_id,
                "su": su.su,
                "sp": su.sp,
            },
            write=True,
        )

    # --- identity glue (resolve the un_id every ntos op keys on) ---
    @mcp.tool()
    async def rsge_ntos_get_un_id_from_tin(tin: str, user_id: int = 0) -> Any:
        """Resolve a taxpayer TIN to its ntos un_id (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_un_id_from_tin",
            {"user_id": user_id, "tin": tin, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_get_un_id_from_user_id(user_id: int = 0) -> Any:
        """Resolve the service-user's own un_id (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_un_id_from_user_id",
            {"user_id": user_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_ntos_get_org_name_from_un_id(un_id: int, user_id: int = 0) -> Any:
        """Resolve an un_id to the organization's legal name (ntos SOAP)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            NTOS,
            "get_org_name_from_un_id",
            {"user_id": user_id, "un_id": un_id, "su": su.su, "sp": su.sp},
        )

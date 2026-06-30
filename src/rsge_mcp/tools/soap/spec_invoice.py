"""NSAF special (oil/fuel) invoice tools (SOAP ``SpecInvoicesService``).

The full NSAF special-invoice lifecycle for the petroleum sector: issue the oil/transport
header (``save_invoice_b_n`` via :class:`SpecInvoice`) + line items, attach SSD/SSAF
customs/excise sub-documents, run the transport flow, buyer accept/refuse, seller status,
corrections & cancel, advance-payment netting, and the reads/lookups that feed the header.

All require SOAP service-user credentials. **Parameter order follows the WSDL exactly and
``su``/``sp`` sit at a DIFFERENT position per op** — last for most, mid-sequence in
``save_line_item``, early in attach/update advance, interleaved in detach — so each tool
builds its param dict explicitly (no shared ordering helper). Writes pass ``write=True`` and
are never auto-retried.

Identity note: this service has no TIN→un_id resolver; obtain the ``un_id`` values it needs
via the ntos identity tools (``rsge_ntos_get_un_id_from_tin`` / ``_from_user_id`` /
``rsge_ntos_get_org_name_from_un_id``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models.spec_invoice import SpecInvoice, SpecInvoiceDesc
from ...soap.credentials import ServiceUser, service_user_or_raise
from ...soap.services import SPECINVOICES
from .._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ...context import AppContext


def _list_params(
    su: ServiceUser,
    user_id: int,
    un_id: int,
    s_dt: str,
    e_dt: str,
    op_s_dt: str,
    op_e_dt: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Ordered params for get_{seller,buyer}_invoices_n (WSDL order, su/sp LAST).

    The four dates are REQUIRED (minOccurs=1) so they are always sent, never compacted away.
    """
    params: dict[str, Any] = {
        "user_id": user_id,
        "un_id": un_id,
        "s_dt": s_dt,
        "e_dt": e_dt,
        "op_s_dt": op_s_dt,
        "op_e_dt": op_e_dt,
    }
    params.update(compact(filters))
    params["su"] = su.su
    params["sp"] = su.sp
    return params


def register(mcp: FastMCP, ctx: AppContext) -> None:
    # --- header & line items ---
    @mcp.tool()
    async def rsge_spec_save_invoice(header: SpecInvoice) -> Any:
        """Issue/save an NSAF special (oil/fuel) invoice header (SOAP ``save_invoice_b_n``).
        WRITE — not auto-retried. Returns the invoice id.

        Pass a :class:`SpecInvoice`; line items are added afterward with
        ``rsge_spec_save_line_item``. `invois_id=0` creates a new invoice.
        """
        su = service_user_or_raise(ctx.settings)
        params = header.to_params()
        params["su"] = su.su
        params["sp"] = su.sp
        return await ctx.soap.call(SPECINVOICES, "save_invoice_b_n", params, write=True)

    @mcp.tool()
    async def rsge_spec_save_line_item(
        invoice_id: int, item: SpecInvoiceDesc, desc_id: int = 0, user_id: int = 0
    ) -> Any:
        """Add (or update) ONE line item on a special invoice (SOAP ``save_invoice_desc_n``).
        WRITE — not auto-retried.

        `desc_id=0` creates a new line; a real id updates it. `su`/`sp` are MID-sequence here
        (user_id, id, su, sp, p_inv_id, …item fields).
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "user_id": user_id,
            "id": desc_id,
            "su": su.su,
            "sp": su.sp,
            "p_inv_id": invoice_id,
        }
        params.update(item.to_params())
        return await ctx.soap.call(SPECINVOICES, "save_invoice_desc_n", params, write=True)

    @mcp.tool()
    async def rsge_spec_delete_line_item(invoice_id: int, desc_id: int, user_id: int = 0) -> Any:
        """Delete ONE line item from a special invoice (SOAP). WRITE — not auto-retried.

        `desc_id` is the line row id (wire `id`); `invoice_id` is the invoice (wire `inv_id`).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "delete_invoice_desc",
            {"user_id": user_id, "id": desc_id, "inv_id": invoice_id, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_get_invoice(invoice_id: int, user_id: int = 0) -> Any:
        """Fetch a special invoice header by id (SOAP ``get_invoice_n``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_invoice_n",
            {"user_id": user_id, "invois_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_spec_get_line_items(invoice_id: int, user_id: int = 0) -> Any:
        """List the line items of a special invoice (SOAP ``get_invoice_desc_n``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_invoice_desc_n",
            {"user_id": user_id, "invois_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    # --- status ---
    @mcp.tool()
    async def rsge_spec_change_status(invoice_id: int, status: int, user_id: int = 0) -> Any:
        """Seller-side status change for a special invoice (SOAP ``change_invoice_status_n``).
        WRITE — not auto-retried. `status` is an rs.ge int code (confirm against rs.ge docs).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "change_invoice_status_n",
            {"user_id": user_id, "inv_id": invoice_id, "status": status, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_accept_status(invoice_id: int, status: int, user_id: int = 0) -> Any:
        """BUYER accepts a received special invoice (SOAP ``acsept_invoice_status_n``).
        WRITE — not auto-retried. `status` is an rs.ge int code (confirm against rs.ge docs).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "acsept_invoice_status_n",
            {"user_id": user_id, "inv_id": invoice_id, "status": status, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_refuse_status(
        invoice_id: int, ref_text: str | None = None, user_id: int = 0
    ) -> Any:
        """BUYER refuses a received special invoice with an optional reason (SOAP
        ``ref_invoice_status_n``). WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"user_id": user_id, "inv_id": invoice_id}
        params.update(compact({"ref_text": ref_text}))
        params.update({"su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "ref_invoice_status_n", params, write=True)

    # --- correction & cancel ---
    @mcp.tool()
    async def rsge_spec_correct_invoice(invoice_id: int, k_type: int, user_id: int = 0) -> Any:
        """Create a correction (credit/debit note) for a special invoice (SOAP ``k_invoice_n``).
        WRITE — not auto-retried. Returns the new correction id.

        `k_type` selects the correction reason — commonly documented as 11=cancel operation,
        12=change operation type, 13=amount change, 14=goods returned, 21/22=post-transport —
        but the WSDL does not enumerate it, so confirm against current rs.ge spec-invoice docs.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "k_invoice_n",
            {"user_id": user_id, "inv_id": invoice_id, "k_type": k_type, "su": su.su, "sp": su.sp},
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_cancel_reason(
        invoice_id: int, reason: str | None = None, user_id: int = 0
    ) -> Any:
        """Record a cancellation reason for a special invoice (SOAP ``gauqmebis_mizezi_n``).
        WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_id": invoice_id}
        params.update(compact({"p_reason": reason}))
        params.update({"user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "gauqmebis_mizezi_n", params, write=True)

    @mcp.tool()
    async def rsge_spec_get_correction(invoice_id: int, user_id: int = 0) -> Any:
        """Check whether a correction exists for a special invoice (SOAP get_makoreqtirebeli)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_makoreqtirebeli",
            {"user_id": user_id, "inv_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    # --- advance / prepayment netting (su/sp position varies) ---
    @mcp.tool()
    async def rsge_spec_attach_advance(
        invoice_id: int,
        advance_invoice_id: int,
        advance_invoice_drg_amount: float,
        seller_un_id: int,
        buyer_tin: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Net an advance invoice into a special invoice (SOAP ``attach_advance_invoice``).
        WRITE — not auto-retried. `su`/`sp` are EARLY (positions 2-3).
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {
            "user_id": user_id,
            "su": su.su,
            "sp": su.sp,
            "seller_un_id": seller_un_id,
        }
        params.update(compact({"buyer_tin": buyer_tin}))
        params.update(
            {
                "invoice_id": invoice_id,
                "advance_invoice_id": advance_invoice_id,
                "advance_invoice_drg_amount": advance_invoice_drg_amount,
            }
        )
        return await ctx.soap.call(SPECINVOICES, "attach_advance_invoice", params, write=True)

    @mcp.tool()
    async def rsge_spec_detach_advance(
        invoice_id: int, advance_invoice_id: int, user_id: int = 0
    ) -> Any:
        """Remove an advance invoice from a special invoice (SOAP ``detach_advance_invoice``).
        WRITE — not auto-retried. `su`/`sp` are INTERLEAVED (invoice_id, user_id, su, sp, …).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "detach_advance_invoice",
            {
                "invoice_id": invoice_id,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
                "advance_invoice_id": advance_invoice_id,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_update_advance(
        invoice_id: int,
        advance_invoice_id: int,
        advance_invoice_drg_amount: float,
        user_id: int = 0,
    ) -> Any:
        """Change the netted amount on an attached advance (SOAP ``update_advance_invoice``).
        WRITE — not auto-retried. `su`/`sp` are EARLY (positions 2-3).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "update_advance_invoice",
            {
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
                "invoice_id": invoice_id,
                "advance_invoice_id": advance_invoice_id,
                "advance_invoice_drg_amount": advance_invoice_drg_amount,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_get_attached_advances(invoice_id: int, user_id: int = 0) -> Any:
        """List advances netted into a special invoice (SOAP ``get_attached_advance_invoices``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_attached_advance_invoices",
            {"invoice_id": invoice_id, "user_id": user_id, "su": su.su, "sp": su.sp},
        )

    @mcp.tool()
    async def rsge_spec_get_attachable_advances(
        operation_dt: str, seller_un_id: int, buyer_tin: str | None = None, user_id: int = 0
    ) -> Any:
        """List advances eligible to net (SOAP ``get_attachable_advance_invs``). `operation_dt`
        is ISO 8601.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"operation_dt": operation_dt, "seller_un_id": seller_un_id}
        params.update(compact({"buyer_tin": buyer_tin}))
        params.update({"user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "get_attachable_advance_invs", params)

    # --- SSD / SSAF sub-documents ---
    @mcp.tool()
    async def rsge_spec_add_ssd(
        invoice_id: int,
        seller_un_id: int,
        ssd_date: str,
        ssd_n: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Attach an SSD customs sub-document to a special invoice (SOAP). WRITE — not
        auto-retried. `ssd_date` ISO 8601. Returns the new sub-doc id.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_seller_un_id": seller_un_id, "p_inv_id": invoice_id}
        params.update(compact({"p_ssd_n": ssd_n}))
        params.update({"p_ssd_date": ssd_date, "user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "add_spec_invoices_ssd_n", params, write=True)

    @mcp.tool()
    async def rsge_spec_add_ssaf(
        invoice_id: int,
        seller_un_id: int,
        ssaf_date: str,
        ssaf_n: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Attach an SSAF excise sub-document to a special invoice (SOAP). WRITE — not
        auto-retried. `ssaf_date` ISO 8601. Returns the new sub-doc id.

        rs.ge QUIRK: this op reuses the SSD wire element names — `ssaf_n`/`ssaf_date` are sent
        as `p_ssd_n`/`p_ssd_date`. Do not "correct" this.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_seller_un_id": seller_un_id, "p_inv_id": invoice_id}
        params.update(compact({"p_ssd_n": ssaf_n}))  # SSAF number on the SSD-named wire field
        params.update({"p_ssd_date": ssaf_date, "user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "add_spec_invoices_ssaf_n", params, write=True)

    @mcp.tool()
    async def rsge_spec_delete_ssd(
        invoice_id: int, seller_un_id: int, ssd_id: int, user_id: int = 0
    ) -> Any:
        """Remove an SSD sub-document from a special invoice (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "del_spec_invoices_ssd",
            {
                "p_seller_un_id": seller_un_id,
                "p_inv_id": invoice_id,
                "p_id": ssd_id,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_delete_ssaf(
        invoice_id: int, seller_un_id: int, ssaf_id: int, user_id: int = 0
    ) -> Any:
        """Remove an SSAF sub-document from a special invoice (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "del_spec_invoices_ssaf",
            {
                "p_seller_un_id": seller_un_id,
                "p_inv_id": invoice_id,
                "p_id": ssaf_id,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_get_ssds(invoice_id: int, un_id: int, user_id: int = 0) -> Any:
        """List the SSD sub-documents of a special invoice (SOAP ``get_spec_ssds_n``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_spec_ssds_n",
            {
                "p_un_id": un_id,
                "p_inv_id": invoice_id,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
            },
        )

    @mcp.tool()
    async def rsge_spec_get_ssafs(invoice_id: int, un_id: int, user_id: int = 0) -> Any:
        """List the SSAF sub-documents of a special invoice (SOAP ``get_spec_ssafs_n``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_spec_ssafs_n",
            {
                "p_un_id": un_id,
                "p_inv_id": invoice_id,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
            },
        )

    # --- transport ---
    @mcp.tool()
    async def rsge_spec_start_transport(invoice_id: int, tr_date: str, user_id: int = 0) -> Any:
        """Initiate transport for a special invoice (SOAP ``start_transport_new_n``). WRITE —
        not auto-retried. `tr_date` ISO 8601 (documented as unused, but a value is required).
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "start_transport_new_n",
            {
                "p_id": invoice_id,
                "p_tr_date": tr_date,
                "user_id": user_id,
                "su": su.su,
                "sp": su.sp,
            },
            write=True,
        )

    @mcp.tool()
    async def rsge_spec_correct_transport_mark(
        invoice_id: int, seller_un_id: int, transport_mark: str | None = None, user_id: int = 0
    ) -> Any:
        """Update the vehicle mark of an in-transit special invoice (SOAP). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_id": invoice_id, "p_seller_un_id": seller_un_id}
        params.update(compact({"p_transport_mark": transport_mark}))
        params.update({"user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "correct_transport_mark", params, write=True)

    @mcp.tool()
    async def rsge_spec_correct_driver_info(
        invoice_id: int,
        seller_un_id: int,
        driver_is_geo: int,
        driver_info: str | None = None,
        driver_no: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """Update the driver of an in-transit special invoice (SOAP ``correct_driver_info``).
        WRITE — not auto-retried. `driver_is_geo`: 0=foreign, 1=Georgian.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_id": invoice_id, "p_seller_un_id": seller_un_id}
        params.update(compact({"p_driver_info": driver_info, "p_driver_no": driver_no}))
        params.update(
            {"p_driver_is_geo": driver_is_geo, "user_id": user_id, "su": su.su, "sp": su.sp}
        )
        return await ctx.soap.call(SPECINVOICES, "correct_driver_info", params, write=True)

    # --- reads / lookups ---
    @mcp.tool()
    async def rsge_spec_get_seller_invoices(
        un_id: int,
        s_dt: str,
        e_dt: str,
        op_s_dt: str,
        op_e_dt: str,
        invoice_no: str | None = None,
        sa_ident_no: str | None = None,
        desc: str | None = None,
        doc_mos_nom: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """List special invoices issued BY a seller (SOAP ``get_seller_invoices_n``). The four
        dates (`s_dt`/`e_dt`/`op_s_dt`/`op_e_dt`) are REQUIRED, ISO 8601.
        """
        su = service_user_or_raise(ctx.settings)
        params = _list_params(
            su,
            user_id,
            un_id,
            s_dt,
            e_dt,
            op_s_dt,
            op_e_dt,
            {
                "invoice_no": invoice_no,
                "sa_ident_no": sa_ident_no,
                "desc": desc,
                "doc_mos_nom": doc_mos_nom,
            },
        )
        return await ctx.soap.call(SPECINVOICES, "get_seller_invoices_n", params)

    @mcp.tool()
    async def rsge_spec_get_buyer_invoices(
        un_id: int,
        s_dt: str,
        e_dt: str,
        op_s_dt: str,
        op_e_dt: str,
        invoice_no: str | None = None,
        sa_ident_no: str | None = None,
        desc: str | None = None,
        doc_mos_nom: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """List special invoices received BY a buyer (SOAP ``get_buyer_invoices_n``). The four
        dates are REQUIRED, ISO 8601.
        """
        su = service_user_or_raise(ctx.settings)
        params = _list_params(
            su,
            user_id,
            un_id,
            s_dt,
            e_dt,
            op_s_dt,
            op_e_dt,
            {
                "invoice_no": invoice_no,
                "sa_ident_no": sa_ident_no,
                "desc": desc,
                "doc_mos_nom": doc_mos_nom,
            },
        )
        return await ctx.soap.call(SPECINVOICES, "get_buyer_invoices_n", params)

    @mcp.tool()
    async def rsge_spec_get_products(
        un_id: int, like: str | None = None, series: str | None = None, user_id: int = 0
    ) -> Any:
        """List an org's oil/fuel products (SOAP ``get_spec_products_n``) for line-item
        `p_good_id` lookup. Optional `like` (text) / `series` filters.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {}
        params.update(compact({"p_like": like}))
        params["p_un_id"] = un_id
        params.update(compact({"p_series": series}))
        params.update({"user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "get_spec_products_n", params)

    @mcp.tool()
    async def rsge_spec_get_product(
        product_id: int, un_id: int, series: str | None = None, user_id: int = 0
    ) -> Any:
        """Fetch a single oil/fuel product by id (SOAP ``get_spec_product_by_id``)."""
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"p_id": product_id, "p_un_id": un_id}
        params.update(compact({"p_series": series}))
        params.update({"user_id": user_id, "su": su.su, "sp": su.sp})
        return await ctx.soap.call(SPECINVOICES, "get_spec_product_by_id", params)

    @mcp.tool()
    async def rsge_spec_get_org_objects(un_id: int, invoice_type: int, user_id: int = 0) -> Any:
        """List an org's facilities (oil load/unload points) by un_id + invoiceType (SOAP
        ``get_v_org_objects_by_un_id_n``) to fill the header's address/N fields.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "get_v_org_objects_by_un_id_n",
            {
                "p_un_id": un_id,
                "user_id": user_id,
                "invoiceType": invoice_type,
                "su": su.su,
                "sp": su.sp,
            },
        )

    @mcp.tool()
    async def rsge_spec_get_my_org_objects(user_id: int = 0) -> Any:
        """List the caller's own registered facilities (SOAP ``get_rs_org_objects``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES, "get_rs_org_objects", {"user_id": user_id, "su": su.su, "sp": su.sp}
        )

    @mcp.tool()
    async def rsge_spec_print_invoice(invoice_id: int, user_id: int = 0) -> Any:
        """Get the printable form of a special invoice (SOAP ``print_invoices``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES,
            "print_invoices",
            {"user_id": user_id, "inv_id": invoice_id, "su": su.su, "sp": su.sp},
        )

    # --- request + admin ---
    @mcp.tool()
    async def rsge_spec_save_invoice_request(
        invoice_id: int,
        buyer_un_id: int,
        seller_un_id: int,
        dt: str,
        overhead_no: str | None = None,
        notes: str | None = None,
        user_id: int = 0,
    ) -> Any:
        """BUYER requests a seller to issue a special invoice (SOAP ``save_invoice_request``).
        WRITE — not auto-retried. `dt` ISO 8601. (Wire buyer field is rs.ge's `bayer_un_id`.)
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
        return await ctx.soap.call(SPECINVOICES, "save_invoice_request", params, write=True)

    @mcp.tool()
    async def rsge_spec_check_users(user_id: int = 0) -> Any:
        """Validate the service-user's NSAF special-invoice access (SOAP ``check_spec_users``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            SPECINVOICES, "check_spec_users", {"user_id": user_id, "su": su.su, "sp": su.sp}
        )

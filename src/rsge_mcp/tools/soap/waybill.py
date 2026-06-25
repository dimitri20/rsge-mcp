"""Waybill tools (SOAP ``WayBillService``).

All require SOAP service-user credentials (``RSGE_SOAP_*``); they raise a clear config
error otherwise. Writes (save/send/close) are not auto-retried.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models.waybill import WaybillGood
from ...soap.credentials import service_user_or_raise
from ...soap.services import WAYBILL
from .._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ...context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_waybill_check_service_user() -> Any:
        """Validate the configured SOAP service-user against WayBillService.

        Returns the un_id / s_user_id, confirming the credentials work.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "chek_service_user", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_waybill(waybill_id: int) -> Any:
        """Fetch a single waybill by its numeric id (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "get_waybill", {"su": su.su, "sp": su.sp, "waybill_id": waybill_id}
        )

    @mcp.tool()
    async def rsge_get_waybills(
        itypes: str | None = None,
        buyer_tin: str | None = None,
        statuses: str | None = None,
        car_number: str | None = None,
        begin_date_s: str | None = None,
        begin_date_e: str | None = None,
        create_date_s: str | None = None,
        create_date_e: str | None = None,
        driver_tin: str | None = None,
        delivery_date_s: str | None = None,
        delivery_date_e: str | None = None,
        full_amount: float | None = None,
        waybill_number: str | None = None,
        close_date_s: str | None = None,
        close_date_e: str | None = None,
        s_user_ids: str | None = None,
        comment: str | None = None,
    ) -> Any:
        """List waybills with optional filters (SOAP WayBillService).

        Dates are ISO 8601 ('YYYY-MM-DDTHH:MM:SS'); `*_s`/`*_e` are range start/end.
        `itypes`, `statuses`, `s_user_ids` are comma-separated id lists. Omitted filters
        are not sent.
        """
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"su": su.su, "sp": su.sp}
        params.update(
            compact(
                {
                    "itypes": itypes,
                    "buyer_tin": buyer_tin,
                    "statuses": statuses,
                    "car_number": car_number,
                    "begin_date_s": begin_date_s,
                    "begin_date_e": begin_date_e,
                    "create_date_s": create_date_s,
                    "create_date_e": create_date_e,
                    "driver_tin": driver_tin,
                    "delivery_date_s": delivery_date_s,
                    "delivery_date_e": delivery_date_e,
                    "full_amount": full_amount,
                    "waybill_number": waybill_number,
                    "close_date_s": close_date_s,
                    "close_date_e": close_date_e,
                    "s_user_ids": s_user_ids,
                    "comment": comment,
                }
            )
        )
        return await ctx.soap.call(WAYBILL, "get_waybills", params)

    @mcp.tool()
    async def rsge_save_waybill(
        waybill_type: int,
        buyer_tin: str,
        seller_un_id: int,
        start_address: str,
        end_address: str,
        goods: list[WaybillGood],
        car_number: str = "",
        driver_tin: str = "",
        transport_cost: float | None = None,
        comment: str = "",
        buyer_name: str | None = None,
        driver_name: str | None = None,
        begin_date: str | None = None,
        trans_id: int | None = None,
        chek_buyer_tin: int | None = None,
        chek_driver_tin: int | None = None,
        full_amount: float | None = None,
        tran_cost_payer: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Create or save a waybill (SOAP WayBillService).

        - `waybill_type`: waybill TYPE code (see rs.ge waybill types).
        - `seller_un_id`: the seller's un_id (from chek_service_user).
        - `goods`: line items; each needs W_NAME, UNIT_ID, QUANTITY, PRICE.
        - `begin_date`: transport start, ISO 8601 ('YYYY-MM-DDTHH:MM:SS').
        - `trans_id`: transport type id (e.g. 2 = road).
        - `chek_buyer_tin` / `chek_driver_tin`: 1 to validate the TIN against the registry.
        - `full_amount`: total amount; `tran_cost_payer`: who pays transport (rs.ge code).
        - `extra`: merged into the WAYBILL object for fields not exposed here.

        Most of the optional fields above are required by the server for a valid draft;
        omitted (None) fields are simply not sent. WRITE — never auto-retried. Saves a
        draft (STATUS=0, no number assigned until send/activate). Returns the saved id.
        """
        su = service_user_or_raise(ctx.settings)
        waybill = compact(
            {
                "GOODS_LIST": {"GOODS": [compact(good.model_dump()) for good in goods]},
                "ID": 0,
                "TYPE": waybill_type,
                "BUYER_TIN": buyer_tin,
                "CHEK_BUYER_TIN": chek_buyer_tin,  # rs.ge's spelling
                "BUYER_NAME": buyer_name,
                "START_ADDRESS": start_address,
                "END_ADDRESS": end_address,
                "DRIVER_TIN": driver_tin,
                "CHEK_DRIVER_TIN": chek_driver_tin,
                "DRIVER_NAME": driver_name,
                "TRANSPORT_COAST": transport_cost,  # rs.ge's spelling
                "STATUS": 0,
                "SELER_UN_ID": seller_un_id,  # rs.ge's spelling
                "FULL_AMOUNT": full_amount,
                "CAR_NUMBER": car_number,
                "BEGIN_DATE": begin_date,
                "TRAN_COST_PAYER": tran_cost_payer,
                "TRANS_ID": trans_id,
                "COMMENT": comment,
            }
        )
        if extra:
            waybill.update(extra)
        return await ctx.soap.call(
            WAYBILL,
            "save_waybill",
            {"su": su.su, "sp": su.sp, "waybill": {"WAYBILL": waybill}},
            write=True,
        )

    @mcp.tool()
    async def rsge_send_waybill(waybill_id: int) -> Any:
        """Activate a waybill for transport (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "send_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_close_waybill(waybill_id: int) -> Any:
        """Close/complete a waybill (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "close_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_del_waybill(waybill_id: int) -> Any:
        """Delete a waybill by id (SOAP WayBillService).

        Only the owning service-user can delete, and typically only drafts (STATUS=0).
        Returns an int code: 1=deleted, -1=not deleted, -101=belongs to another user,
        -100=bad service-user/password. WRITE — never auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "del_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    # --- reference catalogs (reads) ---
    @mcp.tool()
    async def rsge_get_waybill_types() -> Any:
        """List valid waybill TYPE codes (SOAP WayBillService reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_waybill_types", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_waybill_units() -> Any:
        """List measurement units for waybill goods (reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_waybill_units", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_transport_types() -> Any:
        """List transport type codes for waybills (reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_trans_types", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_wood_types() -> Any:
        """List wood/timber category codes (reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_wood_types", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_akciz_codes(search: str | None = None) -> Any:
        """List excise (akciz) goods codes; `search` filters by text (reference)."""
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"su": su.su, "sp": su.sp}
        params.update(compact({"s_text": search}))
        return await ctx.soap.call(WAYBILL, "get_akciz_codes", params)

    @mcp.tool()
    async def rsge_get_waybill_error_codes() -> Any:
        """List waybill error codes and their messages (reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_error_codes", {"su": su.su, "sp": su.sp})

    @mcp.tool()
    async def rsge_get_bar_codes(barcode: str | None = None) -> Any:
        """List the account's saved waybill barcodes; `barcode` filters (reference)."""
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"su": su.su, "sp": su.sp}
        params.update(compact({"bar_code": barcode}))
        return await ctx.soap.call(WAYBILL, "get_bar_codes", params)

    @mcp.tool()
    async def rsge_get_car_numbers() -> Any:
        """List the account's saved vehicle (car) numbers (reference)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(WAYBILL, "get_car_numbers", {"su": su.su, "sp": su.sp})

    # --- lifecycle completers (writes) ---
    @mcp.tool()
    async def rsge_confirm_waybill(waybill_id: int) -> Any:
        """Buyer-confirm a waybill by id (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "confirm_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_reject_waybill(waybill_id: int) -> Any:
        """Buyer-reject a waybill by id (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "reject_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_ref_waybill(waybill_id: int) -> Any:
        """Cancel (refuse) a waybill by id (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "ref_waybill",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_close_waybill_vd(waybill_id: int, delivery_date: str) -> Any:
        """Close a waybill with an explicit delivery date (SOAP). `delivery_date` is ISO
        8601 ('YYYY-MM-DDTHH:MM:SS'). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "close_waybill_vd",
            {"su": su.su, "sp": su.sp, "delivery_date": delivery_date, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_send_waybill_vd(waybill_id: int, begin_date: str) -> Any:
        """Activate (send) a waybill with an explicit transport-start date (SOAP).
        `begin_date` is ISO 8601. WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "send_waybil_vd",  # rs.ge's spelling
            {"su": su.su, "sp": su.sp, "begin_date": begin_date, "waybill_id": waybill_id},
            write=True,
        )

    @mcp.tool()
    async def rsge_ref_waybill_vd(waybill_id: int, comment: str | None = None) -> Any:
        """Cancel a waybill with an optional reason `comment` (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        params: dict[str, Any] = {"su": su.su, "sp": su.sp, "waybill_id": waybill_id}
        params.update(compact({"comment": comment}))
        return await ctx.soap.call(WAYBILL, "ref_waybill_vd", params, write=True)

    # --- identity helpers (reads) ---
    @mcp.tool()
    async def rsge_get_name_from_tin(tin: str) -> Any:
        """Look up a taxpayer's name by TIN (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "get_name_from_tin", {"su": su.su, "sp": su.sp, "tin": tin}
        )

    @mcp.tool()
    async def rsge_get_tin_from_un_id(un_id: int) -> Any:
        """Resolve a TIN from an un_id (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "get_tin_from_un_id", {"su": su.su, "sp": su.sp, "un_id": un_id}
        )

    @mcp.tool()
    async def rsge_get_payer_type_from_un_id(un_id: int) -> Any:
        """Get a taxpayer's payer type from an un_id (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "get_payer_type_from_un_id", {"su": su.su, "sp": su.sp, "un_id": un_id}
        )

    @mcp.tool()
    async def rsge_is_vat_payer(un_id: int) -> Any:
        """Check whether an un_id is a VAT payer (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "is_vat_payer", {"su": su.su, "sp": su.sp, "un_id": un_id}
        )

    @mcp.tool()
    async def rsge_is_vat_payer_tin(tin: str) -> Any:
        """Check whether a TIN is a VAT payer (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "is_vat_payer_tin", {"su": su.su, "sp": su.sp, "tin": tin}
        )

    # --- single reads ---
    @mcp.tool()
    async def rsge_get_waybill_by_number(waybill_number: str) -> Any:
        """Fetch a waybill by its assigned number (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "get_waybill_by_number",
            {"su": su.su, "sp": su.sp, "waybill_number": waybill_number},
        )

    @mcp.tool()
    async def rsge_get_waybill_pdf(waybill_id: int) -> Any:
        """Get the printable waybill as a base64-encoded PDF string (SOAP WayBillService)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "get_print_pdf", {"su": su.su, "sp": su.sp, "waybill_id": waybill_id}
        )

    # --- waybill -> VAT invoice (write) ---
    @mcp.tool()
    async def rsge_waybill_to_invoice(waybill_id: int, in_inv_id: int = 0) -> Any:
        """Issue a VAT invoice from a waybill (SOAP WayBillService `save_invoice`).

        `in_inv_id`: an existing invoice id to attach to (0 = new). WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL,
            "save_invoice",
            {"su": su.su, "sp": su.sp, "waybill_id": waybill_id, "in_inv_id": in_inv_id},
            write=True,
        )

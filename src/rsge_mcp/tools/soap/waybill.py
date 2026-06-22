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
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Create or save a waybill (SOAP WayBillService).

        - `waybill_type`: waybill TYPE code (see rs.ge waybill types).
        - `seller_un_id`: the seller's un_id (from chek_service_user).
        - `goods`: line items; each needs W_NAME, UNIT_ID, QUANTITY, PRICE.
        - `extra`: merged into the WAYBILL object for fields not exposed here.

        WRITE — never auto-retried. Returns the saved waybill id.
        """
        su = service_user_or_raise(ctx.settings)
        waybill = compact(
            {
                "GOODS_LIST": {"GOODS": [compact(good.model_dump()) for good in goods]},
                "ID": 0,
                "TYPE": waybill_type,
                "BUYER_TIN": buyer_tin,
                "SELER_UN_ID": seller_un_id,  # rs.ge's spelling
                "START_ADDRESS": start_address,
                "END_ADDRESS": end_address,
                "DRIVER_TIN": driver_tin,
                "CAR_NUMBER": car_number,
                "TRANSPORT_COAST": transport_cost,  # rs.ge's spelling
                "STATUS": 0,
                "COMMENT": comment,
            }
        )
        if extra:
            waybill.update(extra)
        return await ctx.soap.call(
            WAYBILL, "save_waybill", {"su": su.su, "sp": su.sp, "waybill": {"WAYBILL": waybill}}
        )

    @mcp.tool()
    async def rsge_send_waybill(waybill_id: int) -> Any:
        """Activate a waybill for transport (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "send_waybill", {"su": su.su, "sp": su.sp, "waybill_id": waybill_id}
        )

    @mcp.tool()
    async def rsge_close_waybill(waybill_id: int) -> Any:
        """Close/complete a waybill (SOAP). WRITE — not auto-retried."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(
            WAYBILL, "close_waybill", {"su": su.su, "sp": su.sp, "waybill_id": waybill_id}
        )

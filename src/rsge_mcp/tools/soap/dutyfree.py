"""Duty-free goods journal tools (SOAP ``wsdutyfree``).

Duty-free shop/warehouse goods journals for licensed free-trade operators. Two journals:
``FormGoodsIn`` (goods entering the point — incoming) and ``FormGoodsOut`` (goods sold/leaving
— outgoing), each with a save → send → (receive/reject) lifecycle, plus the reference lookups
(units, point codes, goods statuses) that feed their code fields.

Unlike WayBillService/ntos/specinvoices, this service authenticates with **``userName`` /
``password``** (the bare service username + password, NOT ``su``/``sp``), and they come FIRST
in every op — same scheme as ``tools/soap/taxpayer.py``. All ops are flat (no nested models);
``compact()`` drops unset optionals while preserving WSDL field order. Writes pass
``write=True`` and are never auto-retried.

Only the modern CamelCase ``*FormGoods*`` API is wrapped; the protocol deprecates the legacy
``form4_*``/``form5_*`` ops (Form4≈FormGoodsIn, Form5≈FormGoodsOut). Batch ``*List``, fuel
``*Oil`` variants, and barcode ops are intentionally out of scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...soap.credentials import ServiceUser, service_user_or_raise
from ...soap.services import DUTYFREE
from .._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ...context import AppContext


def _auth(su: ServiceUser) -> dict[str, Any]:
    """Seed a param dict with the duty-free credential pair (userName/password, first)."""
    return {"userName": su.user, "password": su.password}


def register(mcp: FastMCP, ctx: AppContext) -> None:
    # --- FormGoodsIn: incoming goods journal ---
    @mcp.tool()
    async def rsge_df_save_goods_in(
        declaration_date: str,
        unit_type_id: int,
        quantity: float,
        unit_price: float,
        status_id: int,
        operation_id: int,
        bar_code: str | None = None,
        cert_number: str | None = None,
        bill_number: str | None = None,
        goods_name: str | None = None,
        sesesn_code: str | None = None,
        unit_type: str | None = None,
        remark: str | None = None,
    ) -> Any:
        """Create an incoming duty-free goods record (SOAP ``SaveFormGoodsIn``). WRITE — not
        auto-retried. Returns the new record id.

        `unit_type_id`/`status_id`/`operation_id` are codes — look them up with
        `rsge_df_get_units` / `rsge_df_get_goods_statuses` / `rsge_df_get_goods_in_operations`.
        Dates are ISO 8601.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params.update(
            compact(
                {
                    "barCode": bar_code,
                    "declarationDate": declaration_date,
                    "certNumber": cert_number,
                    "billNumber": bill_number,
                    "goodsName": goods_name,
                    "sesesnCode": sesesn_code,
                    "unitTypeID": unit_type_id,
                    "unitType": unit_type,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "statusID": status_id,
                    "remark": remark,
                    "operationID": operation_id,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "SaveFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_update_goods_in(
        record_id: int,
        declaration_date: str,
        unit_type_id: int,
        quantity: float,
        unit_price: float,
        operation_id: int,
        bar_code: str | None = None,
        cert_number: str | None = None,
        bill_number: str | None = None,
        goods_name: str | None = None,
        sesesn_code: str | None = None,
        unit_type: str | None = None,
        remark: str | None = None,
    ) -> Any:
        """Edit an unsent incoming goods record (SOAP ``UpdateFormGoodsIn``). WRITE — not
        auto-retried. (No `status_id` here — set at save.)
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "barCode": bar_code,
                    "declarationDate": declaration_date,
                    "certNumber": cert_number,
                    "billNumber": bill_number,
                    "goodsName": goods_name,
                    "sesesnCode": sesesn_code,
                    "unitTypeID": unit_type_id,
                    "unitType": unit_type,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "remark": remark,
                    "operationID": operation_id,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "UpdateFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_send_goods_in(
        record_id: int,
        declaration_date: str,
        unit_type_id: int,
        quantity: float,
        unit_price: float,
        operation_id: int,
        bar_code: str | None = None,
        cert_number: str | None = None,
        bill_number: str | None = None,
        goods_name: str | None = None,
        sesesn_code: str | None = None,
        unit_type: str | None = None,
        remark: str | None = None,
    ) -> Any:
        """Submit an incoming goods record to rs.ge (SOAP ``SendFormGoodsIn``). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "barCode": bar_code,
                    "declarationDate": declaration_date,
                    "certNumber": cert_number,
                    "billNumber": bill_number,
                    "goodsName": goods_name,
                    "sesesnCode": sesesn_code,
                    "unitTypeID": unit_type_id,
                    "unitType": unit_type,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "remark": remark,
                    "operationID": operation_id,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "SendFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_send_receive_goods_in(
        record_id: int,
        declaration_date: str,
        unit_price: float,
        bill_number: str | None = None,
        remark: str | None = None,
    ) -> Any:
        """Confirm receipt of an incoming goods record (SOAP ``SendReceiveFormGoodsIn``).
        WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "declarationDate": declaration_date,
                    "billNumber": bill_number,
                    "unitPrice": unit_price,
                    "remark": remark,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "SendReceiveFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_update_receive_goods_in(
        record_id: int,
        declaration_date: str,
        unit_price: float,
        bill_number: str | None = None,
        remark: str | None = None,
    ) -> Any:
        """Edit an already-received incoming goods record (SOAP ``UpdateReceiveFormGoodsIn``).
        WRITE — not auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "declarationDate": declaration_date,
                    "billNumber": bill_number,
                    "unitPrice": unit_price,
                    "remark": remark,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "UpdateReceiveFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_reject_goods_in(record_id: int, remark: str | None = None) -> Any:
        """Reject an incoming goods record (SOAP ``RejectFormGoodsIn``). WRITE — not retried."""
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(compact({"remark": remark}))
        return await ctx.soap.call(DUTYFREE, "RejectFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_delete_goods_in(record_id: int, remark: str | None = None) -> Any:
        """Delete/cancel an incoming goods record (SOAP ``DeleteFormGoodsIn``). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(compact({"remark": remark}))
        return await ctx.soap.call(DUTYFREE, "DeleteFormGoodsIn", params, write=True)

    @mcp.tool()
    async def rsge_df_get_goods_in(record_id: int) -> Any:
        """Fetch one incoming goods record by id (SOAP ``GetFormGoodsIn``)."""
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsIn", params)

    @mcp.tool()
    async def rsge_df_list_goods_in(start_date: str, end_date: str) -> Any:
        """List incoming goods records for a date range (SOAP ``GetFormGoodsInList``). ISO 8601."""
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params.update({"startDate": start_date, "endDate": end_date})
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsInList", params)

    @mcp.tool()
    async def rsge_df_get_goods_in_operations() -> Any:
        """List the operation types for incoming goods (SOAP ``GetFormGoodsInOperations``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsInOperations", _auth(su))

    # --- FormGoodsOut: sold/outgoing goods journal ---
    @mcp.tool()
    async def rsge_df_save_goods_out(
        sale_date: str,
        quantity: float,
        unit_price: float,
        operation_id: int,
        bar_code: str | None = None,
        sesesn_code: str | None = None,
        person_number: str | None = None,
        air_ticket_number: str | None = None,
        air_staff_number: str | None = None,
        mfa_document: str | None = None,
        other_document: str | None = None,
        transfer_document: str | None = None,
        remark: str | None = None,
        waybill_number: str | None = None,
        send_point_code: str | None = None,
    ) -> Any:
        """Create an outgoing (sold/transferred) duty-free goods record (SOAP
        ``SaveFormGoodsOut``). WRITE — not auto-retried. Returns the new record id.

        Sales to travellers use `person_number`/`air_ticket_number`; transfers use
        `transfer_document`/`send_point_code`. Dates are ISO 8601.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params.update(
            compact(
                {
                    "saleDate": sale_date,
                    "barCode": bar_code,
                    "sesesnCode": sesesn_code,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "personNumber": person_number,
                    "airTicketNumber": air_ticket_number,
                    "airStaffNumber": air_staff_number,
                    "mfaDocument": mfa_document,
                    "otherDocument": other_document,
                    "transferDocument": transfer_document,
                    "remark": remark,
                    "waybillNumber": waybill_number,
                    "operationID": operation_id,
                    "sendPointCode": send_point_code,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "SaveFormGoodsOut", params, write=True)

    @mcp.tool()
    async def rsge_df_update_goods_out(
        record_id: int,
        sale_date: str,
        quantity: float,
        unit_price: float,
        operation_id: int,
        bar_code: str | None = None,
        sesesn_code: str | None = None,
        person_number: str | None = None,
        air_ticket_number: str | None = None,
        air_staff_number: str | None = None,
        mfa_document: str | None = None,
        other_document: str | None = None,
        transfer_document: str | None = None,
        remark: str | None = None,
        waybill_number: str | None = None,
        send_point_code: str | None = None,
    ) -> Any:
        """Edit an unsent outgoing goods record (SOAP ``UpdateFormGoodsOut``). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "saleDate": sale_date,
                    "barCode": bar_code,
                    "sesesnCode": sesesn_code,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "personNumber": person_number,
                    "airTicketNumber": air_ticket_number,
                    "airStaffNumber": air_staff_number,
                    "mfaDocument": mfa_document,
                    "otherDocument": other_document,
                    "transferDocument": transfer_document,
                    "remark": remark,
                    "waybillNumber": waybill_number,
                    "operationID": operation_id,
                    "sendPointCode": send_point_code,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "UpdateFormGoodsOut", params, write=True)

    @mcp.tool()
    async def rsge_df_send_goods_out(
        record_id: int,
        sale_date: str,
        quantity: float,
        unit_price: float,
        operation_id: int,
        bar_code: str | None = None,
        sesesn_code: str | None = None,
        person_number: str | None = None,
        air_ticket_number: str | None = None,
        air_staff_number: str | None = None,
        mfa_document: str | None = None,
        other_document: str | None = None,
        transfer_document: str | None = None,
        remark: str | None = None,
        waybill_number: str | None = None,
        send_point_code: str | None = None,
    ) -> Any:
        """Submit an outgoing goods record to rs.ge (SOAP ``SendFormGoodsOut``). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(
            compact(
                {
                    "saleDate": sale_date,
                    "barCode": bar_code,
                    "sesesnCode": sesesn_code,
                    "quantity": quantity,
                    "unitPrice": unit_price,
                    "personNumber": person_number,
                    "airTicketNumber": air_ticket_number,
                    "airStaffNumber": air_staff_number,
                    "mfaDocument": mfa_document,
                    "otherDocument": other_document,
                    "transferDocument": transfer_document,
                    "remark": remark,
                    "waybillNumber": waybill_number,
                    "operationID": operation_id,
                    "sendPointCode": send_point_code,
                }
            )
        )
        return await ctx.soap.call(DUTYFREE, "SendFormGoodsOut", params, write=True)

    @mcp.tool()
    async def rsge_df_delete_goods_out(record_id: int, remark: str | None = None) -> Any:
        """Delete/cancel an outgoing goods record (SOAP ``DeleteFormGoodsOut``). WRITE — not
        auto-retried.
        """
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        params.update(compact({"remark": remark}))
        return await ctx.soap.call(DUTYFREE, "DeleteFormGoodsOut", params, write=True)

    @mcp.tool()
    async def rsge_df_get_goods_out(record_id: int) -> Any:
        """Fetch one outgoing goods record by id (SOAP ``GetFormGoodsOut``)."""
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params["id"] = record_id
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsOut", params)

    @mcp.tool()
    async def rsge_df_list_goods_out(start_date: str, end_date: str) -> Any:
        """List outgoing goods records for a date range (SOAP ``GetFormGoodsOutList``). ISO 8601."""
        su = service_user_or_raise(ctx.settings)
        params = _auth(su)
        params.update({"startDate": start_date, "endDate": end_date})
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsOutList", params)

    @mcp.tool()
    async def rsge_df_get_goods_out_operations() -> Any:
        """List the operation types for outgoing goods (SOAP ``GetFormGoodsOutOperations``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(DUTYFREE, "GetFormGoodsOutOperations", _auth(su))

    # --- reference lookups (feed unitTypeID / pointCode / statusID) ---
    @mcp.tool()
    async def rsge_df_get_units() -> Any:
        """List duty-free unit types (SOAP ``get_units``) — id + name for `unit_type_id`."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(DUTYFREE, "get_units", _auth(su))

    @mcp.tool()
    async def rsge_df_get_point_codes() -> Any:
        """List duty-free point codes (SOAP ``get_point_codes``)."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(DUTYFREE, "get_point_codes", _auth(su))

    @mcp.tool()
    async def rsge_df_get_goods_statuses() -> Any:
        """List goods status codes (SOAP ``get_goods_statuses``) — id + name for `status_id`."""
        su = service_user_or_raise(ctx.settings)
        return await ctx.soap.call(DUTYFREE, "get_goods_statuses", _auth(su))

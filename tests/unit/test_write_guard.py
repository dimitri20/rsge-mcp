"""The read-only write guard: every mutating tool is blocked unless RSGE_ALLOW_WRITES.

The parametrized block is a fail-closed safety net — if a new write tool forgets to pass
``write=True``, its entry here will let the call through and the test will fail.
"""

from __future__ import annotations

import dataclasses

import httpx
import pytest
import respx

from helpers import FakeMCP, make_ctx, soap_scalar
from rsge_mcp.errors import RsgeWriteBlockedError
from rsge_mcp.models.invoice import InvoiceGood
from rsge_mcp.models.waybill import WaybillGood
from rsge_mcp.soap.services import WAYBILL
from rsge_mcp.tools import employees, invoice
from rsge_mcp.tools.soap import ntos_invoice, waybill

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_DT = "01-01-2026 00:00:00"

# Every mutating tool, with minimal valid arguments. Must list ALL 40 writes.
WRITE_CALLS = {
    "save_invoice": lambda t: t["rsge_save_invoice"](
        seller_tin="1",
        buyer_tin="2",
        operation_date=_DT,
        goods=[InvoiceGood(GOODS_NAME="X", UNIT_ID=1, QUANTITY=1, UNIT_PRICE=1.0)],
    ),
    "confirm_invoice": lambda t: t["rsge_confirm_invoice"](1),
    "refuse_invoice": lambda t: t["rsge_refuse_invoice"](1),
    "cancel_invoice": lambda t: t["rsge_cancel_invoice"](1),
    "save_waybill": lambda t: t["rsge_save_waybill"](
        waybill_type=2,
        buyer_tin="1",
        seller_un_id=1,
        start_address="A",
        end_address="B",
        goods=[WaybillGood(W_NAME="X", UNIT_ID=1, QUANTITY=1, PRICE=1.0)],
    ),
    "send_waybill": lambda t: t["rsge_send_waybill"](1),
    "close_waybill": lambda t: t["rsge_close_waybill"](1),
    "del_waybill": lambda t: t["rsge_del_waybill"](1),
    "ntos_save_invoice": lambda t: t["rsge_ntos_save_invoice"](
        invoice_id=1,
        operation_date=_DT,
        seller_un_id=1,
        buyer_un_id=2,
        overhead_dt=_DT,
        b_s_user_id=1,
    ),
    "ntos_save_invoice_desc": lambda t: t["rsge_ntos_save_invoice_desc"](
        invoice_id=1,
        goods_name="X",
        g_number=1,
        full_amount=1,
        drg_amount=0,
        aqcizi_amount=0,
        akciz_id=0,
    ),
    "ntos_change_invoice_status": lambda t: t["rsge_ntos_change_invoice_status"](
        invoice_id=1, status=2
    ),
    "activate_invoice": lambda t: t["rsge_activate_invoice"](1),
    "activate_invoices": lambda t: t["rsge_activate_invoices"]([1]),
    "delete_invoice": lambda t: t["rsge_delete_invoice"](1),
    "confirm_invoices": lambda t: t["rsge_confirm_invoices"]([1]),
    "refuse_invoices": lambda t: t["rsge_refuse_invoices"]([1]),
    "clear_barcodes": lambda t: t["rsge_clear_barcodes"](),
    "get_seqnum": lambda t: t["rsge_get_seqnum"]("202601"),
    "create_decl": lambda t: t["rsge_create_decl"]([1], "202601"),
    "save_employee": lambda t: t["rsge_save_employee"](tin="1", phone="5", work_type=1),
    "confirm_waybill": lambda t: t["rsge_confirm_waybill"](1),
    "reject_waybill": lambda t: t["rsge_reject_waybill"](1),
    "ref_waybill": lambda t: t["rsge_ref_waybill"](1),
    "close_waybill_vd": lambda t: t["rsge_close_waybill_vd"](1, "2026-01-01T00:00:00"),
    "send_waybill_vd": lambda t: t["rsge_send_waybill_vd"](1, "2026-01-01T00:00:00"),
    "ref_waybill_vd": lambda t: t["rsge_ref_waybill_vd"](1),
    "waybill_to_invoice": lambda t: t["rsge_waybill_to_invoice"](1),
    # ntos long-tail (P4)
    "ntos_save_invoice_a": lambda t: t["rsge_ntos_save_invoice_a"](
        invoice_id=1,
        operation_date=_DT,
        seller_un_id=1,
        buyer_un_id=2,
        overhead_dt=_DT,
        b_s_user_id=1,
    ),
    "ntos_save_invoice_n": lambda t: t["rsge_ntos_save_invoice_n"](
        invoice_id=1,
        operation_date=_DT,
        seller_un_id=1,
        buyer_un_id=2,
        overhead_dt=_DT,
        b_s_user_id=1,
    ),
    "ntos_correct_invoice": lambda t: t["rsge_ntos_correct_invoice"](1, 1),
    "ntos_cancel_invoice": lambda t: t["rsge_ntos_cancel_invoice"](1),
    "ntos_delete_invoice_desc": lambda t: t["rsge_ntos_delete_invoice_desc"](1, 2),
    "ntos_accept_invoice_status": lambda t: t["rsge_ntos_accept_invoice_status"](1, 2),
    "ntos_refuse_invoice_status": lambda t: t["rsge_ntos_refuse_invoice_status"](1),
    "ntos_attach_advance_invoice": lambda t: t["rsge_ntos_attach_advance_invoice"](1, 2, 3.0, 4),
    "ntos_update_advance_invoice": lambda t: t["rsge_ntos_update_advance_invoice"](1, 2, 3.0),
    "ntos_detach_advance_invoices": lambda t: t["rsge_ntos_detach_advance_invoices"](1, [2]),
    "ntos_save_invoice_request": lambda t: t["rsge_ntos_save_invoice_request"](1, 2, 3, _DT),
    "ntos_accept_invoice_request": lambda t: t["rsge_ntos_accept_invoice_request"](1, 2),
    "ntos_del_invoice_request": lambda t: t["rsge_ntos_del_invoice_request"](1, 2),
}


def _register_all(fake: FakeMCP, ctx) -> None:
    for module in (invoice, employees, waybill, ntos_invoice):
        module.register(fake, ctx)


@pytest.mark.parametrize("name", list(WRITE_CALLS))
async def test_write_blocked_in_readonly(soap_settings, name) -> None:
    readonly = dataclasses.replace(soap_settings, allow_writes=False)
    async with make_ctx(readonly) as ctx:
        fake = FakeMCP()
        _register_all(fake, ctx)
        with pytest.raises(RsgeWriteBlockedError):
            await WRITE_CALLS[name](fake.tools)


async def test_write_allowed_when_enabled(soap_settings) -> None:
    cfg = dataclasses.replace(soap_settings, allow_writes=True)
    with respx.mock as router:
        router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("del_waybill", del_waybillResult="1"))
        )
        async with make_ctx(cfg) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            res = await fake.tools["rsge_del_waybill"](1)
        assert res == {"del_waybillResult": "1"}


async def test_reads_not_blocked_in_readonly(soap_settings) -> None:
    readonly = dataclasses.replace(soap_settings, allow_writes=False)
    with respx.mock as router:
        router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("get_waybill", get_waybillResult="ok")
            )
        )
        async with make_ctx(readonly) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_waybill"](1)  # a read works in read-only mode

"""Tests for the SOAP tool modules (request shaping + credential gating)."""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers import FakeMCP, make_ctx, soap_diffgram, soap_scalar
from rsge_mcp.errors import RsgeConfigError
from rsge_mcp.models.waybill import WaybillGood
from rsge_mcp.soap.services import NTOS, WAYBILL
from rsge_mcp.tools.soap import ntos_invoice, waybill

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _content(route) -> str:
    return route.calls.last.request.content.decode()


async def test_get_waybill_sends_credentials_and_id(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("get_waybill", get_waybillResult="ok")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_waybill"](601759104)
        body = _content(route)
        assert "<su>itana:206322102</su>" in body
        assert "<sp>123456</sp>" in body
        assert "<waybill_id>601759104</waybill_id>" in body


async def test_save_waybill_builds_nested_goods(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_waybill", save_waybillResult="500")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_save_waybill"](
                waybill_type=2,
                buyer_tin="123",
                seller_un_id=731937,
                start_address="A",
                end_address="B",
                goods=[WaybillGood(W_NAME="Widget", UNIT_ID=1, QUANTITY=2, PRICE=5.0)],
            )
        body = _content(route)
        assert "<waybill><WAYBILL>" in body
        assert "<GOODS_LIST><GOODS>" in body
        assert "<W_NAME>Widget</W_NAME>" in body
        assert "<SELER_UN_ID>731937</SELER_UN_ID>" in body  # rs.ge spelling preserved


async def test_save_waybill_emits_new_optional_fields(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_waybill", save_waybillResult="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_save_waybill"](
                waybill_type=2,
                buyer_tin="123",
                seller_un_id=731937,
                start_address="A",
                end_address="B",
                goods=[WaybillGood(W_NAME="X", UNIT_ID=1, QUANTITY=1, PRICE=1.0)],
                buyer_name="Buyer Co",
                begin_date="2026-06-23T10:00:00",
                chek_buyer_tin=1,
                full_amount=5.0,
                trans_id=2,
            )
        body = _content(route)
        assert "<BUYER_NAME>Buyer Co</BUYER_NAME>" in body
        assert "<BEGIN_DATE>2026-06-23T10:00:00</BEGIN_DATE>" in body
        assert "<CHEK_BUYER_TIN>1</CHEK_BUYER_TIN>" in body
        assert "<FULL_AMOUNT>5.0</FULL_AMOUNT>" in body
        assert "<TRANS_ID>2</TRANS_ID>" in body


async def test_save_waybill_omits_unset_optional_fields(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_waybill", save_waybillResult="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_save_waybill"](
                waybill_type=2,
                buyer_tin="123",
                seller_un_id=731937,
                start_address="A",
                end_address="B",
                goods=[WaybillGood(W_NAME="X", UNIT_ID=1, QUANTITY=1, PRICE=1.0)],
            )
        body = _content(route)
        for tag in ("BUYER_NAME", "DRIVER_NAME", "BEGIN_DATE", "FULL_AMOUNT", "TRANS_ID"):
            assert f"<{tag}>" not in body  # None dropped by compact()


async def test_del_waybill_sends_credentials_and_id(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("del_waybill", del_waybillResult="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            result = await fake.tools["rsge_del_waybill"](601759104)
        assert result == {"del_waybillResult": "1"}
        body = _content(route)
        assert "<su>itana:206322102</su>" in body
        assert "<waybill_id>601759104</waybill_id>" in body
        assert body.index("<su>") < body.index("<sp>") < body.index("<waybill_id>")  # WSDL order


async def test_del_waybill_requires_soap_credentials(settings) -> None:
    async with make_ctx(settings) as ctx:  # no SOAP creds
        fake = FakeMCP()
        waybill.register(fake, ctx)
        with pytest.raises(RsgeConfigError):
            await fake.tools["rsge_del_waybill"](1)


async def test_save_waybill_requires_soap_credentials(settings) -> None:
    async with make_ctx(settings) as ctx:  # no SOAP creds
        fake = FakeMCP()
        waybill.register(fake, ctx)
        with pytest.raises(RsgeConfigError):
            await fake.tools["rsge_save_waybill"](
                waybill_type=2,
                buyer_tin="1",
                seller_un_id=1,
                start_address="A",
                end_address="B",
                goods=[WaybillGood(W_NAME="x", UNIT_ID=1, QUANTITY=1, PRICE=1.0)],
            )


async def test_ntos_get_invoice_param_order(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("get_invoice", get_invoiceResult="ok")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_get_invoice"](161058850, user_id=783)
        body = _content(route)
        # WSDL order: user_id, invois_id, su, sp
        assert (
            body.index("<user_id>")
            < body.index("<invois_id>")
            < body.index("<su>")
            < body.index("<sp>")
        )
        assert "<invois_id>161058850</invois_id>" in body


async def test_ntos_seller_invoices_filters_and_su_last(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_diffgram("get_seller_invoices", "INVOICE", [{"ID": "1"}])
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            data = await fake.tools["rsge_ntos_get_seller_invoices"](un_id=731937, invoice_no="A-1")
        assert data == [{"ID": "1"}]
        body = _content(route)
        assert "<un_id>731937</un_id>" in body
        assert "<invoice_no>A-1</invoice_no>" in body
        assert body.index("<un_id>") < body.index("<su>")  # su/sp last for ntos


async def test_ntos_save_invoice_order_and_optional(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice", save_invoiceResult="42")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_save_invoice"](
                invoice_id=42,
                operation_date="2026-02-01T10:00:00",
                seller_un_id=731937,
                buyer_un_id=555,
                overhead_dt="2026-02-01T09:00:00",
                b_s_user_id=135,
                user_id=783,
            )
        body = _content(route)
        # WSDL order: user_id, invois_id, operation_date, seller_un_id, buyer_un_id,
        # [overhead_no], overhead_dt, b_s_user_id, su, sp
        order = [
            "<user_id>",
            "<invois_id>",
            "<operation_date>",
            "<seller_un_id>",
            "<buyer_un_id>",
            "<overhead_dt>",
            "<b_s_user_id>",
            "<su>",
            "<sp>",
        ]
        positions = [body.index(tag) for tag in order]
        assert positions == sorted(positions)
        assert "<overhead_no>" not in body  # optional, omitted when None
        assert "<invois_id>42</invois_id>" in body


async def test_ntos_save_invoice_desc_su_sp_mid_sequence(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice_desc", save_invoice_descResult="ok")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_save_invoice_desc"](
                invoice_id=42,
                goods_name="Widget",
                g_number=2,
                full_amount=200,
                drg_amount=36,
                aqcizi_amount=0,
                akciz_id=0,
            )
        body = _content(route)
        # su/sp sit between id and invois_id, not first/last
        assert body.index("<id>") < body.index("<su>") < body.index("<invois_id>")
        assert body.index("<invois_id>") < body.index("<goods>") < body.index("<g_number>")
        assert "<goods>Widget</goods>" in body
        assert "<g_unit>" not in body  # optional, omitted


async def test_ntos_change_invoice_status_body(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("change_invoice_status", change_invoice_statusResult="ok")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_change_invoice_status"](invoice_id=42, status=2)
        body = _content(route)
        assert "<inv_id>42</inv_id>" in body
        assert "<status>2</status>" in body


async def test_ntos_save_invoice_requires_credentials(settings) -> None:
    async with make_ctx(settings) as ctx:  # no SOAP creds
        fake = FakeMCP()
        ntos_invoice.register(fake, ctx)
        with pytest.raises(RsgeConfigError):
            await fake.tools["rsge_ntos_change_invoice_status"](invoice_id=1, status=2)

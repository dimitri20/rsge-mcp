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

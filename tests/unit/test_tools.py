"""Tests for the MCP tool modules (request shaping + response unwrapping)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from helpers import FakeMCP, env, make_ctx
from rsge_mcp.models.invoice import InvoiceGood
from rsge_mcp.tools import auth_tools, common, invoice, org, taxpayer_public

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

AUTH = "https://eapi.rs.ge/Users/Authenticate"


def _token_route(router) -> None:
    router.post(AUTH).mock(
        return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
    )


def _body(route) -> dict:
    return json.loads(route.calls.last.request.content)


async def test_get_org_info_by_tin(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Org/GetOrgInfoByTin").mock(
            return_value=httpx.Response(200, json=env({"Name": "ACME"}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            org.register(fake, ctx)
            data = await fake.tools["rsge_get_org_info_by_tin"]("123")
        assert data == {"Name": "ACME"}
        assert _body(target) == {"Tin": "123"}


async def test_get_units_sends_empty_body(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Common/GetUnits").mock(
            return_value=httpx.Response(200, json=env([{"value": "1", "label": "ცალი"}]))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            common.register(fake, ctx)
            data = await fake.tools["rsge_get_units"]()
        assert data == [{"value": "1", "label": "ცალი"}]
        assert _body(target) == {}


async def test_taxpayer_public_info_is_unauthenticated(settings) -> None:
    with respx.mock as router:
        auth = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        target = router.post("https://xdata.rs.ge/TaxPayer/RSPublicInfo").mock(
            return_value=httpx.Response(200, json=[{"Status": "active"}])
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            taxpayer_public.register(fake, ctx)
            data = await fake.tools["rsge_taxpayer_public_info"]("206322102")
        assert data == [{"Status": "active"}]
        assert not auth.called  # public endpoint: no login
        assert "authorization" not in target.calls.last.request.headers
        assert _body(target) == {"IdentCode": "206322102"}


async def test_save_invoice_builds_nested_body(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Invoice/SaveInvoice").mock(
            return_value=httpx.Response(200, json=env({"INVOICE_ID": "555"}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            data = await fake.tools["rsge_save_invoice"](
                seller_tin="111",
                buyer_tin="222",
                operation_date="01-02-2026 10:00:00",
                goods=[InvoiceGood(GOODS_NAME="Widget", UNIT_ID=1, QUANTITY=2, UNIT_PRICE=5.0)],
            )
        assert data == {"INVOICE_ID": "555"}
        inv = _body(target)["INVOICE"]
        assert inv["TIN_SELLER"] == "111"
        assert inv["TIN_BUYER"] == "222"
        assert inv["OPERATION_DATE"] == "01-02-2026 10:00:00"
        assert inv["INV_CATEGORY"] == 1 and inv["INV_TYPE"] == 2
        good = inv["INVOICE_GOODS"][0]
        assert good["GOODS_NAME"] == "Widget"
        assert good["UNIT_ID"] == 1 and good["QUANTITY"] == 2 and good["UNIT_PRICE"] == 5.0
        assert good["ID"] == 0
        assert "BARCODE" not in good and "VAT_TYPE" not in good  # None dropped by compact()


async def test_save_invoice_extra_merged(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Invoice/SaveInvoice").mock(
            return_value=httpx.Response(200, json=env({"INVOICE_ID": "9"}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            await fake.tools["rsge_save_invoice"](
                seller_tin="1",
                buyer_tin="2",
                operation_date="01-02-2026 10:00:00",
                goods=[InvoiceGood(GOODS_NAME="X", UNIT_ID=1, QUANTITY=1, UNIT_PRICE=1.0)],
                extra={"AMOUNT_VAT": "18"},
            )
        assert _body(target)["INVOICE"]["AMOUNT_VAT"] == "18"


async def test_confirm_invoice_sends_id(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Invoice/ConfirmInvoice").mock(
            return_value=httpx.Response(200, json=env({"ok": True}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            await fake.tools["rsge_confirm_invoice"](7)
        assert _body(target) == {"INVOICE": {"ID": 7}}


async def test_get_vat_payer_status_body(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Org/GetVatPayerStatus").mock(
            return_value=httpx.Response(200, json=env({"IsVatPayer": True}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            org.register(fake, ctx)
            data = await fake.tools["rsge_get_vat_payer_status"]("123", "01-02-2026 10:00:00")
        assert data == {"IsVatPayer": True}
        assert _body(target) == {"Tin": "123", "VatDate": "01-02-2026 10:00:00"}


async def test_get_transaction_result_body(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post("https://eapi.rs.ge/Common/GetTransactionResult").mock(
            return_value=httpx.Response(200, json=env({"INVOICE_ID": "7"}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            common.register(fake, ctx)
            data = await fake.tools["rsge_get_transaction_result"]("uuid-1")
        assert data == {"INVOICE_ID": "7"}
        assert _body(target) == {"TransactionId": "uuid-1"}


@pytest.mark.parametrize(
    "tool_name,path",
    [
        ("rsge_refuse_invoice", "https://eapi.rs.ge/Invoice/RefuseInvoice"),
        ("rsge_cancel_invoice", "https://eapi.rs.ge/Invoice/CancelInvoice"),
    ],
)
async def test_invoice_lifecycle_sends_id(settings, tool_name, path) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(path).mock(return_value=httpx.Response(200, json=env({"ok": True})))
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            await fake.tools[tool_name](42)
        assert _body(target) == {"INVOICE": {"ID": 42}}


async def test_save_invoice_wait_polls_transaction(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        router.post("https://eapi.rs.ge/Invoice/SaveInvoice").mock(
            return_value=httpx.Response(200, json=env({"TransactionId": "tx-9"}))
        )
        result = router.post("https://eapi.rs.ge/Common/GetTransactionResult").mock(
            return_value=httpx.Response(200, json=env({"INVOICE_ID": "777"}))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            data = await fake.tools["rsge_save_invoice"](
                seller_tin="1",
                buyer_tin="2",
                operation_date="01-02-2026 10:00:00",
                goods=[InvoiceGood(GOODS_NAME="X", UNIT_ID=1, QUANTITY=1, UNIT_PRICE=1.0)],
                wait=True,
            )
        assert data == {"INVOICE_ID": "777"}
        assert _body(result) == {"TransactionId": "tx-9"}


async def test_submit_pin_tool_in_tool_mode(settings) -> None:
    import dataclasses

    from rsge_mcp.config import TwoFactorMode

    cfg = dataclasses.replace(settings, two_factor_mode=TwoFactorMode.TOOL)
    with respx.mock as router:
        router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"PIN_TOKEN": "P", "MASKED_MOBILE": "*16"}))
        )
        router.post("https://eapi.rs.ge/Users/AuthenticatePin").mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        async with make_ctx(cfg) as ctx:
            from rsge_mcp.errors import RsgePinRequiredError

            with pytest.raises(RsgePinRequiredError):
                await ctx.session.get_token()
            fake = FakeMCP()
            auth_tools.register(fake, ctx)
            msg = await fake.tools["rsge_submit_pin"]("1234")
        assert "authenticated" in msg


async def test_signout_invalidates_session(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        out = router.post("https://eapi.rs.ge/Users/SignOut").mock(
            return_value=httpx.Response(200, json=env({}))
        )
        async with make_ctx(settings) as ctx:
            await ctx.session.get_token()  # establish a token
            fake = FakeMCP()
            auth_tools.register(fake, ctx)
            msg = await fake.tools["rsge_signout"]()
            assert ctx.session.has_token is False
        assert out.called
        assert msg == "Signed out."


# --- P1: invoice lifecycle + reference tools ---


async def _invoice_call(settings, tool, path, response, *args, **kwargs):
    """Register the invoice module, call `tool`, return (returned_data, request_body)."""
    with respx.mock as router:
        _token_route(router)
        target = router.post(f"https://eapi.rs.ge{path}").mock(
            return_value=httpx.Response(200, json=env(response))
        )
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            invoice.register(fake, ctx)
            data = await fake.tools[tool](*args, **kwargs)
        return data, _body(target)


async def test_list_excise(settings) -> None:
    data, body = await _invoice_call(
        settings,
        "rsge_list_excise",
        "/Invoice/ListExcise",
        {"Data": {"Rows": []}},
        {"PRODUCT_NAME": "X"},
    )
    assert data == {"Data": {"Rows": []}}
    assert body == {"PRODUCT_NAME": "X"}


async def test_list_excise_empty_filters(settings) -> None:
    _, body = await _invoice_call(settings, "rsge_list_excise", "/Invoice/ListExcise", {})
    assert body == {}


async def test_list_barcodes_empty_filters(settings) -> None:
    _, body = await _invoice_call(settings, "rsge_list_barcodes", "/Invoice/ListBarCodes", {})
    assert body == {}


async def test_get_barcode_uses_camelcase_key(settings) -> None:
    data, body = await _invoice_call(
        settings, "rsge_get_barcode", "/Invoice/GetBarCode", {"RESULT": {"BARCODE": "55"}}, "55"
    )
    assert data == {"RESULT": {"BARCODE": "55"}}
    assert body == {"barCode": "55"}


async def test_list_goods_batch_body(settings) -> None:
    _, body = await _invoice_call(
        settings, "rsge_list_goods", "/Invoice/ListGoods", {"INVOICES": []}, [1137, 1138]
    )
    assert body == {"Invoices": [{"ID": 1137}, {"ID": 1138}]}


async def test_get_actions(settings) -> None:
    data, body = await _invoice_call(
        settings, "rsge_get_actions", "/Invoice/GetActions", [{"ID": "3", "NAME": "active"}]
    )
    assert data == [{"ID": "3", "NAME": "active"}]
    assert body == {}


async def test_activate_invoice_single_ref(settings) -> None:
    data, body = await _invoice_call(
        settings,
        "rsge_activate_invoice",
        "/Invoice/ActivateInvoice",
        {"INVOICE_ID": 918, "SELLER_ACTION": 1},
        918,
    )
    assert body == {"INVOICE": {"ID": 918}}
    assert data == {"INVOICE_ID": 918, "SELLER_ACTION": 1}


async def test_delete_invoice_single_ref(settings) -> None:
    _, body = await _invoice_call(
        settings, "rsge_delete_invoice", "/Invoice/DeleteInvoice", {"SELLER_ACTION": -1}, 913
    )
    assert body == {"INVOICE": {"ID": 913}}


async def test_clear_barcodes_empty_body(settings) -> None:
    _, body = await _invoice_call(settings, "rsge_clear_barcodes", "/Invoice/ClearBarCodes", {})
    assert body == {}


async def test_get_seqnum_body(settings) -> None:
    data, body = await _invoice_call(
        settings, "rsge_get_seqnum", "/Invoice/GetSeqNum", {"SeqNum": "26466366"}, "201901"
    )
    assert body == {"OperationPeriod": "201901"}
    assert data == {"SeqNum": "26466366"}


async def test_create_decl_body(settings) -> None:
    _, body = await _invoice_call(
        settings, "rsge_create_decl", "/Invoice/CreateDecl", {}, [339], "201901"
    )
    assert body == {"Invoices": [{"ID": 339}], "OperationPeriod": "201901"}


@pytest.mark.parametrize(
    "tool,path",
    [
        ("rsge_activate_invoices", "/Invoice/ActivateInvoices"),
        ("rsge_confirm_invoices", "/Invoice/ConfirmInvoices"),
        ("rsge_refuse_invoices", "/Invoice/RefuseInvoices"),
    ],
)
async def test_invoice_batch_ops(settings, tool, path) -> None:
    _, body = await _invoice_call(settings, tool, path, {}, [917, 916])
    assert body == {"Invoices": [{"ID": 917}, {"ID": 916}]}

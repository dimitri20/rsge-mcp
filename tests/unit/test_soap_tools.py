"""Tests for the SOAP tool modules (request shaping + credential gating)."""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers import FakeMCP, make_ctx, soap_diffgram, soap_scalar
from rsge_mcp.errors import RsgeConfigError
from rsge_mcp.models.spec_invoice import SpecInvoice, SpecInvoiceDesc
from rsge_mcp.models.waybill import WaybillGood
from rsge_mcp.soap.services import NTOS, SPECINVOICES, TAXPAYER, WAYBILL
from rsge_mcp.tools.soap import ntos_invoice, spec_invoice, taxpayer, waybill

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


async def test_z_report_details_credentials_and_order(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(TAXPAYER.endpoint).mock(
            return_value=httpx.Response(
                200,
                text=soap_diffgram("Get_Z_Report_Details", "ZreportDetails", [{"ZNumber": "5"}]),
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            taxpayer.register(fake, ctx)
            data = await fake.tools["rsge_get_z_report_details"](
                "2024-01-01T00:00:00", "2024-01-31T00:00:00"
            )
        assert data == [{"ZNumber": "5"}]
        body = _content(route)
        assert "<UserName>itana</UserName>" in body  # bare username, not su:tin
        assert "<Password>123456</Password>" in body
        # WSDL order: UserName, Password, StartDate, EndDate
        assert body.index("<UserName>") < body.index("<Password>") < body.index("<StartDate>")
        assert "<EndDate>2024-01-31T00:00:00</EndDate>" in body


async def test_z_report_sum_scalar(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(TAXPAYER.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("Get_Z_Report_Sum", PaidCash="100", PaidOther="50")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            taxpayer.register(fake, ctx)
            data = await fake.tools["rsge_get_z_report_sum"](
                "2024-01-01T00:00:00", "2024-01-31T00:00:00"
            )
        assert data == {"PaidCash": "100", "PaidOther": "50"}
        assert "<StartDate>2024-01-01T00:00:00</StartDate>" in _content(route)


# --- P3: waybill long-tail ---


@pytest.mark.parametrize(
    "tool,op",
    [
        ("rsge_get_waybill_types", "get_waybill_types"),
        ("rsge_get_waybill_units", "get_waybill_units"),
        ("rsge_get_transport_types", "get_trans_types"),
        ("rsge_get_wood_types", "get_wood_types"),
        ("rsge_get_waybill_error_codes", "get_error_codes"),
        ("rsge_get_car_numbers", "get_car_numbers"),
    ],
)
async def test_waybill_reference_catalogs(soap_settings, tool, op) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_diffgram(op, "ROW", [{"ID": "1"}]))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            data = await fake.tools[tool]()
        assert data == [{"ID": "1"}]
        body = _content(route)
        assert (
            f'<{op} xmlns="http://tempuri.org/"><su>itana:206322102</su><sp>123456</sp></{op}>'
            in body
        )


async def test_get_akciz_codes_search_filter(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_diffgram("get_akciz_codes", "A", [{"CODE": "2207"}])
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_akciz_codes"]("oil")
        assert "<s_text>oil</s_text>" in _content(route)


async def test_get_akciz_codes_omits_unset_filter(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_diffgram("get_akciz_codes", "A", []))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_akciz_codes"]()
        assert "<s_text>" not in _content(route)


async def test_get_bar_codes_filter(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_diffgram("get_bar_codes", "B", []))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_bar_codes"]("999")
        assert "<bar_code>999</bar_code>" in _content(route)


@pytest.mark.parametrize(
    "tool,op",
    [
        ("rsge_confirm_waybill", "confirm_waybill"),
        ("rsge_reject_waybill", "reject_waybill"),
        ("rsge_ref_waybill", "ref_waybill"),
    ],
)
async def test_waybill_lifecycle_single_id(soap_settings, tool, op) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools[tool](42)
        body = _content(route)
        assert "<waybill_id>42</waybill_id>" in body
        assert body.index("<su>") < body.index("<sp>") < body.index("<waybill_id>")


async def test_close_waybill_vd_date_before_id(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("close_waybill_vd", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_close_waybill_vd"](7, "2026-01-01T00:00:00")
        body = _content(route)
        assert "<delivery_date>2026-01-01T00:00:00</delivery_date>" in body
        assert body.index("<delivery_date>") < body.index("<waybill_id>")  # WSDL order


async def test_send_waybill_vd_date_before_id(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("send_waybil_vd", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_send_waybill_vd"](7, "2026-01-01T00:00:00")
        body = _content(route)
        assert "<begin_date>2026-01-01T00:00:00</begin_date>" in body
        assert body.index("<begin_date>") < body.index("<waybill_id>")


async def test_ref_waybill_vd_optional_comment(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("ref_waybill_vd", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_ref_waybill_vd"](7, "wrong address")
        assert "<comment>wrong address</comment>" in _content(route)


@pytest.mark.parametrize(
    "tool,op,arg,tag,val",
    [
        ("rsge_get_name_from_tin", "get_name_from_tin", "123", "tin", "123"),
        ("rsge_is_vat_payer_tin", "is_vat_payer_tin", "123", "tin", "123"),
        ("rsge_get_tin_from_un_id", "get_tin_from_un_id", 7, "un_id", "7"),
        ("rsge_get_payer_type_from_un_id", "get_payer_type_from_un_id", 7, "un_id", "7"),
        ("rsge_is_vat_payer", "is_vat_payer", 7, "un_id", "7"),
    ],
)
async def test_waybill_identity_helpers(soap_settings, tool, op, arg, tag, val) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result=val))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools[tool](arg)
        assert f"<{tag}>{val}</{tag}>" in _content(route)


async def test_get_waybill_by_number(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("get_waybill_by_number", ID="5"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_get_waybill_by_number"]("AA-000123")
        assert "<waybill_number>AA-000123</waybill_number>" in _content(route)


async def test_get_waybill_pdf(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("get_print_pdf", get_print_pdfResult="JVBERi0=")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            data = await fake.tools["rsge_get_waybill_pdf"](7)
        assert data == {"get_print_pdfResult": "JVBERi0="}
        assert "<waybill_id>7</waybill_id>" in _content(route)


async def test_waybill_to_invoice_body(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(WAYBILL.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice", save_invoiceResult="99")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            await fake.tools["rsge_waybill_to_invoice"](7, in_inv_id=3)
        body = _content(route)
        assert "<waybill_id>7</waybill_id>" in body and "<in_inv_id>3</in_inv_id>" in body


# --- P4: ntos long-tail ---


async def test_ntos_save_invoice_a_su_sp_last(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice_a", save_invoice_aResult="500")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_save_invoice_a"](
                invoice_id=1,
                operation_date="2026-01-01T00:00:00",
                seller_un_id=2,
                buyer_un_id=3,
                overhead_dt="2026-01-01T00:00:00",
                b_s_user_id=1,
            )
        body = _content(route)
        assert "<invois_id>1</invois_id>" in body
        assert body.index("<b_s_user_id>") < body.index("<su>") < body.index("<sp>")


async def test_ntos_save_invoice_n_note_after_su_sp(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice_n", save_invoice_nResult="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_save_invoice_n"](
                invoice_id=1,
                operation_date="D",
                seller_un_id=2,
                buyer_un_id=3,
                overhead_dt="D",
                b_s_user_id=1,
                note="hello",
            )
        body = _content(route)
        assert "<note>hello</note>" in body
        assert body.index("<sp>") < body.index("<note>")  # WSDL quirk: note AFTER su/sp


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        (
            "rsge_ntos_correct_invoice",
            "k_invoice",
            (5, 3),
            ["<inv_id>5</inv_id>", "<k_type>3</k_type>"],
        ),
        ("rsge_ntos_cancel_invoice", "g_invoice", (5,), ["<inv_id>5</inv_id>"]),
        (
            "rsge_ntos_accept_invoice_status",
            "acsept_invoice_status",
            (5, 2),
            ["<inv_id>5</inv_id>", "<status>2</status>"],
        ),
        (
            "rsge_ntos_delete_invoice_desc",
            "delete_invoice_desc",
            (5, 9),
            ["<id>9</id>", "<inv_id>5</inv_id>"],
        ),
        (
            "rsge_ntos_accept_invoice_request",
            "acsept_invoice_request_status",
            (7, 4),
            ["<id>7</id>", "<seller_un_id>4</seller_un_id>"],
        ),
        (
            "rsge_ntos_del_invoice_request",
            "del_invoice_request",
            (5, 6),
            ["<inv_id>5</inv_id>", "<bayer_un_id>6</bayer_un_id>"],
        ),
    ],
)
async def test_ntos_simple_writes_su_sp_last(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        assert body.rindex("<su>") < body.rindex("<sp>")  # su then sp, trailing


async def test_ntos_refuse_invoice_status_optional_text(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("ref_invoice_status", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_refuse_invoice_status"](5, ref_text="wrong amount")
        body = _content(route)
        assert "<ref_text>wrong amount</ref_text>" in body
        assert body.index("<ref_text>") < body.index("<su>")  # ref_text before su/sp


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        (
            "rsge_ntos_attach_advance_invoice",
            "attach_advance_invoice",
            (1, 2, 3.0, 4),
            [
                "<invoice_id>1</invoice_id>",
                "<advance_invoice_id>2</advance_invoice_id>",
                "<advance_invoice_drg_amount>3.0</advance_invoice_drg_amount>",
                "<seller_un_id>4</seller_un_id>",
            ],
        ),
        (
            "rsge_ntos_update_advance_invoice",
            "update_advance_invoice",
            (1, 2, 3.0),
            ["<invoice_id>1</invoice_id>", "<advance_invoice_id>2</advance_invoice_id>"],
        ),
        (
            "rsge_ntos_get_attached_advance_invoices",
            "get_attached_advance_invoices",
            (1,),
            ["<invoice_id>1</invoice_id>"],
        ),
    ],
)
async def test_ntos_advance_su_sp_first(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        assert body.index("<su>") < body.index("<sp>") < body.index("<user_id>")  # su/sp FIRST


async def test_ntos_get_attachable_advance_invoices(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_diffgram("get_attachable_advance_invoices", "ADV", [{"ID": "1"}])
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            data = await fake.tools["rsge_ntos_get_attachable_advance_invoices"](
                seller_un_id=4, operation_date="2026-01-01T00:00:00", buyer_tin="123"
            )
        assert data == [{"ID": "1"}]
        body = _content(route)
        assert body.index("<su>") < body.index("<user_id>")  # su/sp FIRST
        assert "<buyer_tin>123</buyer_tin>" in body
        assert body.index("<buyer_tin>") < body.index("<operation_date>")  # WSDL order


async def test_ntos_detach_advance_invoices_xml(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("detach_advance_invoices", Result="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_detach_advance_invoices"](1, [7, 8])
        assert "<advance_invoices><id>7</id><id>8</id></advance_invoices>" in _content(route)


async def test_ntos_detach_advance_invoices_rejects_empty(soap_settings) -> None:
    async with make_ctx(soap_settings) as ctx:
        fake = FakeMCP()
        ntos_invoice.register(fake, ctx)
        with pytest.raises(ValueError):
            await fake.tools["rsge_ntos_detach_advance_invoices"](1, [])


async def test_ntos_save_invoice_request_shape(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("save_invoice_request", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools["rsge_ntos_save_invoice_request"](
                invoice_id=1,
                buyer_un_id=2,
                seller_un_id=3,
                dt="2026-01-01T00:00:00",
                notes="please",
            )
        body = _content(route)
        assert "<bayer_un_id>2</bayer_un_id>" in body  # rs.ge spelling on the wire
        assert "<notes>please</notes>" in body
        assert body.index("<dt>") < body.index("<notes>") < body.index("<su>")  # WSDL order


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        ("rsge_ntos_get_un_id_from_tin", "get_un_id_from_tin", ("123",), ["<tin>123</tin>"]),
        (
            "rsge_ntos_get_un_id_from_user_id",
            "get_un_id_from_user_id",
            (),
            ["<user_id>0</user_id>"],
        ),
        (
            "rsge_ntos_get_org_name_from_un_id",
            "get_org_name_from_un_id",
            (731937,),
            ["<un_id>731937</un_id>"],
        ),
        ("rsge_ntos_get_invoice_desc", "get_invoice_desc", (5,), ["<invois_id>5</invois_id>"]),
        ("rsge_ntos_get_invoice_request", "get_invoice_request", (5,), ["<inv_id>5</inv_id>"]),
        (
            "rsge_ntos_get_invoice_requests",
            "get_invoice_requests",
            (2,),
            ["<bayer_un_id>2</bayer_un_id>"],
        ),
        (
            "rsge_ntos_get_requested_invoices",
            "get_requested_invoices",
            (3,),
            ["<seller_un_id>3</seller_un_id>"],
        ),
    ],
)
async def test_ntos_reads_su_sp_last(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(NTOS.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            ntos_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        assert body.rindex("<su>") < body.rindex("<sp>")  # su/sp present, su before sp


# --- P5: NSAF special (oil/fuel) invoices ---


def _spec_header() -> SpecInvoice:
    return SpecInvoice(
        p_OPERATION_DT="2026-01-01T00:00:00",
        p_SELLER_UN_ID=1,
        p_BUYER_UN_ID=2,
        p_CALC_DATE="2026-01-01T00:00:00",
        p_TR_ST_DATE="2026-01-01T00:00:00",
        p_USER_ID=3,
        p_S_USER_ID=4,
        p_B_S_USER_ID=5,
        p_SSD_DATE="2026-01-01T00:00:00",
        p_SSAF_DATE="2026-01-01T00:00:00",
        p_PAY_TYPE=1,
        p_SSAF_ALT_STATUS=0,
        p_SSD_ALT_STATUS=0,
        p_driver_is_geo=1,
        user_id=9,
        invoiceType=2,
        p_SSD_N="SSD-1",
        p_OIL_ST_ADDRESS="Depot A",
    )


def _spec_desc() -> SpecInvoiceDesc:
    return SpecInvoiceDesc(
        p_g_number=10.0,
        p_un_price=2.5,
        p_drg_amount=4.5,
        p_aqcizi_amount=0.0,
        p_user_id=3,
        p_aqcizi_rate=0.0,
        p_dgg_rate=18.0,
        p_g_number_alt=10.0,
        p_good_id=7,
        p_drg_type=1,
        p_goods="Diesel",
    )


async def test_spec_save_invoice_header_field_order(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice_b_n", save_invoice_b_nResult="500")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools["rsge_spec_save_invoice"](_spec_header())
        body = _content(route)
        # flat sequence (no <waybill> wrapper); optional p_SSD_N sits before p_CALC_DATE per WSDL
        assert "<p_SSD_N>SSD-1</p_SSD_N>" in body
        assert body.index("<p_SSD_N>") < body.index("<p_CALC_DATE>")
        # unset optionals dropped; trailing order ...invoiceType, su, sp
        assert "<p_K_SSAF_N>" not in body
        assert body.index("<invoiceType>") < body.index("<su>") < body.index("<sp>")


async def test_spec_save_line_item_su_sp_mid(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("save_invoice_desc_n", save_invoice_desc_nResult="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools["rsge_spec_save_line_item"](5, _spec_desc(), desc_id=0)
        body = _content(route)
        # WSDL: user_id, id, su, sp, p_inv_id, ...item
        assert body.index("<su>") < body.index("<p_inv_id>") < body.index("<p_goods>")
        assert "<p_good_id>7</p_good_id>" in body


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        (
            "rsge_spec_attach_advance",
            "attach_advance_invoice",
            (1, 2, 3.0, 4),
            ["<seller_un_id>4</seller_un_id>", "<invoice_id>1</invoice_id>"],
        ),
        (
            "rsge_spec_update_advance",
            "update_advance_invoice",
            (1, 2, 3.0),
            ["<invoice_id>1</invoice_id>", "<advance_invoice_id>2</advance_invoice_id>"],
        ),
    ],
)
async def test_spec_advance_su_sp_early(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        # su/sp early: right after user_id, before the business fields
        assert body.index("<user_id>") < body.index("<su>") < body.index("<sp>")
        assert body.index("<sp>") < body.index("<advance_invoice_id>")


async def test_spec_detach_advance_interleaved(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar("detach_advance_invoice", Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools["rsge_spec_detach_advance"](2, 3)
        body = _content(route)
        # WSDL: invoice_id, user_id, su, sp, advance_invoice_id
        assert (
            body.index("<invoice_id>")
            < body.index("<user_id>")
            < body.index("<su>")
            < body.index("<sp>")
            < body.index("<advance_invoice_id>")
        )


async def test_spec_add_ssaf_maps_to_ssd_wire_names(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_scalar("add_spec_invoices_ssaf_n", Result="1")
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools["rsge_spec_add_ssaf"](1, 2, "2026-01-01T00:00:00", ssaf_n="SSAF-9")
        body = _content(route)
        # rs.ge quirk: SSAF number rides the SSD-named wire fields
        assert "<p_ssd_n>SSAF-9</p_ssd_n>" in body
        assert "<p_ssaf_n>" not in body


async def test_spec_get_seller_invoices_dates_required(soap_settings) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(
                200, text=soap_diffgram("get_seller_invoices_n", "INV", [{"ID": "1"}])
            )
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            data = await fake.tools["rsge_spec_get_seller_invoices"](
                un_id=7, s_dt="A", e_dt="B", op_s_dt="C", op_e_dt="D"
            )
        assert data == [{"ID": "1"}]
        body = _content(route)
        for tag in ("s_dt", "e_dt", "op_s_dt", "op_e_dt"):
            assert f"<{tag}>" in body  # required, always sent
        assert body.rindex("<su>") < body.rindex("<sp>")


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        (
            "rsge_spec_delete_line_item",
            "delete_invoice_desc",
            (1, 2),
            ["<id>2</id>", "<inv_id>1</inv_id>"],
        ),
        (
            "rsge_spec_change_status",
            "change_invoice_status_n",
            (1, 2),
            ["<inv_id>1</inv_id>", "<status>2</status>"],
        ),
        (
            "rsge_spec_accept_status",
            "acsept_invoice_status_n",
            (1, 2),
            ["<inv_id>1</inv_id>", "<status>2</status>"],
        ),
        (
            "rsge_spec_correct_invoice",
            "k_invoice_n",
            (1, 11),
            ["<inv_id>1</inv_id>", "<k_type>11</k_type>"],
        ),
        ("rsge_spec_cancel_reason", "gauqmebis_mizezi_n", (1,), ["<p_id>1</p_id>"]),
        (
            "rsge_spec_start_transport",
            "start_transport_new_n",
            (1, "D"),
            ["<p_id>1</p_id>", "<p_tr_date>D</p_tr_date>"],
        ),
        (
            "rsge_spec_correct_transport_mark",
            "correct_transport_mark",
            (1, 2),
            ["<p_id>1</p_id>", "<p_seller_un_id>2</p_seller_un_id>"],
        ),
        (
            "rsge_spec_correct_driver_info",
            "correct_driver_info",
            (1, 2, 1),
            ["<p_driver_is_geo>1</p_driver_is_geo>"],
        ),
        (
            "rsge_spec_delete_ssd",
            "del_spec_invoices_ssd",
            (1, 2, 3),
            ["<p_inv_id>1</p_inv_id>", "<p_id>3</p_id>"],
        ),
        (
            "rsge_spec_delete_ssaf",
            "del_spec_invoices_ssaf",
            (1, 2, 3),
            ["<p_inv_id>1</p_inv_id>", "<p_id>3</p_id>"],
        ),
        (
            "rsge_spec_add_ssd",
            "add_spec_invoices_ssd_n",
            (1, 2, "D"),
            ["<p_inv_id>1</p_inv_id>", "<p_ssd_date>D</p_ssd_date>"],
        ),
        (
            "rsge_spec_save_invoice_request",
            "save_invoice_request",
            (1, 2, 3, "D"),
            ["<bayer_un_id>2</bayer_un_id>", "<dt>D</dt>"],
        ),
    ],
)
async def test_spec_simple_writes(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        assert body.rindex("<su>") < body.rindex("<sp>")


@pytest.mark.parametrize(
    "tool,op,args,checks",
    [
        ("rsge_spec_get_invoice", "get_invoice_n", (1,), ["<invois_id>1</invois_id>"]),
        ("rsge_spec_get_line_items", "get_invoice_desc_n", (1,), ["<invois_id>1</invois_id>"]),
        ("rsge_spec_get_correction", "get_makoreqtirebeli", (1,), ["<inv_id>1</inv_id>"]),
        (
            "rsge_spec_get_attached_advances",
            "get_attached_advance_invoices",
            (1,),
            ["<invoice_id>1</invoice_id>"],
        ),
        (
            "rsge_spec_get_attachable_advances",
            "get_attachable_advance_invs",
            ("D", 4),
            ["<operation_dt>D</operation_dt>", "<seller_un_id>4</seller_un_id>"],
        ),
        (
            "rsge_spec_get_ssds",
            "get_spec_ssds_n",
            (1, 2),
            ["<p_un_id>2</p_un_id>", "<p_inv_id>1</p_inv_id>"],
        ),
        (
            "rsge_spec_get_ssafs",
            "get_spec_ssafs_n",
            (1, 2),
            ["<p_un_id>2</p_un_id>", "<p_inv_id>1</p_inv_id>"],
        ),
        ("rsge_spec_get_products", "get_spec_products_n", (7,), ["<p_un_id>7</p_un_id>"]),
        (
            "rsge_spec_get_product",
            "get_spec_product_by_id",
            (5, 7),
            ["<p_id>5</p_id>", "<p_un_id>7</p_un_id>"],
        ),
        (
            "rsge_spec_get_org_objects",
            "get_v_org_objects_by_un_id_n",
            (7, 2),
            ["<p_un_id>7</p_un_id>", "<invoiceType>2</invoiceType>"],
        ),
        ("rsge_spec_get_my_org_objects", "get_rs_org_objects", (), ["<user_id>0</user_id>"]),
        ("rsge_spec_print_invoice", "print_invoices", (1,), ["<inv_id>1</inv_id>"]),
        ("rsge_spec_check_users", "check_spec_users", (), ["<user_id>0</user_id>"]),
    ],
)
async def test_spec_reads(soap_settings, tool, op, args, checks) -> None:
    with respx.mock as router:
        route = router.post(SPECINVOICES.endpoint).mock(
            return_value=httpx.Response(200, text=soap_scalar(op, Result="1"))
        )
        async with make_ctx(soap_settings) as ctx:
            fake = FakeMCP()
            spec_invoice.register(fake, ctx)
            await fake.tools[tool](*args)
        body = _content(route)
        for c in checks:
            assert c in body
        assert body.rindex("<su>") < body.rindex("<sp>")


async def test_spec_save_invoice_requires_soap_credentials(settings) -> None:
    async with make_ctx(settings) as ctx:  # no SOAP creds
        fake = FakeMCP()
        spec_invoice.register(fake, ctx)
        with pytest.raises(RsgeConfigError):
            await fake.tools["rsge_spec_save_invoice"](_spec_header())

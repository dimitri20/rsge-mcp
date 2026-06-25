"""Tests for server construction and the CLI entry point."""

from __future__ import annotations

import pytest

from rsge_mcp.config import load_settings
from rsge_mcp.server import build_server

pytestmark = pytest.mark.unit

EXPECTED_TOOLS = {
    "rsge_get_org_info_by_tin",
    "rsge_get_vat_payer_status",
    "rsge_get_units",
    "rsge_get_transaction_result",
    "rsge_get_invoice",
    "rsge_list_invoices",
    "rsge_save_invoice",
    "rsge_confirm_invoice",
    "rsge_refuse_invoice",
    "rsge_cancel_invoice",
    # Invoice lifecycle/reference (P1)
    "rsge_list_excise",
    "rsge_list_barcodes",
    "rsge_get_barcode",
    "rsge_list_goods",
    "rsge_get_actions",
    "rsge_activate_invoice",
    "rsge_activate_invoices",
    "rsge_delete_invoice",
    "rsge_confirm_invoices",
    "rsge_refuse_invoices",
    "rsge_clear_barcodes",
    "rsge_get_seqnum",
    "rsge_create_decl",
    # Employees + Customs (P2)
    "rsge_get_countries",
    "rsge_get_employee",
    "rsge_list_employees",
    "rsge_save_employee",
    "rsge_get_customs_declarations",
    "rsge_taxpayer_public_info",
    "rsge_signout",
    # SOAP (Phase 2)
    "rsge_waybill_check_service_user",
    "rsge_get_waybill",
    "rsge_get_waybills",
    "rsge_save_waybill",
    "rsge_send_waybill",
    "rsge_close_waybill",
    "rsge_del_waybill",
    # Waybill long-tail (P3)
    "rsge_get_waybill_types",
    "rsge_get_waybill_units",
    "rsge_get_transport_types",
    "rsge_get_wood_types",
    "rsge_get_akciz_codes",
    "rsge_get_waybill_error_codes",
    "rsge_get_bar_codes",
    "rsge_get_car_numbers",
    "rsge_confirm_waybill",
    "rsge_reject_waybill",
    "rsge_ref_waybill",
    "rsge_close_waybill_vd",
    "rsge_send_waybill_vd",
    "rsge_ref_waybill_vd",
    "rsge_get_name_from_tin",
    "rsge_get_tin_from_un_id",
    "rsge_get_payer_type_from_un_id",
    "rsge_is_vat_payer",
    "rsge_is_vat_payer_tin",
    "rsge_get_waybill_by_number",
    "rsge_get_waybill_pdf",
    "rsge_waybill_to_invoice",
    "rsge_ntos_check_service_user",
    "rsge_ntos_get_invoice",
    "rsge_ntos_get_seller_invoices",
    "rsge_ntos_get_buyer_invoices",
    "rsge_ntos_save_invoice",
    "rsge_ntos_save_invoice_desc",
    "rsge_ntos_change_invoice_status",
    "rsge_get_z_report_details",
    "rsge_get_z_report_sum",
}


@pytest.mark.asyncio
async def test_build_server_registers_all_tools() -> None:
    mcp = build_server(load_settings({"RSGE_ENV": "test"}))
    names = {t.name for t in await mcp.list_tools()}
    assert names == EXPECTED_TOOLS


@pytest.mark.asyncio
async def test_submit_pin_only_in_tool_mode() -> None:
    mcp = build_server(load_settings({"RSGE_ENV": "test", "RSGE_2FA_MODE": "tool"}))
    names = {t.name for t in await mcp.list_tools()}
    assert "rsge_submit_pin" in names


@pytest.mark.asyncio
async def test_build_server_without_credentials_still_builds() -> None:
    # prod + no creds: exercises the no-credentials warning branch.
    mcp = build_server(load_settings({"RSGE_ENV": "prod"}))
    assert await mcp.list_tools()


def test_main_invokes_run(monkeypatch) -> None:
    import rsge_mcp.__main__ as entry

    ran = {}

    class Dummy:
        def run(self) -> None:
            ran["called"] = True

    monkeypatch.setattr(entry, "build_server", lambda: Dummy())
    entry.main()
    assert ran["called"]

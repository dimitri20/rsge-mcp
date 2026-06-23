"""Opt-in LIVE SOAP write verification against services-test.rs.ge.

Double-gated: requires RSGE_RUN_INTEGRATION=1 AND RSGE_ALLOW_WRITES=1. Strictly
draft-only: chek_service_user (read-only) to find a working service user, then
save_waybill (STATUS=0 draft) -> get_waybill -> del_waybill. It NEVER calls
send_waybill/close_waybill (those activate a legally binding tax document).

Status (verified 2026-06-23): services-test.rs.ge serves the WSDL but its WayBillService
backend currently returns a server fault ("Could not load ... Oracle.DataAccess"), so no
service-user validates and this test self-skips. It is ready to run once rs.ge's test host
is functional and a valid service user is available (set RSGE_SOAP_USER/TIN/PASSWORD).
"""

from __future__ import annotations

import os

import pytest

from helpers import FakeMCP, make_ctx
from rsge_mcp.config import Settings, load_settings
from rsge_mcp.errors import RsgeError
from rsge_mcp.models.waybill import WaybillGood
from rsge_mcp.tools.soap import waybill

pytestmark = pytest.mark.integration

_RUN = os.environ.get("RSGE_RUN_INTEGRATION") == "1"
_ALLOW_WRITES = os.environ.get("RSGE_ALLOW_WRITES") == "1"
_skip = pytest.mark.skipif(
    not (_RUN and _ALLOW_WRITES),
    reason="set RSGE_RUN_INTEGRATION=1 and RSGE_ALLOW_WRITES=1 to run live SOAP write tests",
)

_TEST_HOST = "https://services-test.rs.ge"

# Documented public test service-user candidates (su = user:tin, sp=123456). If real
# creds are supplied via env, they take precedence and are tried first.
_CANDIDATES = [
    ("itana", "206322102"),
    ("itgigi", "206322102"),
    ("programmer", "12345678910"),
    ("satesto2", "12345678910"),
    ("tbilisi", "206322102"),
]


def _settings_for(user: str, tin: str, password: str = "123456") -> Settings:
    return load_settings(
        {
            "RSGE_ENV": "test",
            "RSGE_SOAP_BASE": _TEST_HOST,
            "RSGE_SOAP_USER": user,
            "RSGE_SOAP_TIN": tin,
            "RSGE_SOAP_PASSWORD": password,
        }
    )


def _candidates() -> list[tuple[str, str, str]]:
    env_user = os.environ.get("RSGE_SOAP_USER")
    env_tin = os.environ.get("RSGE_SOAP_TIN")
    env_pw = os.environ.get("RSGE_SOAP_PASSWORD", "123456")
    picks = [(u, t, "123456") for u, t in _CANDIDATES]
    if env_user and env_tin:
        picks.insert(0, (env_user, env_tin, env_pw))
    return picks


async def _discover_service_user() -> tuple[Settings | None, int, str]:
    """Return (settings, un_id, '') for the first validating candidate, else (None, -1, reason)."""
    reason = "no candidates tried"
    for user, tin, pw in _candidates():
        settings = _settings_for(user, tin, pw)
        async with make_ctx(settings) as ctx:
            fake = FakeMCP()
            waybill.register(fake, ctx)
            try:
                res = await fake.tools["rsge_waybill_check_service_user"]()
            except RsgeError as exc:
                reason = f"{user}:{tin} -> {exc}"
                continue
        ok = str(res.get("chek_service_userResult", "")).lower() == "true"
        un_id_raw = str(res.get("un_id", "")).strip()
        un_id = int(un_id_raw) if un_id_raw.lstrip("-").isdigit() else -1
        if ok and un_id >= 0:
            return settings, un_id, ""
        reason = (
            f"{user}:{tin} -> invalid (result={res.get('chek_service_userResult')}, un_id={un_id})"
        )
    return None, -1, reason


def _extract_save(parsed: object) -> tuple[int, int]:
    """Extract (status, waybill_id) from a save_waybill response, tolerant of nesting."""
    node = parsed.get("save_waybillResult", parsed) if isinstance(parsed, dict) else {}
    result = node.get("RESULT", node) if isinstance(node, dict) else {}
    return int(result["STATUS"]), int(result["ID"])


@_skip
@pytest.mark.asyncio
async def test_waybill_draft_roundtrip_and_delete_live() -> None:
    settings, un_id, reason = await _discover_service_user()
    if settings is None:
        pytest.skip(f"no service-user validated on services-test.rs.ge ({reason})")

    async with make_ctx(settings) as ctx:
        fake = FakeMCP()
        waybill.register(fake, ctx)
        waybill_id = None
        try:
            saved = await fake.tools["rsge_save_waybill"](
                waybill_type=2,
                buyer_tin="12345678910",
                seller_un_id=un_id,
                start_address="Tbilisi, test start",
                end_address="Tbilisi, test end",
                goods=[
                    WaybillGood(
                        W_NAME="Test widget",
                        UNIT_ID=1,
                        UNIT_TXT="cnt",
                        QUANTITY=1,
                        PRICE=1.0,
                        AMOUNT=1.0,
                        VAT_TYPE=0,
                    )
                ],
                buyer_name="Test Buyer",
                chek_buyer_tin=1,
                begin_date="2026-06-23T10:00:00",
                full_amount=1.0,
                trans_id=2,
                tran_cost_payer=1,
            )
            status, waybill_id = _extract_save(saved)
            assert status == 0, f"draft rejected: {saved}"
            assert waybill_id > 0

            got = await fake.tools["rsge_get_waybill"](waybill_id)
            wb = got["WAYBILL"]
            assert int(wb["STATUS"]) == 0  # still a draft
            assert not str(wb.get("WAYBILL_NUMBER") or "").strip()  # no number until activated
        finally:
            # Clean up in finally so a failed assertion still deletes the draft.
            if waybill_id:
                res = await fake.tools["rsge_del_waybill"](waybill_id)
                assert int(res["del_waybillResult"]) == 1, f"cleanup failed: {res}"
    # send_waybill / close_waybill are intentionally NEVER called (they create a binding doc).

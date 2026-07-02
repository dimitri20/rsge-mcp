"""Production-hardening regression tests (review findings, iteration 2).

Covers: SOAP parse robustness (unrecognized 200s, non-XML 500s, entity hardening),
structural write-no-retry, Retry-After capping, token-TTL fallback, RSGE_SOAP_BASE host
scoping, version single-sourcing, and clean startup config errors.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers import env
from rsge_mcp.errors import RsgeHttpError
from rsge_mcp.rest.auth import EapiSession
from rsge_mcp.rest.client import RestClient
from rsge_mcp.rest.rate_limit import RateLimiter
from rsge_mcp.soap.client import _apply_soap_base
from rsge_mcp.soap.parse import parse

pytestmark = pytest.mark.unit

AUTH = "https://eapi.rs.ge/Users/Authenticate"
TARGET = "https://eapi.rs.ge/Org/GetOrgInfoByTin"


# --- SOAP parse robustness ---


def test_parse_raises_on_non_soap_xml() -> None:
    # A well-formed XHTML maintenance page served with HTTP 200 must NOT become None.
    xhtml = "<html><body><h1>Maintenance</h1></body></html>"
    with pytest.raises(RsgeHttpError, match="no get_waybillResponse or SOAP Body"):
        parse(xhtml, "get_waybill")


def test_parse_non_xml_carries_status_code() -> None:
    with pytest.raises(RsgeHttpError) as exc_info:
        parse("<<< not xml at all", "get_waybill", status_code=500)
    assert exc_info.value.status_code == 500
    assert "HTTP 500" in str(exc_info.value)


def test_parse_does_not_expand_doctype_entities() -> None:
    # resolve_entities=False: a DOCTYPE-declared entity must never expand into the data.
    evil = (
        '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "boom">]>'
        "<r><get_waybillResponse><v>&x;</v></get_waybillResponse></r>"
    )
    result = parse(evil, "get_waybill")
    assert "boom" not in str(result)


# --- REST client: structural write-no-retry + Retry-After cap ---


async def _noop_sleep(_: float) -> None:
    return None


def _client(settings, http, sleep=_noop_sleep):
    session = EapiSession(settings, http, RateLimiter(0.0))
    return RestClient(settings, http, session, RateLimiter(0.0), sleep=sleep)


def _token_route(router) -> None:
    router.post(AUTH).mock(
        return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
    )


@pytest.mark.asyncio
async def test_write_never_retried_even_if_caller_allows(settings) -> None:
    # write=True + (erroneous) retry_reads=True: a retryable 502 must NOT be retried.
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(return_value=httpx.Response(502))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError):
                await _client(settings, http).post(
                    "/Org/GetOrgInfoByTin", {}, write=True, retry_reads=True
                )
        assert target.call_count == 1  # exactly one attempt — no write is ever replayed


@pytest.mark.asyncio
async def test_retry_after_is_capped(settings) -> None:
    sleeps: list[float] = []

    async def record_sleep(s: float) -> None:
        sleeps.append(s)

    with respx.mock as router:
        _token_route(router)
        router.post(TARGET).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "900"}),
                httpx.Response(200, json=env({"ok": 1})),
            ]
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http, sleep=record_sleep).post(
                "/Org/GetOrgInfoByTin", {}
            )
        assert data == {"ok": 1}
        assert sleeps and max(sleeps) <= 30.0  # 900s header honored only up to the cap


# --- auth: degenerate EXPIRES_IN must not disable the token cache ---


@pytest.mark.asyncio
async def test_token_cached_despite_zero_expires_in(settings) -> None:
    with respx.mock as router:
        auth_route = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 0}))
        )
        async with httpx.AsyncClient() as http:
            s = EapiSession(settings, http, RateLimiter(0.0))
            assert await s.get_token() == "T"
            assert await s.get_token() == "T"  # served from cache (fallback TTL)
        assert auth_route.call_count == 1


# --- RSGE_SOAP_BASE only rewrites services.rs.ge-hosted endpoints ---


@pytest.mark.parametrize(
    "endpoint,expected",
    [
        (
            "https://services.rs.ge/WayBillService/WayBillService.asmx",
            "https://services-test.rs.ge/WayBillService/WayBillService.asmx",
        ),
        (  # ntos lives on revenue.mof.ge — no counterpart on the test host
            "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
            "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
        ),
        (  # webserv.rs.ge (spec/dutyfree) — untouched as well
            "https://webserv.rs.ge/dutyfree/wsdutyfree.asmx",
            "https://webserv.rs.ge/dutyfree/wsdutyfree.asmx",
        ),
    ],
)
def test_apply_soap_base_scoped_to_services_host(endpoint, expected) -> None:
    assert _apply_soap_base(endpoint, "https://services-test.rs.ge") == expected


# --- version single-sourcing + startup error handling ---


def test_version_single_sourced() -> None:
    import importlib.metadata

    import rsge_mcp

    assert rsge_mcp.__version__ == importlib.metadata.version("rsge-mcp")


def test_main_reports_config_error_cleanly(monkeypatch, capsys) -> None:
    import rsge_mcp.__main__ as entry
    from rsge_mcp.errors import RsgeConfigError

    def boom() -> None:
        raise RsgeConfigError("RSGE_ENV must be 'test' or 'prod', got 'bogus'")

    monkeypatch.setattr(entry, "build_server", boom)
    with pytest.raises(SystemExit) as exc_info:
        entry.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "configuration error" in err and "Traceback" not in err

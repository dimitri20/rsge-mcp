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


# --- second-round review fixes ---


@pytest.mark.asyncio
async def test_soap_base_ignored_warns_per_service(soap_settings, caplog) -> None:
    import dataclasses
    import logging as _logging

    import rsge_mcp.soap.client as soap_client_mod
    from rsge_mcp.soap.services import DUTYFREE

    cfg = dataclasses.replace(
        soap_settings,
        hosts=dataclasses.replace(soap_settings.hosts, soap_base="services-test.rs.ge"),
    )
    soap_client_mod._soap_base_warned.clear()
    with respx.mock as router:
        router.post(DUTYFREE.endpoint).mock(  # NOT rewritten: goes to production endpoint
            return_value=httpx.Response(
                200,
                text='<e xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
                "<soap:Body><get_unitsResponse><r>1</r></get_unitsResponse></soap:Body></e>",
            )
        )
        async with httpx.AsyncClient() as http:
            from rsge_mcp.rest.rate_limit import RateLimiter
            from rsge_mcp.soap.client import SoapClient

            sc = SoapClient(cfg, http, RateLimiter(0.0))
            with caplog.at_level(_logging.WARNING, logger="rsge_mcp.soap.client"):
                await sc.call(DUTYFREE, "get_units", {"userName": "u", "password": "p"})
                await sc.call(DUTYFREE, "get_units", {"userName": "u", "password": "p"})
    warnings = [r for r in caplog.records if "PRODUCTION" in r.getMessage()]
    assert len(warnings) == 1  # loud, but once per service


def test_rsge_dotenv_missing_file_raises(monkeypatch, tmp_path) -> None:
    from rsge_mcp.config import load_env_file
    from rsge_mcp.errors import RsgeConfigError

    monkeypatch.setenv("RSGE_DOTENV", str(tmp_path / "nope.env"))
    with pytest.raises(RsgeConfigError, match="does not point to a readable file"):
        load_env_file()


def test_rsge_dotenv_empty_file_is_fine(monkeypatch, tmp_path) -> None:
    from rsge_mcp.config import load_env_file

    empty = tmp_path / "placeholder.env"
    empty.write_text("# all values come from the MCP client env block\n")
    monkeypatch.setenv("RSGE_DOTENV", str(empty))
    load_env_file()  # must not raise


def test_dotenv_discovery_does_not_walk_up(monkeypatch, tmp_path) -> None:
    from rsge_mcp.config import load_env_file

    (tmp_path / ".env").write_text("RSGE_SENTINEL_PARENT=1\n")
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.delenv("RSGE_DOTENV", raising=False)
    monkeypatch.delenv("RSGE_SENTINEL_PARENT", raising=False)
    monkeypatch.chdir(child)
    load_env_file()
    import os

    assert "RSGE_SENTINEL_PARENT" not in os.environ  # parent .env NOT silently adopted


def test_build_server_loads_env_before_logging(monkeypatch) -> None:
    import rsge_mcp.server as server_mod

    order: list[str] = []
    monkeypatch.setattr(server_mod, "load_env_file", lambda: order.append("env"))
    monkeypatch.setattr(server_mod, "setup_logging", lambda: order.append("logging"))
    server_mod.build_server()  # uses real load_settings with ambient env (test default)
    assert order[:2] == ["env", "logging"]  # RSGE_LOG_LEVEL from .env must be visible

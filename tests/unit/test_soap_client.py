"""Tests for the SOAP client (request build, headers, response handling)."""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers import soap_diffgram, soap_fault
from rsge_mcp.errors import RsgeError, RsgeHttpError, RsgeTimeoutError
from rsge_mcp.rest.rate_limit import RateLimiter
from rsge_mcp.soap.client import SoapClient
from rsge_mcp.soap.services import WAYBILL

# asyncio_mode=auto runs the async tests; the module mixes one sync test, so don't
# blanket-mark the module asyncio.
pytestmark = pytest.mark.unit

ENDPOINT = WAYBILL.endpoint


def _client(settings, http):
    return SoapClient(settings, http, RateLimiter(0.0))


def test_build_request_wraps_envelope(settings) -> None:
    req = _client(settings, None).build_request(WAYBILL, "get_waybill", {"waybill_id": 5})
    assert req.startswith('<?xml version="1.0" encoding="utf-8"?><soap:Envelope')
    assert (
        '<get_waybill xmlns="http://tempuri.org/"><waybill_id>5</waybill_id></get_waybill>' in req
    )


async def test_call_parses_diffgram_and_sets_headers(settings) -> None:
    with respx.mock as router:
        route = router.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200, text=soap_diffgram("get_waybills", "WAYBILL", [{"ID": "1"}])
            )
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http).call(
                WAYBILL, "get_waybills", {"su": "u", "sp": "p"}
            )
        assert data == [{"ID": "1"}]
        req = route.calls.last.request
        assert req.headers["soapaction"] == '"http://tempuri.org/get_waybills"'
        assert req.headers["content-type"].startswith("text/xml")
        assert b"<get_waybills" in req.content


async def test_call_fault_500_raises(settings) -> None:
    with respx.mock as router:
        router.post(ENDPOINT).mock(return_value=httpx.Response(500, text=soap_fault("nope")))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeError, match="nope"):
                await _client(settings, http).call(
                    WAYBILL, "chek_service_user", {"su": "u", "sp": "p"}
                )


async def test_call_unexpected_status_raises(settings) -> None:
    with respx.mock as router:
        router.post(ENDPOINT).mock(return_value=httpx.Response(404, text="not found"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError):
                await _client(settings, http).call(WAYBILL, "get_waybill", {"su": "u", "sp": "p"})


async def test_call_timeout_maps(settings) -> None:
    with respx.mock as router:
        router.post(ENDPOINT).mock(side_effect=httpx.ConnectTimeout("slow"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeTimeoutError):
                await _client(settings, http).call(WAYBILL, "get_waybill", {"su": "u", "sp": "p"})

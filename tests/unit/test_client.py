"""Tests for the REST client: auth header, -104 re-auth, retry policy."""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers import env
from rsge_mcp.errors import RsgeAuthError, RsgeHttpError, RsgeTimeoutError
from rsge_mcp.rest.auth import EapiSession
from rsge_mcp.rest.client import RestClient
from rsge_mcp.rest.rate_limit import RateLimiter

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

AUTH = "https://eapi.rs.ge/Users/Authenticate"
TARGET = "https://eapi.rs.ge/Org/GetOrgInfoByTin"


async def _noop_sleep(_: float) -> None:
    return None


def _client(settings, http):
    session = EapiSession(settings, http, RateLimiter(0.0))
    return RestClient(settings, http, session, RateLimiter(0.0), sleep=_noop_sleep)


def _token_route(router) -> None:
    router.post(AUTH).mock(
        return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
    )


async def test_sends_bearer_header_and_unwraps(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(
            return_value=httpx.Response(200, json=env({"Name": "ACME"}))
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http).post("/Org/GetOrgInfoByTin", {"Tin": "1"})
        assert data == {"Name": "ACME"}
        assert target.calls.last.request.headers["authorization"] == "bearer T"


async def test_reauth_once_on_invalid_token(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(
            side_effect=[
                httpx.Response(200, json=env(None, sid=-104, text="bad token")),
                httpx.Response(200, json=env({"Name": "ACME"})),
            ]
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http).post("/Org/GetOrgInfoByTin", {"Tin": "1"})
        assert data == {"Name": "ACME"}
        assert target.call_count == 2


async def test_second_invalid_token_raises(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(
            return_value=httpx.Response(200, json=env(None, sid=-104, text="bad token"))
        )
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeAuthError):
                await _client(settings, http).post("/Org/GetOrgInfoByTin", {"Tin": "1"})
        assert target.call_count == 2  # original + one re-auth retry


async def test_read_retried_on_503(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json=env({"ok": True})),
            ]
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http).post("/Org/GetOrgInfoByTin", {"Tin": "1"})
        assert data == {"ok": True}
        assert target.call_count == 2


async def test_read_retried_on_429(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(
            side_effect=[httpx.Response(429), httpx.Response(200, json=env({"ok": True}))]
        )
        async with httpx.AsyncClient() as http:
            data = await _client(settings, http).post("/Org/GetOrgInfoByTin", {"Tin": "1"})
        assert data == {"ok": True}
        assert target.call_count == 2


async def test_retry_after_honored(settings) -> None:
    slept: list[float] = []

    async def rec(delay: float) -> None:
        slept.append(delay)

    with respx.mock as router:
        _token_route(router)
        router.post(TARGET).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "5"}),
                httpx.Response(200, json=env({"ok": True})),
            ]
        )
        async with httpx.AsyncClient() as http:
            session = EapiSession(settings, http, RateLimiter(0.0))
            client = RestClient(settings, http, session, RateLimiter(0.0), sleep=rec)
            await client.post("/Org/GetOrgInfoByTin", {"Tin": "1"})
    assert max(slept) >= 5.0  # backoff honored the Retry-After


async def test_write_not_retried_on_503(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        target = router.post(TARGET).mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError):
                await _client(settings, http).post(
                    "/Org/GetOrgInfoByTin", {"Tin": "1"}, retry_reads=False
                )
        assert target.call_count == 1


async def test_timeout_maps_to_rsge_timeout(settings) -> None:
    with respx.mock as router:
        _token_route(router)
        router.post(TARGET).mock(side_effect=httpx.ConnectTimeout("slow"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeTimeoutError):
                await _client(settings, http).post(
                    "/Org/GetOrgInfoByTin", {"Tin": "1"}, retry_reads=False
                )

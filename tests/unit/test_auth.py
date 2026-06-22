"""Tests for the eAPI bearer-token session."""

from __future__ import annotations

import asyncio
import dataclasses

import httpx
import pytest
import respx

from helpers import env
from rsge_mcp.config import TwoFactorMode
from rsge_mcp.errors import RsgeAuthError, RsgeConfigError, RsgeEnvelopeError, RsgePinRequiredError
from rsge_mcp.rest.auth import EapiSession
from rsge_mcp.rest.rate_limit import RateLimiter

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

AUTH = "https://eapi.rs.ge/Users/Authenticate"
PIN = "https://eapi.rs.ge/Users/AuthenticatePin"


class Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def _session(settings, http, clock=None):
    return EapiSession(settings, http, RateLimiter(0.0), clock=clock or Clock())


async def test_login_caches_token(settings) -> None:
    with respx.mock as router:
        route = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(settings, http)
            assert await s.get_token() == "T"
            assert await s.get_token() == "T"  # cached, no second call
        assert route.call_count == 1


async def test_token_refreshes_after_expiry(settings) -> None:
    clock = Clock()
    with respx.mock as router:
        route = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(settings, http, clock)
            await s.get_token()
            clock.t += 5000  # advance past expiry (2400 - 120 skew)
            await s.get_token()
        assert route.call_count == 2


async def test_concurrent_get_token_logs_in_once(settings) -> None:
    with respx.mock as router:
        route = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(settings, http)
            results = await asyncio.gather(*[s.get_token() for _ in range(5)])
        assert results == ["T"] * 5
        assert route.call_count == 1


async def test_missing_credentials_raises_config_error(settings) -> None:
    s_no_creds = dataclasses.replace(settings, eapi_username=None, eapi_password=None)
    async with httpx.AsyncClient() as http:
        s = _session(s_no_creds, http)
        with pytest.raises(RsgeConfigError):
            await s.get_token()


async def test_auth_failure_status_raises(settings) -> None:
    with respx.mock as router:
        router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env(None, sid=-1, text="system error"))
        )
        async with httpx.AsyncClient() as http:
            s = _session(settings, http)
            with pytest.raises(RsgeEnvelopeError):
                await s.get_token()


async def test_auth_without_token_or_pin_raises(settings) -> None:
    with respx.mock as router:
        router.post(AUTH).mock(return_value=httpx.Response(200, json=env({})))
        async with httpx.AsyncClient() as http:
            s = _session(settings, http)
            with pytest.raises(RsgeAuthError):
                await s.get_token()


async def test_static_pin_mode_completes_login(settings) -> None:
    cfg = dataclasses.replace(settings, two_factor_mode=TwoFactorMode.STATIC_PIN, pin="0000")
    with respx.mock as router:
        router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"PIN_TOKEN": "P", "MASKED_MOBILE": "*16"}))
        )
        pin_route = router.post(PIN).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T2", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(cfg, http)
            assert await s.get_token() == "T2"
        assert pin_route.called
        import json

        assert json.loads(pin_route.calls.last.request.content) == {"PIN_TOKEN": "P", "PIN": "0000"}


async def test_tool_mode_defers_then_submit_pin(settings) -> None:
    cfg = dataclasses.replace(settings, two_factor_mode=TwoFactorMode.TOOL)
    with respx.mock as router:
        router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"PIN_TOKEN": "P", "MASKED_MOBILE": "*16"}))
        )
        router.post(PIN).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T3", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(cfg, http)
            with pytest.raises(RsgePinRequiredError) as exc:
                await s.get_token()
            assert exc.value.pin_token == "P"
            assert await s.submit_pin("1234") == "T3"
            assert await s.get_token() == "T3"  # now cached


async def test_submit_pin_without_pending_raises(settings) -> None:
    async with httpx.AsyncClient() as http:
        s = _session(settings, http)
        with pytest.raises(RsgeAuthError):
            await s.submit_pin("1234")


async def test_invalidate_forces_relogin(settings) -> None:
    with respx.mock as router:
        route = router.post(AUTH).mock(
            return_value=httpx.Response(200, json=env({"ACCESS_TOKEN": "T", "EXPIRES_IN": 2400}))
        )
        async with httpx.AsyncClient() as http:
            s = _session(settings, http)
            await s.get_token()
            s.invalidate()
            assert not s.has_token
            await s.get_token()
        assert route.call_count == 2

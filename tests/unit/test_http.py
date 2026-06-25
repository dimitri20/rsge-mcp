"""Tests for the low-level HTTP helper's error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from rsge_mcp.errors import RsgeHttpError, RsgeTimeoutError
from rsge_mcp.rest._http import post_json

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

URL = "https://x.rs.ge/a"


async def test_timeout_maps() -> None:
    with respx.mock as router:
        router.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeTimeoutError):
                await post_json(http, URL, {}, {}, 1.0)


async def test_connect_error_maps_to_http_error() -> None:
    with respx.mock as router:
        router.post(URL).mock(side_effect=httpx.ConnectError("no route"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError):
                await post_json(http, URL, {}, {}, 1.0)


async def test_non_200_carries_status_code() -> None:
    with respx.mock as router:
        router.post(URL).mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError) as exc:
                await post_json(http, URL, {}, {}, 1.0)
        assert exc.value.status_code == 500


async def test_non_json_body_raises() -> None:
    with respx.mock as router:
        router.post(URL).mock(return_value=httpx.Response(200, content=b"<html></html>"))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError):
                await post_json(http, URL, {}, {}, 1.0)


async def test_method_get_with_body() -> None:
    with respx.mock as router:
        route = router.get(URL).mock(
            return_value=httpx.Response(200, json={"DATA": [], "STATUS": {"ID": 0}})
        )
        async with httpx.AsyncClient() as http:
            data = await post_json(http, URL, {"x": 1}, {}, 1.0, method="GET")
        assert data == {"DATA": [], "STATUS": {"ID": 0}}
        req = route.calls.last.request
        assert req.method == "GET"
        assert req.content  # body was sent with the GET


async def test_retry_after_parsed_on_429() -> None:
    with respx.mock as router:
        router.post(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "7"}))
        async with httpx.AsyncClient() as http:
            with pytest.raises(RsgeHttpError) as exc:
                await post_json(http, URL, {}, {}, 1.0)
        assert exc.value.status_code == 429
        assert exc.value.retry_after == 7.0

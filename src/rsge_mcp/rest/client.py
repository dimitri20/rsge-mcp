"""RestClient: the spine of the REST layer.

Every eAPI tool funnels through ``post()``. It applies the rate gate and bearer header,
sends the request, unwraps the ``{DATA, STATUS}`` envelope, and:
- transparently re-authenticates **once** on an invalid-token (``-104``) envelope, then
  replays the request (safe: the server rejected it pre-processing, so no state changed);
- retries idempotent **reads** on timeouts / 502-504, but **never retries writes**
  (duplicate waybills/invoices have legal consequences) — callers pass ``retry_reads``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ..config import Settings
from ..errors import INVALID_TOKEN, RsgeAuthError, RsgeHttpError, RsgeTimeoutError
from ..logging import get_logger
from ._http import JSON_HEADERS, post_json
from .auth import EapiSession
from .envelope import unwrap
from .rate_limit import RateLimiter

log = get_logger("client")

MAX_READ_RETRIES = 2
RETRYABLE_STATUS = frozenset({502, 503, 504})
_BACKOFFS = (0.5, 1.5)


class RestClient:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient,
        session: EapiSession,
        rate_limiter: RateLimiter,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._http = http
        self._session = session
        self._rate = rate_limiter
        self._sleep = sleep

    async def post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        auth: bool = True,
        retry_reads: bool = True,
        base: str | None = None,
    ) -> Any:
        """POST to ``path`` and return the unwrapped ``DATA``."""
        try:
            return await self._attempt(path, body, auth=auth, retry_reads=retry_reads, base=base)
        except RsgeAuthError as exc:
            if auth and exc.status_id == INVALID_TOKEN:
                log.info("invalid token (-104); re-authenticating and retrying once")
                self._session.invalidate()
                return await self._attempt(
                    path, body, auth=auth, retry_reads=retry_reads, base=base
                )
            raise

    async def _attempt(
        self,
        path: str,
        body: dict[str, Any] | None,
        *,
        auth: bool,
        retry_reads: bool,
        base: str | None,
    ) -> Any:
        headers = dict(JSON_HEADERS)
        if auth:
            headers["Authorization"] = f"bearer {await self._session.get_token()}"
        url = (base or self._settings.hosts.eapi_base) + path
        raw = await self._send(url, body or {}, headers, retry_reads)
        return unwrap(raw)

    async def _send(
        self, url: str, body: dict[str, Any], headers: dict[str, str], retry_reads: bool
    ) -> Any:
        attempts = 1 + (MAX_READ_RETRIES if retry_reads else 0)
        last: Exception | None = None
        for i in range(attempts):
            await self._rate.acquire()
            try:
                return await post_json(self._http, url, body, headers, self._settings.http_timeout)
            except RsgeTimeoutError as exc:
                last = exc
            except RsgeHttpError as exc:
                if not (retry_reads and exc.status_code in RETRYABLE_STATUS):
                    raise
                last = exc
            if i < attempts - 1:
                await self._sleep(_BACKOFFS[min(i, len(_BACKOFFS) - 1)])
        assert last is not None
        raise last

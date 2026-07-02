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
from ..errors import (
    INVALID_TOKEN,
    RsgeAuthError,
    RsgeHttpError,
    RsgeTimeoutError,
    RsgeWriteBlockedError,
)
from ..logging import get_logger
from ._http import JSON_HEADERS, post_json
from .auth import EapiSession
from .envelope import unwrap
from .rate_limit import RateLimiter

log = get_logger("client")

MAX_READ_RETRIES = 2
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
_BACKOFFS = (0.5, 1.5)
# Honor a 429 Retry-After only up to this many seconds; a hostile/huge header must not
# hang the tool call for minutes.
RETRY_AFTER_CAP = 30.0


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
        write: bool = False,
        method: str = "POST",
    ) -> Any:
        """Send a JSON request to ``path`` and return the unwrapped ``DATA``.

        Pass ``write=True`` for mutating calls; they are refused unless writes are
        enabled (``RSGE_ALLOW_WRITES``). ``method`` allows GET-with-body (customs).
        """
        if write and not self._settings.allow_writes:
            raise RsgeWriteBlockedError(
                f"refusing to call {path}: server is read-only — "
                "set RSGE_ALLOW_WRITES=1 to enable writes"
            )
        # Structural guarantee, not convention: a write is NEVER retried, regardless of
        # what the caller passed for retry_reads (duplicate submissions have legal weight).
        retry_reads = retry_reads and not write
        try:
            return await self._attempt(
                path, body, auth=auth, retry_reads=retry_reads, base=base, method=method
            )
        except RsgeAuthError as exc:
            if auth and exc.status_id == INVALID_TOKEN:
                log.info("invalid token (-104); re-authenticating and retrying once")
                self._session.invalidate()
                return await self._attempt(
                    path, body, auth=auth, retry_reads=retry_reads, base=base, method=method
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
        method: str,
    ) -> Any:
        headers = dict(JSON_HEADERS)
        if auth:
            headers["Authorization"] = f"bearer {await self._session.get_token()}"
        url = (base or self._settings.hosts.eapi_base) + path
        raw = await self._send(url, body or {}, headers, retry_reads, method)
        return unwrap(raw)

    async def _send(
        self,
        url: str,
        body: dict[str, Any],
        headers: dict[str, str],
        retry_reads: bool,
        method: str = "POST",
    ) -> Any:
        attempts = 1 + (MAX_READ_RETRIES if retry_reads else 0)
        last: Exception | None = None
        for i in range(attempts):
            await self._rate.acquire()
            log.debug("%s %s (attempt %d/%d)", method, url, i + 1, attempts)
            try:
                return await post_json(
                    self._http, url, body, headers, self._settings.http_timeout, method
                )
            except RsgeTimeoutError as exc:
                log.debug("%s %s timed out (attempt %d/%d)", method, url, i + 1, attempts)
                last = exc
            except RsgeHttpError as exc:
                if not (retry_reads and exc.status_code in RETRYABLE_STATUS):
                    raise
                log.debug("%s %s -> HTTP %s; will retry", method, url, exc.status_code)
                last = exc
            if i < attempts - 1:
                delay = _BACKOFFS[min(i, len(_BACKOFFS) - 1)]
                if isinstance(last, RsgeHttpError) and last.retry_after:
                    # Honor a 429 Retry-After, but capped — never hang for minutes.
                    delay = max(delay, min(last.retry_after, RETRY_AFTER_CAP))
                await self._sleep(delay)
        assert last is not None
        raise last

"""eAPI bearer-token session: lazy login, token cache, 2FA PIN handling.

The server process serves one set of credentials, so a single long-lived session holds
the token in memory. Login is lazy (first tool that needs auth triggers it). The token
is cached until ``EXPIRES_IN`` minus a safety skew; an ``asyncio.Lock`` prevents a
login stampede when several tools fire at once.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import httpx

from ..config import Settings, TwoFactorMode
from ..errors import RsgeAuthError, RsgeConfigError, RsgePinRequiredError
from ..logging import get_logger
from ._http import JSON_HEADERS, post_json
from .envelope import unwrap
from .rate_limit import RateLimiter

log = get_logger("auth")

EXPIRY_SKEW_SECONDS = 120.0


class EapiSession:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._http = http
        self._rate = rate_limiter
        self._clock = clock
        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._expires_at = 0.0
        self._pin_token: str | None = None

    @property
    def _base(self) -> str:
        return self._settings.hosts.eapi_base

    @property
    def has_token(self) -> bool:
        return self._token is not None

    def invalidate(self) -> None:
        """Drop the cached token so the next ``get_token`` re-authenticates."""
        self._token = None
        self._expires_at = 0.0

    async def get_token(self) -> str:
        """Return a valid bearer token, logging in (once) if needed."""
        if self._token is not None and self._clock() < self._expires_at:
            return self._token
        async with self._lock:
            if self._token is not None and self._clock() < self._expires_at:
                return self._token
            return await self._login()

    async def submit_pin(self, pin: str) -> str:
        """Complete a pending two-factor login with the SMS ``pin`` (tool mode)."""
        async with self._lock:
            if not self._pin_token:
                raise RsgeAuthError(0, "no PIN is pending; trigger a login first")
            data = await self._post("/Users/AuthenticatePin", self._pin_body(self._pin_token, pin))
            token = self._store_token(data)
            if token is None:
                raise RsgeAuthError(0, "PIN authentication did not return a token")
            return token

    # -- internals --------------------------------------------------------------

    async def _login(self) -> str:
        if not self._settings.has_eapi_creds:
            raise RsgeConfigError("eAPI credentials are not configured")
        body: dict[str, Any] = {
            "USERNAME": self._settings.eapi_username,
            "PASSWORD": self._settings.eapi_password,
        }
        if self._settings.eapi_device_code:
            body["DEVICE_CODE"] = self._settings.eapi_device_code
        data = await self._post("/Users/Authenticate", body)
        return await self._complete(data)

    async def _complete(self, data: Any) -> str:
        token = self._store_token(data)
        if token is not None:
            return token

        pin_token = _get(data, "PIN_TOKEN")
        if not pin_token:
            raise RsgeAuthError(0, "authentication returned neither ACCESS_TOKEN nor PIN_TOKEN")

        if self._settings.two_factor_mode is TwoFactorMode.STATIC_PIN:
            data2 = await self._post(
                "/Users/AuthenticatePin", self._pin_body(pin_token, self._settings.pin)
            )
            token = self._store_token(data2)
            if token is None:
                raise RsgeAuthError(0, "PIN authentication did not return a token")
            return token

        # tool mode (or no PIN configured): defer to a human via submit_pin.
        self._pin_token = pin_token
        raise RsgePinRequiredError(pin_token, _get(data, "MASKED_MOBILE"))

    def _pin_body(self, pin_token: str, pin: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {"PIN_TOKEN": pin_token, "PIN": pin}
        if self._settings.eapi_device_code:
            body["DEVICE_CODE"] = self._settings.eapi_device_code
        return body

    def _store_token(self, data: Any) -> str | None:
        token = _get(data, "ACCESS_TOKEN")
        if not token:
            return None
        self._token = str(token)
        expires = float(_get(data, "EXPIRES_IN") or 0)
        self._expires_at = self._clock() + max(0.0, expires - EXPIRY_SKEW_SECONDS)
        self._pin_token = None
        return self._token

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        await self._rate.acquire()
        raw = await post_json(
            self._http, self._base + path, body, dict(JSON_HEADERS), self._settings.http_timeout
        )
        return unwrap(raw)


def _get(data: Any, key: str) -> Any:
    return data.get(key) if isinstance(data, dict) else None

"""SoapClient: render a SOAP 1.1 request, POST it, and parse the response.

Shares the REST layer's rate gate (CLAUDE.md courtesy delay). SOAP faults arrive as
HTTP 500 with a fault body, so 500 is passed to ``parse`` which surfaces the faultstring.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from ..errors import RsgeHttpError, RsgeTimeoutError
from ..logging import get_logger
from ..rest.rate_limit import RateLimiter
from .build import operation_element
from .parse import parse
from .services import SoapService

log = get_logger("soap.client")

_ENVELOPE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    "<soap:Body>{body}</soap:Body>"
    "</soap:Envelope>"
)


class SoapClient:
    def __init__(
        self, settings: Settings, http: httpx.AsyncClient, rate_limiter: RateLimiter
    ) -> None:
        self._settings = settings
        self._http = http
        self._rate = rate_limiter

    def build_request(self, service: SoapService, operation: str, params: dict[str, Any]) -> str:
        """Build the full SOAP envelope string for an operation (exposed for tests)."""
        body = operation_element(service.namespace, operation, params)
        return _ENVELOPE.format(body=body)

    async def call(self, service: SoapService, operation: str, params: dict[str, Any]) -> Any:
        """Render, POST, and parse a SOAP operation."""
        envelope = self.build_request(service, operation, params)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{service.namespace}{operation}"',
        }
        await self._rate.acquire()
        try:
            resp = await self._http.post(
                service.endpoint,
                content=envelope.encode("utf-8"),
                headers=headers,
                timeout=self._settings.http_timeout,
            )
        except httpx.TimeoutException as exc:
            raise RsgeTimeoutError(f"SOAP {operation} timed out") from exc
        except httpx.HTTPError as exc:
            raise RsgeHttpError(f"SOAP {operation} failed: {exc}") from exc

        # SOAP faults come back as HTTP 500; let parse() surface the faultstring.
        if resp.status_code not in (200, 500):
            raise RsgeHttpError(
                f"SOAP {operation} returned HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        return parse(resp.text, operation)

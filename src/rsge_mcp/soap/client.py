"""SoapClient: render a SOAP 1.1 request, POST it, and parse the response.

Shares the REST layer's rate gate (CLAUDE.md courtesy delay). SOAP faults arrive as
HTTP 500 with a fault body, so 500 is passed to ``parse`` which surfaces the faultstring.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from ..config import Settings
from ..errors import RsgeHttpError, RsgeTimeoutError, RsgeWriteBlockedError
from ..logging import get_logger
from ..rest.rate_limit import RateLimiter
from .build import operation_element
from .parse import parse
from .services import SoapService

log = get_logger("soap.client")


# RSGE_SOAP_BASE only makes sense for services hosted on services.rs.ge — the test host
# (services-test.rs.ge) mirrors that host's paths. ntos (www.revenue.mof.ge) and the
# webserv.rs.ge services have no equivalent there; rewriting them would 404.
_OVERRIDABLE_HOSTS = frozenset({"services.rs.ge"})

# Services already warned about an ignored RSGE_SOAP_BASE (warn once per service, not per
# call). An operator who set the override must not believe "everything points at test"
# while ntos/spec/dutyfree traffic silently goes to PRODUCTION.
_soap_base_warned: set[str] = set()


def _apply_soap_base(endpoint: str, soap_base: str | None) -> str:
    """Rewrite the scheme+netloc of ``endpoint`` to ``soap_base``, keeping path/query.

    Lets ``RSGE_SOAP_BASE`` point SOAP calls at a test host (e.g. services-test.rs.ge)
    while preserving each service's own ``.asmx`` path. Only applies to endpoints whose
    production host is ``services.rs.ge`` (waybill/taxpayer/custompost) — the other SOAP
    hosts have no counterpart on the test host and are left untouched. ``soap_base`` may
    be a bare host, a scheme+host, or carry a trailing slash — only scheme+netloc are used.
    """
    if not soap_base:
        return endpoint
    ep = urlsplit(endpoint)
    if ep.netloc not in _OVERRIDABLE_HOSTS:
        return endpoint
    base = urlsplit(soap_base if "//" in soap_base else f"//{soap_base}")
    # A bare host (no scheme) lands in base.path, not base.netloc.
    return urlunsplit(
        (base.scheme or ep.scheme, base.netloc or base.path, ep.path, ep.query, ep.fragment)
    )


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

    async def call(
        self, service: SoapService, operation: str, params: dict[str, Any], *, write: bool = False
    ) -> Any:
        """Render, POST, and parse a SOAP operation.

        Pass ``write=True`` for mutating operations; they are refused unless writes are
        enabled (``RSGE_ALLOW_WRITES``).
        """
        if write and not self._settings.allow_writes:
            raise RsgeWriteBlockedError(
                f"refusing SOAP {operation}: server is read-only — "
                "set RSGE_ALLOW_WRITES=1 to enable writes"
            )
        envelope = self.build_request(service, operation, params)
        # SOAPAction = targetNamespace + operation joined with exactly one "/": tempuri and
        # DutyFreeService/ end in a slash; services.rs.ge does not (its WSDL actions are
        # "services.rs.ge/Op"). The body xmlns uses the namespace verbatim.
        ns = service.namespace
        action = f"{ns}{operation}" if ns.endswith("/") else f"{ns}/{operation}"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{action}"',
        }
        target = _apply_soap_base(service.endpoint, self._settings.hosts.soap_base)
        if (
            self._settings.hosts.soap_base
            and target == service.endpoint
            and service.name not in _soap_base_warned
        ):
            _soap_base_warned.add(service.name)
            log.warning(
                "RSGE_SOAP_BASE is set but does NOT apply to %s (%s has no counterpart "
                "on the test host) — its calls go to PRODUCTION",
                service.name,
                urlsplit(service.endpoint).netloc,
            )
        await self._rate.acquire()
        log.debug("SOAP %s -> %s", operation, target)
        try:
            resp = await self._http.post(
                target,
                content=envelope.encode("utf-8"),
                headers=headers,
                timeout=self._settings.http_timeout,
            )
        except httpx.TimeoutException as exc:
            raise RsgeTimeoutError(f"SOAP {operation} timed out") from exc
        except httpx.HTTPError as exc:
            raise RsgeHttpError(f"SOAP {operation} failed: {exc}") from exc

        log.debug("SOAP %s <- HTTP %d (%d bytes)", operation, resp.status_code, len(resp.text))
        # SOAP faults come back as HTTP 500; let parse() surface the faultstring.
        if resp.status_code not in (200, 500):
            raise RsgeHttpError(
                f"SOAP {operation} returned HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        return parse(resp.text, operation, status_code=resp.status_code)

"""Application context: the wired-up clients tools depend on."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import Settings
from .rest.auth import EapiSession
from .rest.client import RestClient
from .rest.rate_limit import RateLimiter
from .soap.client import SoapClient


@dataclass
class AppContext:
    settings: Settings
    http: httpx.AsyncClient
    session: EapiSession
    rest: RestClient
    soap: SoapClient


def build_context(settings: Settings) -> AppContext:
    """Construct the shared HTTP client, rate limiter, session, and transport clients."""
    http = httpx.AsyncClient()
    rate = RateLimiter(settings.rate_delay_ms / 1000.0)  # shared by REST + SOAP
    session = EapiSession(settings, http, rate)
    rest = RestClient(settings, http, session, rate)
    soap = SoapClient(settings, http, rate)
    return AppContext(settings=settings, http=http, session=session, rest=rest, soap=soap)

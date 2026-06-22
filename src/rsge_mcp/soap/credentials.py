"""SOAP service-user credentials.

The legacy services authenticate by carrying ``su`` and ``sp`` in *every* request body
(there is no token). ``su`` is ``"{user}:{TIN}"`` (e.g. ``itana:206322102``); ``sp`` is
the password.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..errors import RsgeConfigError


@dataclass(frozen=True)
class ServiceUser:
    user: str
    tin: str
    password: str

    @property
    def su(self) -> str:
        return f"{self.user}:{self.tin}"

    @property
    def sp(self) -> str:
        return self.password


def service_user_or_raise(settings: Settings) -> ServiceUser:
    """Return the configured service user, or raise a clear config error."""
    if not (settings.soap_user and settings.soap_tin and settings.soap_password):
        raise RsgeConfigError(
            "SOAP service-user credentials are not configured "
            "(set RSGE_SOAP_USER, RSGE_SOAP_TIN, RSGE_SOAP_PASSWORD)."
        )
    return ServiceUser(settings.soap_user, settings.soap_tin, settings.soap_password)

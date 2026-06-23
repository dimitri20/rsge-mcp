"""Configuration: load and validate settings from the environment / ``.env``.

``RSGE_ENV`` selects behavior:
- ``test`` (default): if no eAPI credentials are supplied, fall back to the documented
  public test account (safe, no real data, 2FA off).
- ``prod``: credentials are required; a test identity is never silently injected.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv

from .errors import RsgeConfigError

# Public, documented test credentials (2FA-off). Injected ONLY when RSGE_ENV=test and
# no real credentials are provided. See docs/text/*eAPI* and the Postman collections.
TEST_EAPI_USERNAME = "Tbilisi"
TEST_EAPI_PASSWORD = "123456"

DEFAULT_EAPI_BASE = "https://eapi.rs.ge"
DEFAULT_XDATA_BASE = "https://xdata.rs.ge"


class TwoFactorMode(StrEnum):
    OFF = "off"
    STATIC_PIN = "static_pin"
    TOOL = "tool"


@dataclass(frozen=True)
class Hosts:
    """Base URLs, overridable to point at the rs.ge test hosts.

    The live test hosts are ``services-test.rs.ge`` (SOAP) and ``xdata-test.rs.ge`` (REST).
    ``soap_base`` is optional because SOAP endpoints are full URLs in ``soap/services.py``;
    ``None`` means "use the production endpoint as-is".
    """

    eapi_base: str = DEFAULT_EAPI_BASE
    xdata_base: str = DEFAULT_XDATA_BASE
    soap_base: str | None = None


@dataclass(frozen=True)
class Settings:
    env: str
    hosts: Hosts
    eapi_username: str | None
    eapi_password: str | None
    eapi_device_code: str | None
    two_factor_mode: TwoFactorMode
    pin: str | None
    soap_user: str | None
    soap_tin: str | None
    soap_password: str | None
    http_timeout: float
    rate_delay_ms: int
    allow_writes: bool = False

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @property
    def has_eapi_creds(self) -> bool:
        return bool(self.eapi_username and self.eapi_password)

    @property
    def has_soap_creds(self) -> bool:
        return bool(self.soap_user and self.soap_tin and self.soap_password)


def _clean(value: str | None) -> str | None:
    """Normalize an env value: strip, treat empty as unset."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _flag(value: str | None) -> bool:
    """Parse a boolean env flag: '1'/'true'/'yes'/'on' (case-insensitive) -> True."""
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _parse_float(raw: str, name: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise RsgeConfigError(f"{name} must be a number, got {raw!r}") from exc


def _parse_int(raw: str, name: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise RsgeConfigError(f"{name} must be an integer, got {raw!r}") from exc


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Build a validated ``Settings`` from environment variables."""
    if environ is None:
        load_dotenv()
        import os

        environ = os.environ

    env = (environ.get("RSGE_ENV") or "test").strip().lower()
    if env not in ("test", "prod"):
        raise RsgeConfigError(f"RSGE_ENV must be 'test' or 'prod', got {env!r}")

    tfm_raw = (environ.get("RSGE_2FA_MODE") or "off").strip().lower()
    try:
        two_factor_mode = TwoFactorMode(tfm_raw)
    except ValueError as exc:
        valid = ", ".join(m.value for m in TwoFactorMode)
        raise RsgeConfigError(f"RSGE_2FA_MODE must be one of: {valid}") from exc

    username = _clean(environ.get("RSGE_EAPI_USERNAME"))
    password = _clean(environ.get("RSGE_EAPI_PASSWORD"))
    if env == "test" and not username and not password:
        username, password = TEST_EAPI_USERNAME, TEST_EAPI_PASSWORD

    pin = _clean(environ.get("RSGE_PIN"))
    if two_factor_mode is TwoFactorMode.STATIC_PIN and not pin:
        raise RsgeConfigError("RSGE_2FA_MODE=static_pin requires RSGE_PIN to be set")

    soap_base = _clean(environ.get("RSGE_SOAP_BASE"))
    hosts = Hosts(
        eapi_base=(environ.get("RSGE_EAPI_BASE") or DEFAULT_EAPI_BASE).rstrip("/"),
        xdata_base=(environ.get("RSGE_XDATA_BASE") or DEFAULT_XDATA_BASE).rstrip("/"),
        soap_base=soap_base.rstrip("/") if soap_base else None,
    )

    http_timeout = _parse_float(environ.get("RSGE_HTTP_TIMEOUT") or "30", "RSGE_HTTP_TIMEOUT")
    rate_delay_ms = _parse_int(environ.get("RSGE_RATE_DELAY_MS") or "300", "RSGE_RATE_DELAY_MS")

    return Settings(
        env=env,
        hosts=hosts,
        eapi_username=username,
        eapi_password=password,
        eapi_device_code=_clean(environ.get("RSGE_EAPI_DEVICE_CODE")),
        two_factor_mode=two_factor_mode,
        pin=pin,
        soap_user=_clean(environ.get("RSGE_SOAP_USER")),
        soap_tin=_clean(environ.get("RSGE_SOAP_TIN")),
        soap_password=_clean(environ.get("RSGE_SOAP_PASSWORD")),
        http_timeout=http_timeout,
        rate_delay_ms=rate_delay_ms,
        allow_writes=_flag(environ.get("RSGE_ALLOW_WRITES")),
    )

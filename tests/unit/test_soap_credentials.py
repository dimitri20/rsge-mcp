"""Tests for SOAP service-user credentials."""

from __future__ import annotations

import pytest

from rsge_mcp.errors import RsgeConfigError
from rsge_mcp.soap.credentials import ServiceUser, service_user_or_raise

pytestmark = pytest.mark.unit


def test_su_sp_format() -> None:
    user = ServiceUser("itana", "206322102", "pw")
    assert user.su == "itana:206322102"
    assert user.sp == "pw"


def test_raises_without_credentials(settings) -> None:
    with pytest.raises(RsgeConfigError):
        service_user_or_raise(settings)


def test_returns_with_credentials(soap_settings) -> None:
    user = service_user_or_raise(soap_settings)
    assert user.su == "itana:206322102"
    assert user.sp == "123456"

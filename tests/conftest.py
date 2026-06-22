"""Pytest fixtures."""

from __future__ import annotations

import pytest

from rsge_mcp.config import Hosts, Settings, TwoFactorMode


@pytest.fixture
def settings() -> Settings:
    """Test settings: known creds, 2FA off, no rate delay (fast tests)."""
    return Settings(
        env="test",
        hosts=Hosts(eapi_base="https://eapi.rs.ge", xdata_base="https://xdata.rs.ge"),
        eapi_username="user",
        eapi_password="pass",
        eapi_device_code=None,
        two_factor_mode=TwoFactorMode.OFF,
        pin=None,
        soap_user=None,
        soap_tin=None,
        soap_password=None,
        http_timeout=5.0,
        rate_delay_ms=0,
    )

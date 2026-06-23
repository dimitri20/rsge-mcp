"""Tests for config loading and validation."""

from __future__ import annotations

import pytest

from rsge_mcp.config import (
    TEST_EAPI_PASSWORD,
    TEST_EAPI_USERNAME,
    TwoFactorMode,
    load_settings,
)
from rsge_mcp.errors import RsgeConfigError

pytestmark = pytest.mark.unit


def test_test_env_injects_public_credentials() -> None:
    s = load_settings({"RSGE_ENV": "test"})
    assert s.is_test
    assert s.eapi_username == TEST_EAPI_USERNAME
    assert s.eapi_password == TEST_EAPI_PASSWORD
    assert s.has_eapi_creds


def test_explicit_credentials_override_test_defaults() -> None:
    s = load_settings(
        {"RSGE_ENV": "test", "RSGE_EAPI_USERNAME": "me", "RSGE_EAPI_PASSWORD": "secret"}
    )
    assert s.eapi_username == "me"
    assert s.eapi_password == "secret"


def test_prod_never_injects_test_credentials() -> None:
    s = load_settings({"RSGE_ENV": "prod"})
    assert not s.has_eapi_creds
    assert s.eapi_username is None


def test_invalid_env_raises() -> None:
    with pytest.raises(RsgeConfigError):
        load_settings({"RSGE_ENV": "staging"})


def test_static_pin_requires_pin() -> None:
    with pytest.raises(RsgeConfigError):
        load_settings({"RSGE_ENV": "test", "RSGE_2FA_MODE": "static_pin"})


def test_static_pin_with_pin_ok() -> None:
    s = load_settings({"RSGE_ENV": "test", "RSGE_2FA_MODE": "static_pin", "RSGE_PIN": "1234"})
    assert s.two_factor_mode is TwoFactorMode.STATIC_PIN
    assert s.pin == "1234"


def test_invalid_2fa_mode_raises() -> None:
    with pytest.raises(RsgeConfigError):
        load_settings({"RSGE_ENV": "test", "RSGE_2FA_MODE": "nonsense"})


def test_host_overrides_and_trailing_slash_stripped() -> None:
    s = load_settings(
        {
            "RSGE_ENV": "test",
            "RSGE_EAPI_BASE": "https://eapi.example/",
            "RSGE_XDATA_BASE": "https://xdata-test.rs.ge/",
        }
    )
    assert s.hosts.eapi_base == "https://eapi.example"
    assert s.hosts.xdata_base == "https://xdata-test.rs.ge"


def test_soap_base_override_strips_trailing_slash() -> None:
    s = load_settings({"RSGE_ENV": "test", "RSGE_SOAP_BASE": "https://services-test.rs.ge/"})
    assert s.hosts.soap_base == "https://services-test.rs.ge"


def test_soap_base_defaults_to_none() -> None:
    assert load_settings({"RSGE_ENV": "test"}).hosts.soap_base is None


def test_soap_base_blank_is_none() -> None:
    assert load_settings({"RSGE_ENV": "test", "RSGE_SOAP_BASE": "  "}).hosts.soap_base is None


def test_bad_number_raises() -> None:
    with pytest.raises(RsgeConfigError):
        load_settings({"RSGE_ENV": "test", "RSGE_HTTP_TIMEOUT": "abc"})


def test_soap_creds_detected() -> None:
    s = load_settings(
        {
            "RSGE_ENV": "test",
            "RSGE_SOAP_USER": "u",
            "RSGE_SOAP_TIN": "123",
            "RSGE_SOAP_PASSWORD": "p",
        }
    )
    assert s.has_soap_creds

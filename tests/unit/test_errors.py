"""Tests for the error hierarchy and STATUS.ID mapping."""

from __future__ import annotations

import pytest

from rsge_mcp.errors import (
    RsgeAuthError,
    RsgeEnvelopeError,
    RsgeHttpError,
    RsgePinRequiredError,
    error_for,
)

pytestmark = pytest.mark.unit


def test_error_for_invalid_token_is_auth() -> None:
    err = error_for(-104, "bad token")
    assert isinstance(err, RsgeAuthError)
    assert err.gloss == "invalid token"


def test_error_for_generic_is_envelope() -> None:
    err = error_for(-30, "data error")
    assert isinstance(err, RsgeEnvelopeError)
    assert not isinstance(err, RsgeAuthError)
    assert "data error" in str(err)


def test_error_for_unknown_code_has_no_gloss() -> None:
    err = error_for(-999, "mystery")
    assert err.gloss is None
    assert err.status_id == -999


def test_http_error_carries_status_code() -> None:
    err = RsgeHttpError("boom", status_code=503)
    assert err.status_code == 503


def test_pin_required_carries_token() -> None:
    err = RsgePinRequiredError("ptok", masked_mobile="*16")
    assert err.pin_token == "ptok"
    assert "*16" in str(err)

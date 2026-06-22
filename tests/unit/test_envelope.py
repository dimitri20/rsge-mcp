"""Tests for envelope unwrapping."""

from __future__ import annotations

import pytest

from rsge_mcp.errors import RsgeAuthError, RsgeEnvelopeError
from rsge_mcp.rest.envelope import unwrap

pytestmark = pytest.mark.unit


def test_success_returns_data() -> None:
    assert unwrap({"DATA": {"x": 1}, "STATUS": {"ID": 0, "TEXT": "ok"}}) == {"x": 1}


def test_string_status_id_zero() -> None:
    assert unwrap({"DATA": 5, "STATUS": {"ID": "0"}}) == 5


def test_error_status_raises_with_text() -> None:
    with pytest.raises(RsgeEnvelopeError) as exc:
        unwrap({"STATUS": {"ID": -30, "TEXT": "შეცდომა"}})
    assert exc.value.status_id == -30
    assert exc.value.status_text == "შეცდომა"


def test_invalid_token_raises_auth_error() -> None:
    with pytest.raises(RsgeAuthError) as exc:
        unwrap({"STATUS": {"ID": -104, "TEXT": "bad"}})
    assert exc.value.status_id == -104


def test_bare_list_passthrough() -> None:
    assert unwrap([{"a": 1}]) == [{"a": 1}]


def test_no_envelope_passthrough() -> None:
    assert unwrap({"foo": "bar"}) == {"foo": "bar"}


def test_case_insensitive_fallback() -> None:
    assert unwrap({"Data": 9, "Status": {"Id": 0}}) == 9


def test_success_without_data_returns_none() -> None:
    assert unwrap({"STATUS": {"ID": 0}}) is None

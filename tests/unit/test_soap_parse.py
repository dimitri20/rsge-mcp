"""Tests for SOAP response parsing."""

from __future__ import annotations

import pytest

from helpers import soap_diffgram, soap_fault, soap_scalar
from rsge_mcp.errors import RsgeError, RsgeHttpError
from rsge_mcp.soap.parse import parse

pytestmark = pytest.mark.unit


def test_scalar_response_to_dict() -> None:
    xml = soap_scalar("chek_service_user", chek_service_userResult="true", un_id="731937")
    assert parse(xml, "chek_service_user") == {
        "chek_service_userResult": "true",
        "un_id": "731937",
    }


def test_diffgram_to_rows() -> None:
    xml = soap_diffgram(
        "get_waybills", "WAYBILL", [{"ID": "10", "STATUS": "1"}, {"ID": "11", "STATUS": "2"}]
    )
    assert parse(xml, "get_waybills") == [
        {"ID": "10", "STATUS": "1"},
        {"ID": "11", "STATUS": "2"},
    ]


def test_empty_diffgram_is_empty_list() -> None:
    assert parse(soap_diffgram("get_waybills", "WAYBILL", []), "get_waybills") == []


def test_fault_raises_rsge_error() -> None:
    with pytest.raises(RsgeError, match="auth failed"):
        parse(soap_fault("auth failed"), "chek_service_user")


def test_invalid_xml_raises_http_error() -> None:
    with pytest.raises(RsgeHttpError):
        parse("<not valid", "op")


def test_nested_and_repeated_elements() -> None:
    xml = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
        '<get_waybillResponse xmlns="http://tempuri.org/"><WAYBILL><ID>5</ID>'
        "<GOODS_LIST><GOODS><W_NAME>A</W_NAME></GOODS><GOODS><W_NAME>B</W_NAME></GOODS>"
        "</GOODS_LIST></WAYBILL></get_waybillResponse></soap:Body></soap:Envelope>"
    )
    assert parse(xml, "get_waybill") == {
        "WAYBILL": {"ID": "5", "GOODS_LIST": {"GOODS": [{"W_NAME": "A"}, {"W_NAME": "B"}]}}
    }

"""Parse SOAP/ASMX responses with lxml.

ASMX services answer in one of two shapes:
- a DataSet wrapped in a ``<diffgr:diffgram>`` (e.g. ``get_waybills``) -> list of row dicts;
- scalar / out-parameter elements directly under the response (e.g. ``chek_service_user``)
  -> a dict of those values.

SOAP faults (HTTP 500) carry a ``<faultstring>`` which we raise as ``RsgeError``.
"""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..errors import RsgeError, RsgeHttpError
from ..logging import get_logger

log = get_logger("soap.parse")

DIFFGRAM = "diffgram"


def parse(xml_text: str, operation: str) -> Any:
    """Parse a SOAP response body for ``operation`` into Python data."""
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise RsgeHttpError(f"SOAP response was not valid XML: {exc}") from exc

    _raise_on_fault(root)

    response = _find_local(root, f"{operation}Response")
    if response is None:
        response = _soap_body_child(root)
    if response is None:
        return None

    diffgram = _find_local(response, DIFFGRAM)
    if diffgram is not None:
        return _diffgram_rows(diffgram)
    return _element_to_obj(response)


def _local(el: Any) -> str:
    return str(etree.QName(el).localname)


def _is_element(el: Any) -> bool:
    return isinstance(el.tag, str)


def _find_local(root: Any, localname: str) -> Any:
    for el in root.iter():
        if _is_element(el) and _local(el) == localname:
            return el
    return None


def _soap_body_child(root: Any) -> Any:
    body = _find_local(root, "Body")
    if body is None:
        return None
    children = [c for c in body if _is_element(c)]
    return children[0] if children else None


def _raise_on_fault(root: Any) -> None:
    fault = _find_local(root, "Fault")
    if fault is None:
        return
    detail = _find_local(fault, "faultstring")
    message = (detail.text if detail is not None else None) or "(no faultstring)"
    raise RsgeError(f"SOAP fault: {message}")


def _diffgram_rows(diffgram: Any) -> list[Any]:
    rows = []
    for dataset in diffgram:
        if not _is_element(dataset):
            continue
        for row in dataset:
            if _is_element(row):
                rows.append(_element_to_obj(row))
    return rows


def _element_to_obj(el: Any) -> Any:
    children = [c for c in el if _is_element(c)]
    if not children:
        return (el.text or "").strip() or None
    result: dict[str, Any] = {}
    for child in children:
        key = _local(child)
        value = _element_to_obj(child)
        if key in result:
            existing = result[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[key] = [existing, value]
        else:
            result[key] = value
    return result

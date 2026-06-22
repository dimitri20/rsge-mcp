"""Tests for the SOAP XML builder."""

from __future__ import annotations

import pytest

from rsge_mcp.soap.build import operation_element, to_xml

pytestmark = pytest.mark.unit


def test_scalar_is_escaped() -> None:
    assert to_xml("a", "x & <y>") == "<a>x &amp; &lt;y&gt;</a>"


def test_none_is_self_closing() -> None:
    assert to_xml("a", None) == "<a/>"


def test_bool_renders_lowercase() -> None:
    assert to_xml("a", True) == "<a>true</a>"
    assert to_xml("a", False) == "<a>false</a>"


def test_nested_dict_preserves_order() -> None:
    assert to_xml("p", {"a": 1, "b": 2}) == "<p><a>1</a><b>2</b></p>"


def test_list_repeats_tag() -> None:
    assert to_xml("g", [{"x": 1}, {"x": 2}]) == "<g><x>1</x></g><g><x>2</x></g>"


def test_operation_element_has_namespace_and_order() -> None:
    out = operation_element("http://tempuri.org/", "op", {"su": "u", "sp": "p"})
    assert out == '<op xmlns="http://tempuri.org/"><su>u</su><sp>p</sp></op>'

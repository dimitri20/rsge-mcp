"""Build request XML programmatically from ordered Python structures.

Hand-written (not zeep): we control element order and nesting exactly, which the picky
ASMX services require — especially for the deeply nested ``save_waybill`` payload
(``WAYBILL -> GOODS_LIST -> GOODS[]``). String values are XML-escaped.
"""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape


def to_xml(tag: str, value: Any) -> str:
    """Serialize ``value`` as ``<tag>...</tag>``.

    - dict -> nested child elements, in insertion order;
    - list -> the same ``tag`` repeated once per item;
    - None -> a self-closing ``<tag/>``;
    - bool -> ``true``/``false``; everything else -> ``str(value)`` (escaped).
    """
    if isinstance(value, dict):
        inner = "".join(to_xml(key, child) for key, child in value.items())
        return f"<{tag}>{inner}</{tag}>"
    if isinstance(value, list):
        return "".join(to_xml(tag, item) for item in value)
    if value is None:
        return f"<{tag}/>"
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return f"<{tag}>{escape(text)}</{tag}>"


def operation_element(namespace: str, operation: str, params: dict[str, Any]) -> str:
    """Build the operation element (with its default xmlns) and ordered params."""
    inner = "".join(to_xml(key, value) for key, value in params.items())
    return f'<{operation} xmlns="{namespace}">{inner}</{operation}>'

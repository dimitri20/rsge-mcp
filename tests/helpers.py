"""Shared test helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from rsge_mcp.config import Settings
from rsge_mcp.context import AppContext, build_context


def env(data: Any, *, sid: int = 0, text: str = "ok") -> dict[str, Any]:
    """Build a rs.ge {DATA, STATUS} envelope."""
    return {"DATA": data, "STATUS": {"ID": sid, "TEXT": text}}


@asynccontextmanager
async def make_ctx(settings: Settings) -> AsyncIterator[AppContext]:
    """Build an AppContext and close its HTTP client afterward."""
    ctx = build_context(settings)
    try:
        yield ctx
    finally:
        await ctx.http.aclose()


_SOAP_OPEN = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
_SOAP_CLOSE = "</soap:Body></soap:Envelope>"


def soap_scalar(operation: str, **fields: Any) -> str:
    """A SOAP response with scalar/out-parameter elements under the response."""
    inner = "".join(f"<{k}>{v}</{k}>" for k, v in fields.items())
    return (
        f'{_SOAP_OPEN}<{operation}Response xmlns="http://tempuri.org/">{inner}'
        f"</{operation}Response>{_SOAP_CLOSE}"
    )


def soap_diffgram(operation: str, table: str, rows: list[dict[str, Any]]) -> str:
    """A SOAP response wrapping a DataSet in a diffgram (one element per row)."""
    body = "".join(
        f"<{table}>" + "".join(f"<{k}>{v}</{k}>" for k, v in row.items()) + f"</{table}>"
        for row in rows
    )
    return (
        f'{_SOAP_OPEN}<{operation}Response xmlns="http://tempuri.org/"><{operation}Result>'
        f'<diffgr:diffgram xmlns:diffgr="urn:schemas-microsoft-com:xml-diffgram-v1">'
        f"<NewDataSet>{body}</NewDataSet></diffgr:diffgram>"
        f"</{operation}Result></{operation}Response>{_SOAP_CLOSE}"
    )


def soap_fault(message: str) -> str:
    """A SOAP 1.1 fault response."""
    return (
        f"{_SOAP_OPEN}<soap:Fault><faultcode>soap:Server</faultcode>"
        f"<faultstring>{message}</faultstring></soap:Fault>{_SOAP_CLOSE}"
    )


class FakeMCP:
    """Captures tools registered via ``@mcp.tool()`` so tests can call them directly."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            self.tools[fn.__name__] = fn
            return fn

        return decorator

"""Common reference + transaction tools (eAPI ``Common/*``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_units() -> Any:
        """List measurement units (value/label) used by invoices and waybills."""
        return await ctx.rest.post("/Common/GetUnits", {})

    @mcp.tool()
    async def rsge_get_transaction_result(transaction_id: str) -> Any:
        """Fetch the result of an asynchronous operation by its TransactionId (UUID).

        Used to resolve a `SaveInvoice` that returned a TransactionId instead of a
        final result.
        """
        return await ctx.rest.post(
            "/Common/GetTransactionResult", {"TransactionId": transaction_id}
        )

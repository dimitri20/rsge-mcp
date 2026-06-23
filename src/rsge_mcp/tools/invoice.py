"""VAT invoice tools (Tax Document eAPI ``Invoice/*``).

Reads list/fetch invoices; writes save and run the buyer/seller lifecycle. Writes are
sent with ``retry_reads=False`` so they are never auto-retried.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..models.invoice import InvoiceGood
from ._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext

_POLL_ATTEMPTS = 10


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_invoice(invoice_id: int) -> Any:
        """Fetch a single VAT invoice (Tax Document eAPI) by its numeric InvoiceID."""
        return await ctx.rest.post("/Invoice/GetInvoice", {"InvoiceID": invoice_id})

    @mcp.tool()
    async def rsge_list_invoices(filters: dict[str, Any] | None = None) -> Any:
        """List VAT invoices.

        `filters` is an optional dict of rs.ge filter fields (date ranges, seller/buyer
        TIN, status). Omit it for the API defaults.
        """
        return await ctx.rest.post("/Invoice/ListInvoices", filters or {})

    @mcp.tool()
    async def rsge_save_invoice(
        seller_tin: str,
        buyer_tin: str,
        operation_date: str,
        goods: list[InvoiceGood],
        inv_category: int = 1,
        inv_type: int = 2,
        extra: dict[str, Any] | None = None,
        wait: bool = False,
    ) -> Any:
        """Create or save a VAT invoice (Tax Document eAPI).

        - `operation_date`: 'DD-MM-YYYY HH:MM:SS'.
        - `goods`: line items (INVOICE_GOODS). Each needs GOODS_NAME, UNIT_ID,
          QUANTITY, UNIT_PRICE; BARCODE and VAT_TYPE are optional.
        - `extra`: merged into the INVOICE object for fields not exposed as params.
        - `wait`: if the API returns a TransactionId, poll until a result is ready.

        WRITE — never auto-retried. Returns the saved invoice data (e.g. INVOICE_ID),
        or a TransactionId to resolve via `rsge_get_transaction_result` (or pass
        `wait=True`).
        """
        invoice = compact(
            {
                "INV_CATEGORY": inv_category,
                "INV_TYPE": inv_type,
                "TIN_SELLER": seller_tin,
                "TIN_BUYER": buyer_tin,
                "OPERATION_DATE": operation_date,
                "INVOICE_GOODS": [compact(good.model_dump()) for good in goods],
            }
        )
        if extra:
            invoice.update(extra)
        data = await ctx.rest.post(
            "/Invoice/SaveInvoice", {"INVOICE": invoice}, retry_reads=False, write=True
        )
        if wait and isinstance(data, dict):
            tid = data.get("TransactionId") or data.get("TRANSACTION_ID")
            if tid:
                return await _poll_transaction(ctx, str(tid))
        return data

    @mcp.tool()
    async def rsge_confirm_invoice(invoice_id: int) -> Any:
        """Buyer-confirm a VAT invoice by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/ConfirmInvoice", _id_body(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_refuse_invoice(invoice_id: int) -> Any:
        """Buyer-refuse a VAT invoice by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/RefuseInvoice", _id_body(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_cancel_invoice(invoice_id: int) -> Any:
        """Seller-cancel a VAT invoice by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/CancelInvoice", _id_body(invoice_id), retry_reads=False, write=True
        )


def _id_body(invoice_id: int) -> dict[str, Any]:
    # The single-invoice lifecycle key is thin in the docs (GetInvoice uses
    # "InvoiceID"; batch ops use item "ID"). We send "ID" and will confirm/adjust
    # against the test environment during integration verification.
    return {"ID": invoice_id}


async def _poll_transaction(ctx: AppContext, transaction_id: str) -> Any:
    """Poll Common/GetTransactionResult, honoring the rate delay, up to a cap."""
    delay = ctx.settings.rate_delay_ms / 1000.0
    for _ in range(_POLL_ATTEMPTS):
        result = await ctx.rest.post(
            "/Common/GetTransactionResult", {"TransactionId": transaction_id}
        )
        if isinstance(result, dict) and result:
            return result
        await asyncio.sleep(delay)
    return {"transaction_id": transaction_id, "status": "pending"}

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
            "/Invoice/ConfirmInvoice", _invoice_ref(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_refuse_invoice(invoice_id: int) -> Any:
        """Buyer-refuse a VAT invoice by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/RefuseInvoice", _invoice_ref(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_cancel_invoice(invoice_id: int) -> Any:
        """Seller-cancel a VAT invoice by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/CancelInvoice", _invoice_ref(invoice_id), retry_reads=False, write=True
        )

    # --- reference reads ---
    @mcp.tool()
    async def rsge_list_excise(filters: dict[str, Any] | None = None) -> Any:
        """List excisable goods and their excise rates (Tax Document eAPI).

        `filters` (all optional): PRODUCT_NAME, EFFECT_DATE / END_DATE as
        'DD-MM-YYYY:DD-MM-YYYY' ranges, MAXIMUM_ROWS. Omit for the API defaults.
        """
        return await ctx.rest.post("/Invoice/ListExcise", filters or {})

    @mcp.tool()
    async def rsge_list_barcodes(filters: dict[str, Any] | None = None) -> Any:
        """List saved goods barcodes (Tax Document eAPI).

        `filters` (all optional): BARCODE, GOODS_NAME, UNIT_TXT, VAT_TYPE_TXT,
        UNIT_PRICE, MAXIMUM_ROWS. Omit for the API defaults.
        """
        return await ctx.rest.post("/Invoice/ListBarCodes", filters or {})

    @mcp.tool()
    async def rsge_get_barcode(barcode: str) -> Any:
        """Look up a single goods barcode. Returns the record, or {} if not found."""
        return await ctx.rest.post("/Invoice/GetBarCode", {"barCode": barcode})

    @mcp.tool()
    async def rsge_list_goods(invoice_ids: list[int]) -> Any:
        """Fetch full invoices with their line-item goods, for several InvoiceIDs."""
        return await ctx.rest.post("/Invoice/ListGoods", _invoice_batch(invoice_ids))

    @mcp.tool()
    async def rsge_get_actions() -> Any:
        """List the valid invoice status/action codes (reference data)."""
        return await ctx.rest.post("/Invoice/GetActions", {})

    # --- lifecycle / declaration writes ---
    @mcp.tool()
    async def rsge_activate_invoice(invoice_id: int) -> Any:
        """Activate a saved VAT invoice by InvoiceID — assigns its registration number,
        making it binding. To save and activate in one go, call rsge_save_invoice then
        this. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/ActivateInvoice", _invoice_ref(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_activate_invoices(invoice_ids: list[int]) -> Any:
        """Batch-activate VAT invoices by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/ActivateInvoices",
            _invoice_batch(invoice_ids),
            retry_reads=False,
            write=True,
        )

    @mcp.tool()
    async def rsge_delete_invoice(invoice_id: int) -> Any:
        """Delete a draft VAT invoice by InvoiceID. Only saved / unconfirmed / refused
        invoices can be deleted. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/DeleteInvoice", _invoice_ref(invoice_id), retry_reads=False, write=True
        )

    @mcp.tool()
    async def rsge_confirm_invoices(invoice_ids: list[int]) -> Any:
        """Batch buyer-confirm VAT invoices by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/ConfirmInvoices",
            _invoice_batch(invoice_ids),
            retry_reads=False,
            write=True,
        )

    @mcp.tool()
    async def rsge_refuse_invoices(invoice_ids: list[int]) -> Any:
        """Batch buyer-refuse VAT invoices by InvoiceID. WRITE — not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/RefuseInvoices",
            _invoice_batch(invoice_ids),
            retry_reads=False,
            write=True,
        )

    @mcp.tool()
    async def rsge_clear_barcodes() -> Any:
        """Clear all saved goods barcodes for the account. WRITE — not auto-retried."""
        return await ctx.rest.post("/Invoice/ClearBarCodes", {}, retry_reads=False, write=True)

    @mcp.tool()
    async def rsge_get_seqnum(operation_period: str) -> Any:
        """Allocate the next VAT-declaration sequence number for a month.

        `operation_period`: 'YYYYMM' (e.g. '202601'). WRITE (allocates a number) —
        not auto-retried."""
        return await ctx.rest.post(
            "/Invoice/GetSeqNum",
            {"OperationPeriod": operation_period},
            retry_reads=False,
            write=True,
        )

    @mcp.tool()
    async def rsge_create_decl(invoice_ids: list[int], operation_period: str) -> Any:
        """Link confirmed VAT invoices to the declaration for a month.

        `operation_period`: 'YYYYMM'. WRITE — not auto-retried."""
        body = {**_invoice_batch(invoice_ids), "OperationPeriod": operation_period}
        return await ctx.rest.post("/Invoice/CreateDecl", body, retry_reads=False, write=True)


def _invoice_ref(invoice_id: int) -> dict[str, Any]:
    # Single-invoice envelope for Activate / Delete / Confirm / Refuse / Cancel. The
    # shape is {"INVOICE": {"ID": n}} per rs.ge's docs + Postman (15_postman.json);
    # confirm against the live test host once it is back up.
    return {"INVOICE": {"ID": invoice_id}}


def _invoice_batch(invoice_ids: list[int]) -> dict[str, Any]:
    # Batch-id envelope for ListGoods / ActivateInvoices / ConfirmInvoices /
    # RefuseInvoices / CreateDecl.
    return {"Invoices": [{"ID": i} for i in invoice_ids]}


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

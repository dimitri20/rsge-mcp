"""Invoice payload models.

Only the *repeated* nested structure (a goods line item) is modeled, so the LLM gets one
clear schema to fill per line. The invoice header's common fields are curated as tool
params, and a free-form ``extra`` dict carries the long tail. ``extra="allow"`` lets a
caller pass additional per-item fields the docs don't enumerate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InvoiceGood(BaseModel):
    """A single line item in a VAT invoice (``INVOICE_GOODS[]``)."""

    model_config = ConfigDict(extra="allow")

    GOODS_NAME: str
    UNIT_ID: int
    QUANTITY: float
    UNIT_PRICE: float
    BARCODE: str | None = None
    VAT_TYPE: int | None = None
    ID: int = 0

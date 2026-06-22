"""Waybill payload models.

Models only the repeated nested goods line item (``WAYBILL -> GOODS_LIST -> GOODS[]``);
``extra="allow"`` lets callers add fields the docs don't enumerate. Field names match the
SOAP element names exactly (incl. rs.ge's own spellings).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WaybillGood(BaseModel):
    """A single goods line item in a waybill (``GOODS``)."""

    model_config = ConfigDict(extra="allow")

    W_NAME: str
    UNIT_ID: int
    QUANTITY: float
    PRICE: float
    UNIT_TXT: str | None = None
    BAR_CODE: str | None = None
    AMOUNT: float | None = None
    VAT_TYPE: int = 0
    A_ID: int = 0
    ID: int = 0

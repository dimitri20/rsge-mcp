"""NSAF special (oil/fuel) invoice payload models (SOAP ``SpecInvoicesService``).

Two heavy, flat payloads get a Pydantic model so callers don't pass dozens of positional
args: ``SpecInvoice`` (the ``save_invoice_b_n`` header) and ``SpecInvoiceDesc`` (a
``save_invoice_desc_n`` line item). Field names match the SOAP element names EXACTLY and in
WSDL order — ``model_dump()`` preserves that order and the tool drops ``None`` optionals via
``compact()``. ``su``/``sp``/``user_id``/``id``/``p_inv_id`` are NOT model fields; the tools
supply them at the right WSDL position. ``extra="allow"`` lets callers add fields the docs
don't enumerate.
"""

# Field names mirror the rs.ge SOAP wire elements verbatim (incl. mixedCase like
# ``invoiceType`` and ``p_OPERATION_DT``), so the mixed-case-attribute lint does not apply.
# ruff: noqa: N815

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SpecInvoice(BaseModel):
    """Header for ``save_invoice_b_n`` (NSAF oil/fuel special invoice).

    Four DISTINCT issuer-id ints coexist by design: ``p_USER_ID``, ``p_S_USER_ID``,
    ``p_B_S_USER_ID`` and ``user_id`` — do not collapse them. The five required date fields
    are typed required ``str`` (no ``None``) so ``compact()`` cannot drop a ``minOccurs=1``
    element; ``p_CALC_DATE``/``p_TR_ST_DATE`` are documented "unused" but still need a value
    (pass a placeholder ISO datetime). ``invoiceType``/``p_PAY_TYPE``/``p_*_ALT_STATUS`` are
    opaque rs.ge int codes — confirm against current rs.ge spec-invoice documentation.
    """

    model_config = ConfigDict(extra="allow")

    # --- required (minOccurs=1), in WSDL order ---
    invois_id: int = 0  # 0 -> new invoice
    p_OPERATION_DT: str
    p_SELLER_UN_ID: int
    p_BUYER_UN_ID: int
    p_CALC_DATE: str  # required-nillable; send a value
    # (optionals p_SSD_N/p_SSAF_N/p_K_SSAF_N slot here in WSDL order, declared below)
    p_TR_ST_DATE: str  # required-nillable; send a value
    p_USER_ID: int
    p_S_USER_ID: int
    p_B_S_USER_ID: int
    p_SSD_DATE: str  # required-nillable; send a value
    p_SSAF_DATE: str  # required-nillable; send a value
    p_PAY_TYPE: int
    p_SSAF_ALT_STATUS: int
    p_SSD_ALT_STATUS: int
    p_driver_is_geo: int  # 0=foreign, 1=Georgian
    user_id: int
    invoiceType: int

    # --- optional (minOccurs=0); dropped by compact() when None ---
    p_SSD_N: str | None = None
    p_SSAF_N: str | None = None
    p_K_SSAF_N: str | None = None
    p_OIL_ST_ADDRESS: str | None = None
    p_OIL_ST_N: str | None = None
    p_OIL_FN_ADDRESS: str | None = None
    p_OIL_FN_N: str | None = None
    p_TRANSPORT_TYPE: str | None = None
    p_TRANSPORT_MARK: str | None = None
    p_DRIVER_INFO: str | None = None
    p_CARRIER_INFO: str | None = None
    p_CARRIE_S_NO: str | None = None  # rs.ge spelling preserved
    p_SELLER_PHONE: str | None = None
    p_BUYER_PHONE: str | None = None
    p_driver_no: str | None = None
    p_SSAF_ALT_NUMBER: str | None = None
    p_SSAF_ALT_TYPE: str | None = None
    p_SSD_ALT_NUMBER: str | None = None
    p_SSD_ALT_TYPE: str | None = None

    def to_params(self) -> dict[str, object]:
        """Ordered SOAP params in WSDL order (invois_id..invoiceType then optionals).

        The wire requires the optional p_SSD_N/p_SSAF_N/p_K_SSAF_N block to sit between
        p_BUYER_UN_ID and p_CALC_DATE, and the oil/transport optionals between p_BUYER_UN_ID
        ... — to keep it simple and correct, emit ALL fields in the exact WSDL sequence here.
        """
        ordered = [
            "invois_id",
            "p_OPERATION_DT",
            "p_SELLER_UN_ID",
            "p_BUYER_UN_ID",
            "p_SSD_N",
            "p_SSAF_N",
            "p_CALC_DATE",
            "p_K_SSAF_N",
            "p_TR_ST_DATE",
            "p_OIL_ST_ADDRESS",
            "p_OIL_ST_N",
            "p_OIL_FN_ADDRESS",
            "p_OIL_FN_N",
            "p_TRANSPORT_TYPE",
            "p_TRANSPORT_MARK",
            "p_DRIVER_INFO",
            "p_CARRIER_INFO",
            "p_CARRIE_S_NO",
            "p_USER_ID",
            "p_S_USER_ID",
            "p_B_S_USER_ID",
            "p_SSD_DATE",
            "p_SSAF_DATE",
            "p_PAY_TYPE",
            "p_SELLER_PHONE",
            "p_BUYER_PHONE",
            "p_driver_no",
            "p_SSAF_ALT_NUMBER",
            "p_SSAF_ALT_TYPE",
            "p_SSD_ALT_NUMBER",
            "p_SSD_ALT_TYPE",
            "p_SSAF_ALT_STATUS",
            "p_SSD_ALT_STATUS",
            "p_driver_is_geo",
            "user_id",
            "invoiceType",
        ]
        data = self.model_dump()
        return {key: data[key] for key in ordered if data.get(key) is not None}


class SpecInvoiceDesc(BaseModel):
    """A single line item for ``save_invoice_desc_n``.

    The tool supplies ``user_id``/``id``/``su``/``sp``/``p_inv_id``; this model is the
    ``p_goods``..``p_drg_type`` slice in WSDL order. ``p_user_id`` is a SECOND, distinct user
    id. ``p_good_id`` links to a ``rsge_spec_get_products`` result. ``p_drg_type`` is an opaque
    rs.ge int code.
    """

    model_config = ConfigDict(extra="allow")

    p_goods: str | None = None
    p_g_unit: str | None = None
    p_g_number: float
    p_un_price: float
    p_drg_amount: float
    p_aqcizi_amount: float
    p_user_id: int
    p_aqcizi_id: str | None = None
    p_aqcizi_rate: float
    p_dgg_rate: float
    p_g_number_alt: float
    p_good_id: int
    p_drg_type: int

    def to_params(self) -> dict[str, object]:
        """Ordered SOAP params in WSDL order (p_goods..p_drg_type); None optionals dropped."""
        ordered = [
            "p_goods",
            "p_g_unit",
            "p_g_number",
            "p_un_price",
            "p_drg_amount",
            "p_aqcizi_amount",
            "p_user_id",
            "p_aqcizi_id",
            "p_aqcizi_rate",
            "p_dgg_rate",
            "p_g_number_alt",
            "p_good_id",
            "p_drg_type",
        ]
        data = self.model_dump()
        return {key: data[key] for key in ordered if data.get(key) is not None}

"""SOAP service metadata (endpoint + XML namespace).

All rs.ge .asmx services use the ASP.NET default namespace ``http://tempuri.org/`` and
SOAP 1.1. Endpoints mirror the ``soap`` section of ``endpoints.json``.
"""

from __future__ import annotations

from dataclasses import dataclass

TEMPURI_NS = "http://tempuri.org/"


@dataclass(frozen=True)
class SoapService:
    name: str
    endpoint: str
    namespace: str = TEMPURI_NS


WAYBILL = SoapService(
    name="WayBillService",
    endpoint="https://services.rs.ge/WayBillService/WayBillService.asmx",
)

NTOS = SoapService(
    name="ntosservice",
    endpoint="https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
)

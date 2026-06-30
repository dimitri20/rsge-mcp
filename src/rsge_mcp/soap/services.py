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

TAXPAYER = SoapService(
    name="taxpayerservice",
    endpoint="https://services.rs.ge/taxservice/taxpayerservice.asmx",
)

# NSAF special (oil/fuel) invoices. Note the distinct host: webserv.rs.ge.
SPECINVOICES = SoapService(
    name="SpecInvoicesService",
    endpoint="https://webserv.rs.ge/specinvoices/SpecInvoicesService.asmx",
)

# Duty-free goods journals. Same webserv.rs.ge host; authenticates with userName/password.
DUTYFREE = SoapService(
    name="wsdutyfree",
    endpoint="https://webserv.rs.ge/dutyfree/wsdutyfree.asmx",
)

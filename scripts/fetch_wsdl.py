#!/usr/bin/env python3
"""Fetch the SOAP WSDLs for all six legacy rs.ge .asmx services and enumerate
every operation. WSDL is the authoritative contract; Postman ships only samples.

The service keys here must match the .wsdl basenames that build_inventory.py
looks up in its SOAP_META table, so the full inventory regenerates in one pass."""
import os
import re

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
WSDL_DIR = os.path.join(ROOT, "wsdl")
os.makedirs(WSDL_DIR, exist_ok=True)

SERVICES = {
    "waybill": "https://services.rs.ge/WayBillService/WayBillService.asmx?WSDL",
    "ntos": "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx?WSDL",
    "specinvoices": "https://webserv.rs.ge/specinvoices/SpecInvoicesService.asmx?WSDL",
    "dutyfree": "https://webserv.rs.ge/dutyfree/wsdutyfree.asmx?WSDL",
    "taxpayer": "https://services.rs.ge/taxservice/taxpayerservice.asmx?WSDL",
    "custompost": "https://services.rs.ge/taxservice/custompostservice.asmx?WSDL",
}

for key, url in SERVICES.items():
    try:
        r = requests.get(url, timeout=60)
        path = os.path.join(WSDL_DIR, key + ".wsdl")
        with open(path, "wb") as f:
            f.write(r.content)
        text = r.text
        # portType operations are the canonical op list (one per binding pair).
        ops = sorted(set(re.findall(r'<(?:wsdl:)?operation\s+name="([^"]+)"', text)))
        print(f"{key:13} HTTP {r.status_code}  {len(r.content):>8}B  {len(ops)} ops")
        print("   ", ", ".join(ops))
    except Exception as e:
        print(f"{key:13} ERROR {e}")

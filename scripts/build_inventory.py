#!/usr/bin/env python3
"""Build the final unified endpoint inventory (endpoints.json) from the fetched
WSDLs + Postman collections, plus a curated REST surface for the eapi.rs.ge /
xdata.rs.ge JSON services. Prints final totals used in SUMMARY.md."""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
OUT_ROOT = os.path.abspath(os.path.join(ROOT, ".."))
WSDL_DIR = os.path.join(ROOT, "wsdl")
POSTMAN_DIR = os.path.join(ROOT, "postman")

# wsdl file -> metadata
SOAP_META = {
    "waybill": ("WayBillService", "https://services.rs.ge/WayBillService/WayBillService.asmx", "Waybills (ზედნადები)", ["1"]),
    "ntos": ("ntosservice", "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx", "VAT invoices (ანგარიშ-ფაქტურა)", ["2"]),
    "specinvoices": ("SpecInvoicesService", "https://webserv.rs.ge/specinvoices/SpecInvoicesService.asmx", "NSAF special invoices (ნსაფ)", ["3"]),
    "dutyfree": ("wsdutyfree", "https://webserv.rs.ge/dutyfree/wsdutyfree.asmx", "Duty-Free goods forms", ["5", "9"]),
    "taxpayer": ("taxpayerservice", "https://services.rs.ge/taxservice/taxpayerservice.asmx", "Taxpayer info / income / Z-reports", ["10", "11", "14"]),
    "custompost": ("custompostservice", "https://services.rs.ge/taxservice/custompostservice.asmx", "Postal parcels & cargo declarations", ["4", "6"]),
}


def wsdl_ops(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    return sorted(set(re.findall(r'<(?:wsdl:)?operation\s+name="([^"]+)"', t)))


inv = {"soap": {}, "rest": {}, "postman": {}}

for fn in sorted(os.listdir(WSDL_DIR)):
    if not fn.endswith(".wsdl"):
        continue
    key = fn[:-5]
    meta = SOAP_META.get(key)
    ops = wsdl_ops(os.path.join(WSDL_DIR, fn))
    inv["soap"][key] = {
        "service": meta[0] if meta else key,
        "endpoint": meta[1] if meta else "?",
        "description": meta[2] if meta else "",
        "doc_ids": meta[3] if meta else [],
        "operation_count": len(ops),
        "operations": ops,
    }

# Curated REST surface (from eAPI PDF + customs HTML + Postman + xdata refs).
inv["rest"] = {
    "eapi_users": {"base": "https://eapi.rs.ge/Users", "auth": "credentials -> bearer token",
        "endpoints": ["Authenticate", "AuthenticatePin", "SignOut"]},
    "eapi_common_org": {"base": "https://eapi.rs.ge", "auth": "bearer",
        "endpoints": ["Org/GetVatPayerStatus", "Org/GetOrgInfoByTin", "Common/GetUnits", "Common/GetTransactionResult"]},
    "eapi_invoice": {"base": "https://eapi.rs.ge/Invoice", "auth": "bearer", "doc_ids": ["15"],
        "endpoints": ["GetInvoice", "SaveInvoice", "ActivateInvoice", "ActivateInvoices", "DeleteInvoice",
            "CancelInvoice", "RefuseInvoice", "RefuseInvoices", "ConfirmInvoice", "ConfirmInvoices",
            "ListInvoices", "ListExcise", "ListBarCodes", "GetBarCode", "ClearBarCodes", "GetSeqNum",
            "CreateDecl", "ListGoods", "GetActions"]},
    "eapi_employees": {"base": "https://eapi.rs.ge/Employees", "auth": "bearer", "doc_ids": ["16"],
        "endpoints": ["GetCountries", "GetEmployee", "SaveEmployee", "ListEmployees"]},
    "eapi_customs": {"base": "https://eapi.rs.ge/CustomsDeclarations", "auth": "bearer", "doc_ids": ["18"],
        "endpoints": ["GetAsycudaDeclarations"]},
    "xdata_taxpayer": {"base": "https://xdata.rs.ge/TaxPayer", "auth": "api key / token", "doc_ids": ["17"],
        "endpoints": ["RSPublicInfo", "IncomeInfo", "SmsVerification", "CheckPhoneNumber"]},
    "oauth": {"base": "https://eservices.rs.ge/WebServices/oAuth.ashx", "auth": "OAuth", "doc_ids": ["13"],
        "endpoints": ["oAuth.ashx (authorize/token)"]},
}

# Postman counts
def walk(items, acc, prefix=""):
    for it in items or []:
        if "item" in it:
            walk(it["item"], acc, (prefix + " / " if prefix else "") + it.get("name", ""))
        elif "request" in it:
            req = it["request"]
            url = req.get("url")
            if isinstance(url, dict):
                url = url.get("raw") or "/".join(url.get("path", []))
            acc.append({"name": it.get("name", ""), "method": req.get("method", ""), "url": url or ""})


for fn in sorted(os.listdir(POSTMAN_DIR)):
    with open(os.path.join(POSTMAN_DIR, fn), encoding="utf-8") as f:
        col = json.load(f)
    reqs = []
    walk(col.get("item", []), reqs)
    inv["postman"][fn] = {
        "collection_name": col.get("info", {}).get("name", ""),
        "request_count": len(reqs),
        "requests": reqs,
    }

with open(os.path.join(OUT_ROOT, "endpoints.json"), "w", encoding="utf-8") as f:
    json.dump(inv, f, ensure_ascii=False, indent=2)

soap_total = sum(v["operation_count"] for v in inv["soap"].values())
rest_total = sum(len(v["endpoints"]) for v in inv["rest"].values())
pm_total = sum(v["request_count"] for v in inv["postman"].values())

print("=== SOAP (WSDL-authoritative) ===")
for k, v in inv["soap"].items():
    print(f"  {v['service']:20} {v['operation_count']:>3} ops   {v['endpoint']}")
print(f"  SOAP TOTAL: {soap_total} operations across {len(inv['soap'])} services\n")
print("=== REST/JSON (eapi.rs.ge + xdata.rs.ge + OAuth) ===")
for k, v in inv["rest"].items():
    print(f"  {k:18} {len(v['endpoints']):>3} endpoints  {v['base']}")
print(f"  REST TOTAL: {rest_total} endpoints across {len(inv['rest'])} groups\n")
print(f"GRAND TOTAL documented operations/endpoints: {soap_total + rest_total}")
print(f"Postman sample requests: {pm_total}")

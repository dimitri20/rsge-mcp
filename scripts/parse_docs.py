#!/usr/bin/env python3
"""Extract text from every downloaded doc and build a unified endpoint inventory.

Outputs:
  docs/text/<name>.txt        plain text per PDF/HTML (greppable; empty => scanned)
  docs/extract_report.json    per-file extraction status (pages, chars, scanned?)
  endpoints.json              unified inventory: SOAP (WSDL) + REST/SOAP (Postman)
"""
import json
import os
import re
from html.parser import HTMLParser

from pypdf import PdfReader

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
PROTO_DIR = os.path.join(ROOT, "protocols")
POSTMAN_DIR = os.path.join(ROOT, "postman")
WSDL_DIR = os.path.join(ROOT, "wsdl")
TEXT_DIR = os.path.join(ROOT, "text")
OUT_ROOT = os.path.abspath(os.path.join(ROOT, ".."))
os.makedirs(TEXT_DIR, exist_ok=True)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data)

    def text(self):
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts))


def extract_pdf(path):
    reader = PdfReader(path)
    pages = []
    for pg in reader.pages:
        try:
            pages.append(pg.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n\n".join(pages)
    return text, len(reader.pages)


def extract_html(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    p = TextExtractor()
    p.feed(raw)
    return p.text(), None


# ---- 1. text extraction ----------------------------------------------------
extract_report = []
for fn in sorted(os.listdir(PROTO_DIR)):
    src = os.path.join(PROTO_DIR, fn)
    base = os.path.splitext(fn)[0]
    try:
        if fn.lower().endswith(".pdf"):
            text, npages = extract_pdf(src)
        elif fn.lower().endswith((".html", ".htm")):
            text, npages = extract_html(src)
        else:
            continue
        out = os.path.join(TEXT_DIR, base + ".txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        chars = len(text.strip())
        scanned = fn.lower().endswith(".pdf") and chars < 200  # heuristic
        extract_report.append(
            {"file": fn, "pages": npages, "chars": chars, "scanned_suspect": scanned}
        )
        tag = "SCANNED?" if scanned else "ok"
        print(f"  [{tag:>8}] {fn:55} pages={npages} chars={chars}")
    except Exception as e:
        extract_report.append({"file": fn, "error": str(e)})
        print(f"  [   ERROR] {fn}: {e}")

with open(os.path.join(ROOT, "extract_report.json"), "w", encoding="utf-8") as f:
    json.dump(extract_report, f, ensure_ascii=False, indent=2)


# ---- 2. endpoint inventory -------------------------------------------------
inventory = {"soap_wsdl": {}, "postman": {}}

# 2a. SOAP WSDL operations (authoritative)
wsdl_endpoints = {
    "waybill": "https://services.rs.ge/WayBillService/WayBillService.asmx",
    "ntos": "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
    "specinvoices": "https://webserv.rs.ge/specinvoices/SpecInvoicesService.asmx",
}
for key, endpoint in wsdl_endpoints.items():
    wpath = os.path.join(WSDL_DIR, key + ".wsdl")
    if not os.path.exists(wpath):
        continue
    with open(wpath, "r", encoding="utf-8", errors="replace") as f:
        wtext = f.read()
    ops = sorted(set(re.findall(r'<(?:wsdl:)?operation\s+name="([^"]+)"', wtext)))
    inventory["soap_wsdl"][key] = {"endpoint": endpoint, "operation_count": len(ops), "operations": ops}


# 2b. Postman requests (verified examples)
def walk(items, acc, prefix=""):
    for it in items or []:
        if "item" in it:
            walk(it["item"], acc, (prefix + " / " if prefix else "") + it.get("name", ""))
        elif "request" in it:
            req = it["request"]
            url = req.get("url")
            if isinstance(url, dict):
                url = url.get("raw") or "/".join(url.get("path", []))
            acc.append(
                {"folder": prefix, "name": it.get("name", ""), "method": req.get("method", ""), "url": url or ""}
            )


for fn in sorted(os.listdir(POSTMAN_DIR)):
    with open(os.path.join(POSTMAN_DIR, fn), "r", encoding="utf-8") as f:
        col = json.load(f)
    reqs = []
    walk(col.get("item", []), reqs)
    unique_urls = sorted(set(r["url"] for r in reqs))
    inventory["postman"][fn] = {
        "collection_name": col.get("info", {}).get("name", ""),
        "request_count": len(reqs),
        "unique_url_count": len(unique_urls),
        "requests": reqs,
    }

with open(os.path.join(OUT_ROOT, "endpoints.json"), "w", encoding="utf-8") as f:
    json.dump(inventory, f, ensure_ascii=False, indent=2)

# ---- summary numbers -------------------------------------------------------
soap_total = sum(v["operation_count"] for v in inventory["soap_wsdl"].values())
pm_total = sum(v["request_count"] for v in inventory["postman"].values())
print("\n=== INVENTORY ===")
for k, v in inventory["soap_wsdl"].items():
    print(f"  SOAP {k:13} {v['operation_count']} ops")
print(f"  SOAP TOTAL: {soap_total} operations")
for k, v in inventory["postman"].items():
    print(f"  PM   {k:25} {v['request_count']} reqs / {v['unique_url_count']} unique urls  ({v['collection_name']})")
print(f"  POSTMAN TOTAL: {pm_total} sample requests")

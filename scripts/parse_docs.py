#!/usr/bin/env python3
"""Extract text from every downloaded doc for grepping / inspection.

Outputs:
  docs/text/<name>.txt        plain text per PDF/HTML (greppable; empty => scanned)
  docs/extract_report.json    per-file extraction status (pages, chars, scanned?)

The unified endpoint inventory (endpoints.json) is built separately and
authoritatively by build_inventory.py — this script does not touch it.
"""
import json
import os
import re
from html.parser import HTMLParser

from pypdf import PdfReader

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
PROTO_DIR = os.path.join(ROOT, "protocols")
TEXT_DIR = os.path.join(ROOT, "text")
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

print(f"\nExtracted {len(extract_report)} docs -> {os.path.relpath(TEXT_DIR)}/")
print("Run build_inventory.py to (re)build endpoints.json.")

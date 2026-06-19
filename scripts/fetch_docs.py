#!/usr/bin/env python3
"""Download all rs.ge API documentation (protocols + Postman collections).

Reverse-engineered backend (see SUMMARY.md / plan):
  manifest : POST https://eapi.rs.ge/Downloads/GetProtocols
  doc      : POST https://eapi.rs.ge/Downloads/GetProtocolFile?fileName=<DocName>&id=<ID>
  postman  : POST https://eapi.rs.ge/Downloads/GetPostmanFile?fileName=postman.json&id=<ID>

No auth is required for downloads. The server returns the raw file with a
content-disposition header, OR a JSON error blob (still HTTP 200) on bad params,
so we validate by magic bytes.
"""
import json
import os
import re
import sys
import time
from urllib.parse import urlencode

import requests

BASE = "https://eapi.rs.ge/"
ROOT = os.path.join(os.path.dirname(__file__), "..", "docs")
ROOT = os.path.abspath(ROOT)
PROTO_DIR = os.path.join(ROOT, "protocols")
POSTMAN_DIR = os.path.join(ROOT, "postman")

session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "*/*"})


def sanitize(name: str) -> str:
    """Make a filesystem-friendly basename (keep extension)."""
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name


def magic_ok(path: str) -> str:
    """Return detected type or 'ERROR' if it looks like a JSON error blob."""
    with open(path, "rb") as f:
        head = f.read(64)
    if head[:4] == b"%PDF":
        return "pdf"
    low = head.lstrip()[:16].lower()
    if low.startswith(b"<!doctype") or low.startswith(b"<html"):
        return "html"
    if head.lstrip()[:1] in (b"{", b"["):
        # Could be a valid Postman json OR an error blob {"message": "...not found..."}
        try:
            with open(path, "rb") as f:
                data = json.load(f)
            if isinstance(data, dict) and "message" in data and len(data) == 1:
                return "ERROR"
            return "json"
        except Exception:
            return "json?"
    return "unknown"


def download(path: str, params: dict, out_path: str) -> dict:
    url = BASE + path + "?" + urlencode(params)
    r = session.post(url, data=json.dumps(params), timeout=60)
    with open(out_path, "wb") as f:
        f.write(r.content)
    kind = magic_ok(out_path)
    return {
        "url": url,
        "status": r.status_code,
        "bytes": len(r.content),
        "kind": kind,
        "content_type": r.headers.get("content-type", ""),
        "out": os.path.relpath(out_path, ROOT),
    }


def main():
    os.makedirs(PROTO_DIR, exist_ok=True)
    os.makedirs(POSTMAN_DIR, exist_ok=True)

    # 1. manifest
    r = session.post(BASE + "Downloads/GetProtocols", data="{}", timeout=60)
    manifest = r.json()
    with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    items = manifest["DATA"]
    print(f"Manifest: {len(items)} protocol entries")

    report = []
    for it in items:
        pid = it["ID"]
        doc = it["DocName"]
        ct = it.get("CollectionType", "0")
        prefix = f"{int(pid):02d}_"
        # protocol doc
        out = os.path.join(PROTO_DIR, prefix + sanitize(doc))
        res = download("Downloads/GetProtocolFile", {"fileName": doc, "id": pid}, out)
        res.update({"id": pid, "name": it["Name"], "docName": doc, "role": "protocol"})
        report.append(res)
        flag = "OK" if res["kind"] not in ("ERROR", "unknown") else "!!"
        print(f"  [{flag}] id={pid:>2} {res['kind']:>6} {res['bytes']:>8}B  {doc}")
        time.sleep(0.3)
        # postman collection
        if ct == "1":
            pout = os.path.join(POSTMAN_DIR, prefix + "postman.json")
            pres = download(
                "Downloads/GetPostmanFile", {"fileName": "postman.json", "id": pid}, pout
            )
            pres.update({"id": pid, "name": it["Name"], "role": "postman"})
            report.append(pres)
            flag = "OK" if pres["kind"] == "json" else "!!"
            print(f"  [{flag}] id={pid:>2} POSTMAN {pres['bytes']:>7}B")
            time.sleep(0.3)

    with open(os.path.join(ROOT, "download_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    bad = [r for r in report if r["kind"] in ("ERROR", "unknown")]
    print(f"\nDownloaded {len(report)} files; {len(bad)} problematic.")
    for b in bad:
        print("  PROBLEM:", b["role"], b["id"], b["kind"], b["url"])


if __name__ == "__main__":
    main()

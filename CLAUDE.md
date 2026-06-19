# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Groundwork for an **rs.ge MCP server**. rs.ge is the Georgian Revenue Service e-services
portal; this repo mines its public API documentation into a machine-readable inventory so an
MCP server can later be built against it. **The MCP server itself does not exist yet** — see
`SUMMARY.md` §7 for the build plan. Right now the repo is a documentation/inventory pipeline.

Docs and `SUMMARY.md` are partly in **Georgian** (service names, doc titles); the text
extraction preserves Georgian, so it's greppable.

## Commands

No build system, test suite, or linter is configured — this is a set of standalone Python
scripts. Dependencies (`requests`, `pypdf`) are not pinned in a requirements file:

```bash
pip install requests pypdf
```

The four scripts form a **regeneration pipeline, run in this order** (each writes into `docs/`):

```bash
python3 scripts/fetch_docs.py       # 1. download manifest + protocol PDFs/HTML + Postman collections
python3 scripts/fetch_wsdl.py       # 2. fetch all 6 SOAP WSDLs + print their operation counts
python3 scripts/parse_docs.py       # 3. extract text from docs -> docs/text/ (also writes a first-pass endpoints.json)
python3 scripts/build_inventory.py  # 4. AUTHORITATIVE endpoints.json (overwrites step 3's) + prints SUMMARY.md totals
```

Scripts take no arguments and hit **live government endpoints** (they `time.sleep(0.3)` between
calls — keep that). Downloads need no auth; the API returns JSON error blobs as HTTP 200, so
`fetch_docs.py` validates by magic bytes.

## Critical: regenerated vs. committed artifacts

`docs/` is **gitignored** (raw rs.ge documents are © Georgian Revenue Service, not redistributed)
and **absent on a fresh clone**. Run the pipeline above to repopulate it. The committed, canonical
artifacts are:

- **`endpoints.json`** — the unified inventory (the deliverable). Authored **last** by
  `build_inventory.py`; schema is `{soap, rest, postman}`. Note `parse_docs.py` writes an earlier
  `{soap_wsdl, postman}` version of the same file that `build_inventory.py` then overwrites — only
  the latter is authoritative.
- **`SUMMARY.md`** — human-readable architecture summary; its counts come from `build_inventory.py`'s
  printed totals. Update it when the inventory changes.

## Architecture of the API surface (the thing being modeled)

The rs.ge API splits into **two generations** that an MCP must bridge differently:

- **Legacy SOAP/`.asmx`** — 6 services, ~251 operations (Waybills, VAT invoices, NSAF, Duty-Free,
  taxpayer/income/Z-reports, parcels/cargo). Auth = **service-user** credentials passed in each SOAP
  body. The **WSDL is the authoritative operation list**; Postman collections ship only a working
  *subset* of samples — never treat Postman as the full surface.
- **Modern REST/JSON** (`eapi.rs.ge`, `xdata.rs.ge`) — Tax Document/Invoice, Employees, Customs,
  taxpayer public info. Auth = **bearer token** (`Users/Authenticate` → token). Uniform envelope
  `{DATA, STATUS:{ID,TEXT}}`. Maps almost 1:1 to MCP tools → build these first.

Four auth models exist (SOAP service-user, eAPI bearer, 2-step SMS OTP, OAuth delegation). Out of
scope for an HTTP MCP: the SAM module (smartcard hardware protocol) and the Windows desktop apps.

### How the inventory is assembled (`build_inventory.py`)

- **SOAP** section: parsed from the `.wsdl` files via regex on `<operation name="…">`. Per-service
  metadata (service name, endpoint URL, human description, source doc IDs) is hardcoded in `SOAP_META`.
- **REST** section: **hand-curated** in the script, not scraped — when the REST surface changes you
  edit the `inv["rest"] = {…}` literal directly.
- **Postman** section: walked recursively from each collection's nested `item` tree.

## Gotchas

- The `.wsdl` basenames written by `fetch_wsdl.py` (its `SERVICES` keys) must stay in sync with the
  keys `build_inventory.py` looks up in `SOAP_META` — both currently list the same six
  (waybill, ntos, specinvoices, dutyfree, taxpayer, custompost). Adding a SOAP service means editing
  both tables.
- Environments: production is `eapi.rs.ge` / `services.rs.ge`; a test host `etest1.rs.ge` is referenced
  by the SPA. Confirm which the user wants before any live integration work.

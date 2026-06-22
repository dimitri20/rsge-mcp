# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two things live here:

1. **The rs.ge MCP server** (`src/rsge_mcp/`) — an MCP server exposing the Georgian Revenue
   Service API as LLM tools. **Both generations are implemented** (22 tools): Phase 1 (REST/eAPI)
   and Phase 2 (legacy SOAP — waybills + VAT invoices). See `SUMMARY.md` §7 for the overall plan.
2. **A documentation-inventory pipeline** (`scripts/`, `endpoints.json`, `SUMMARY.md`) that mines
   the rs.ge API docs into a machine-readable inventory. This is the reference the server's tools
   were hand-authored against — it is **not** a runtime dependency of the server.

Docs and `SUMMARY.md` are partly in **Georgian** (service names, doc titles); the text
extraction preserves Georgian, so it's greppable.

## Commands

### MCP server (`src/rsge_mcp/`)

Python 3.12, packaged via `pyproject.toml` (`src/` layout). Install, run, and develop:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
rsge-mcp                       # or: python -m rsge_mcp   (stdio transport)

pytest                         # unit tests + coverage (gate: --cov-fail-under=80)
pytest tests/unit/test_auth.py::test_login_caches_token   # a single test
black src tests && ruff check src tests && mypy src
RSGE_RUN_INTEGRATION=1 pytest -m integration   # opt-in LIVE smoke (public test creds)
```

Config is via env / `.env` (see `.env.example`). `RSGE_ENV=test` (default) injects the documented
public test account when no creds are set; `prod` **never** falls back to a test identity.

### Documentation pipeline (`scripts/`)

Standalone scripts; deps (`requests`, `pypdf`) are not pinned in a requirements file:

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

## MCP server architecture (`src/rsge_mcp/`)

Phase 1 implements the REST/eAPI surface. Strict layering: transport clients know nothing about
MCP; tool modules know nothing about HTTP wire details.

- `server.py` / `__main__.py` — build a FastMCP server (stdio) and register every tool module.
- `config.py` — `Settings` (frozen) from env/`.env`; resolves test-vs-prod hosts; injects public
  test creds only when `RSGE_ENV=test`.
- `rest/` — `client.py` (generic POST: bearer header, envelope unwrap, **one-shot `-104` re-auth**,
  reads-retried / **writes-never-retried**), `auth.py` (`EapiSession`: lazy login, token cache with
  expiry skew, `asyncio.Lock` against login stampede, 2FA PIN modes), `envelope.py`
  (`{DATA,STATUS}` → `DATA` or raise), `rate_limit.py` (shared ~300ms gate), `_http.py`
  (httpx → `RsgeError` mapping).
- `tools/` — one module per domain, each exposing `register(mcp, ctx)`. Tools are **hand-authored**
  with curated params/docstrings; `endpoints.json` is the reference, not an auto-gen source.
- `errors.py` — `RsgeError` hierarchy; `STATUS.ID` → exception, surfacing the Georgian `TEXT`
  verbatim plus an English gloss for known codes.

Writes (`Save*`, `send`/`close`, invoice lifecycle) are never auto-retried — duplicate
invoices/waybills have legal consequences.

**SOAP layer (`soap/`, Phase 2):** `client.py` renders a SOAP 1.1 envelope, POSTs `text/xml` with
the `SOAPAction` header, and parses the response; `build.py` serializes request XML
**programmatically from ordered dicts** (hand-written, not zeep — zeep can't type the `<s:any>`
diffgram responses); `parse.py` turns diffgram DataSets into row dicts and scalar responses into
dicts, raising on SOAP faults; `credentials.py` injects the `su`/`sp` service-user into every body;
`services.py` holds per-service endpoints. SOAP tools live in `tools/soap/`. (The plan called for
Jinja2 templates; a programmatic ordered-dict builder proved simpler and more testable for the
many-optional-filter ops while staying fully hand-written.)

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
- MCP server single-invoice lifecycle tools (`rsge_confirm_invoice` / `refuse` / `cancel`) send
  `{"ID": n}`; the exact key is thin in the docs (`GetInvoice` uses `InvoiceID`) — confirm against
  `etest1` during live testing. See the note in `src/rsge_mcp/tools/invoice.py`.
- Real eAPI accounts with SMS 2FA need `RSGE_2FA_MODE=tool` (exposes an `rsge_submit_pin` tool); the
  public test account is 2FA-off, so the default `off` mode is fine for development.
- SOAP request **element order matters** (XSD sequences) and must follow the WSDL — e.g. `su`/`sp`
  come first in WayBillService ops but **last** in ntos ops. SOAP tools build params in WSDL order;
  param names were extracted from `docs/wsdl/*.wsdl`. rs.ge's own field spellings are preserved
  verbatim (e.g. `SELER_UN_ID`, `TRANSPORT_COAST` in the waybill payload) — don't "correct" them.

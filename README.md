# rsge-mcp

An [MCP](https://modelcontextprotocol.io) server for the **rs.ge** (Georgian Revenue Service)
API. It exposes Georgian tax, invoicing, and customs operations as tools an LLM client (Claude
Desktop/Code, MCP Inspector, any MCP host) can call — so you can do rs.ge paperwork
conversationally instead of clicking through the portal or hand-rolling API integrations.

**145 tools across 10 business areas**, bridging both rs.ge API generations (modern REST/JSON
eAPI + the legacy SOAP/`.asmx` services). See **[FEATURES.md](FEATURES.md)** for the full
capability map.

## What it can do

| Area | Examples |
|---|---|
| **Company / taxpayer due diligence** | public profile + risk flags, org info by TIN, VAT-payer status |
| **VAT invoices — modern eAPI** | issue → activate → confirm/refuse/cancel, batches, declarations, excise, barcodes |
| **VAT invoices — legacy ntos** | issue, line items, corrections (credit/debit notes), advance netting, requests |
| **NSAF oil/fuel special invoices** | header + line items, SSD/SSAF sub-docs, transport tracking, accept/refuse |
| **Waybills (ზედნადები)** | create → send → close lifecycle, reference catalogs, party validation, PDF |
| **Duty-free goods journals** | incoming/outgoing goods records, send/receive, reference lookups |
| **Employees · Customs · Z-reports** | employee registry, ASYCUDA declarations, cash-register totals |

> 🔒 **Read-only by default.** Every mutating operation (issue/confirm/cancel invoices,
> create/activate/close waybills, save duty-free records, change status, …) is **refused** unless
> you set `RSGE_ALLOW_WRITES=1`. Reads always work, so it is safe to point at production for lookups
> with no risk of an accidental write. Writes are also never auto-retried.

## Install

Requires **Python 3.12+**.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # editable + dev tooling
# or, once published:  pip install rsge-mcp
```

## Configure

Copy [`.env.example`](.env.example) to `.env` and fill in what you need. With `RSGE_ENV=test`
(the default) and **no credentials supplied**, the server uses the documented **public test
account**, so it runs out of the box on a fresh clone.

Most-used settings (full list + comments in `.env.example`):

| Variable | Purpose |
|---|---|
| `RSGE_ENV` | `test` (default; public test account fallback) or `prod` (credentials required, no fallback) |
| `RSGE_ALLOW_WRITES` | unset = read-only (default); `1` = permit mutating tools |
| `RSGE_EAPI_USERNAME` / `RSGE_EAPI_PASSWORD` | eAPI (REST) bearer-token login |
| `RSGE_2FA_MODE` / `RSGE_PIN` | SMS-OTP handling: `off` / `static_pin` / `tool` |
| `RSGE_SOAP_USER` / `RSGE_SOAP_TIN` / `RSGE_SOAP_PASSWORD` | SOAP service-user (waybills, invoices, duty-free, …) |
| `RSGE_LOG_LEVEL` | stderr log level (`DEBUG` logs every HTTP/SOAP request for diagnostics) |
| `RSGE_DOTENV` | explicit `.env` path (for pipx/uvx installs where the cwd isn't your project) |

**Auth models:** the modern eAPI uses a bearer token (lazy login + caching, optional SMS 2FA); the
legacy SOAP services use a **service-user** you create inside your rs.ge account (passed in each
request body). The two are independent — configure whichever surface you use.

## Run

```bash
rsge-mcp                 # stdio transport;  equivalently:  python -m rsge_mcp
```

### Use from an MCP client

Point any MCP host at that command. For **Claude Desktop**, add to its config
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rsge": {
      "command": "/absolute/path/to/.venv/bin/rsge-mcp",
      "env": {
        "RSGE_ENV": "test"
      }
    }
  }
}
```

Add the credential / `RSGE_ALLOW_WRITES` env vars there as needed. (Use the venv's absolute path,
or `"command": "python", "args": ["-m", "rsge_mcp"]` with the interpreter that has the package
installed.)

## Test environments & verification status

- **eAPI** has no separate test host — its "test mode" runs on production `eapi.rs.ge` with the
  public test account, so writes there stay draft-only.
- **SOAP** test hosts can be targeted with `RSGE_SOAP_BASE` (only scheme+host are swapped; the
  `.asmx` path is kept).
- The eAPI read surface is **production-verified live**. The SOAP **write** tools are **unit-tested
  only** — a live round-trip is gated on a working rs.ge test backend / service-user. They are
  safe-by-design (read-only-by-default, never auto-retried) and locked by per-op request-shape tests.

## Develop

```bash
pytest                                   # unit tests + coverage (gate: ≥80%)
black src tests && ruff check src tests && mypy src
RSGE_RUN_INTEGRATION=1 pytest -m integration   # opt-in live smoke (public test creds)
```

Architecture and contributor notes live in **[CLAUDE.md](CLAUDE.md)**. The repo also ships a
documentation-inventory pipeline (`scripts/`, `endpoints.json`, `SUMMARY.md`) that mines the rs.ge
API docs into a machine-readable inventory — the reference the tools were hand-authored against.

## License

[MIT](LICENSE) © Dimitri Gulua. Not affiliated with or endorsed by the Georgian Revenue Service;
raw rs.ge documents are © Georgian Revenue Service and are not redistributed in this repo.

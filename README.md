# rsge-mcp

An [MCP](https://modelcontextprotocol.io) server for the **rs.ge** (Georgian Revenue
Service) API — exposes tax/customs operations (taxpayer lookups, VAT invoices, waybills,
…) as tools an LLM client can call.

The repo also contains a documentation-inventory pipeline (`scripts/`, `endpoints.json`,
`SUMMARY.md`) that maps the rs.ge API surface; see [`CLAUDE.md`](CLAUDE.md).

## Status

- **Phase 1 (REST / eAPI)** — implemented. Bearer-token auth, taxpayer/org lookups,
  VAT-invoice lifecycle against `eapi.rs.ge` / `xdata.rs.ge`.
- **Phase 2 (SOAP)** — implemented. Waybills (incl. nested save/send/close) and VAT invoices
  (reads + save / line-item / status writes) via the legacy `.asmx` services. **25 tools total.**

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Configure

Copy `.env.example` to `.env` and fill it in. With `RSGE_ENV=test` (the default) and no
credentials supplied, the server falls back to the documented public test account, so it is
runnable on a fresh clone.

## Run

```bash
rsge-mcp            # or: python -m rsge_mcp   (stdio transport)
```

Point an MCP client (Claude Desktop/Code, MCP Inspector) at that command.

## Develop

```bash
pytest                 # unit tests + coverage (≥80%)
black . && ruff check . && mypy src
RSGE_RUN_INTEGRATION=1 pytest -m integration   # opt-in live smoke (test creds)
```

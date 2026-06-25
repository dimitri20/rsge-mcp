# rsge-mcp — Features & Capabilities

This MCP server turns the **Georgian Revenue Service (rs.ge) e-services API** into tools an
AI assistant can call. From any MCP client (Claude Desktop/Code, IDE extensions), you can do
rs.ge tax & logistics paperwork conversationally — *"is this company a VAT payer?"*, *"create a
waybill for this shipment"*, *"list my unconfirmed invoices"* — instead of clicking through the
rs.ge portal or writing API integration code.

It currently exposes **68 tools** across 8 business areas, bridging both rs.ge API generations
(modern REST/JSON eAPI + legacy SOAP/ASMX).

---

## 1. Company & taxpayer due diligence 🔎

Verify and research any Georgian company or person by tax ID — the foundation of onboarding,
KYC, and pre-contract checks.

**What you can do**
- **Look up a taxpayer's public profile** — legal name, registration type (LLC, individual
  entrepreneur, JSC), VAT-payer status, and **risk flags**: property liens/mortgages, asset
  seizures (sequestration), special tax statuses, resident/non-resident. *(No credentials needed.)*
- **Get an organization's details by TIN** — name, address, VAT-payer & diplomat flags, un_id.
- **Confirm VAT-payer status as of a specific date** — essential before issuing/accepting a VAT invoice.

**Business uses:** vendor/customer onboarding, credit-risk screening, counterparty verification.

| Tool | Action |
|---|---|
| `rsge_taxpayer_public_info` | Public taxpayer profile + risk flags (no auth) |
| `rsge_get_org_info_by_tin` | Org name/address/VAT status by TIN |
| `rsge_get_vat_payer_status` | Was this TIN a VAT payer on date X? |

---

## 2. Electronic VAT invoices — modern eAPI 🧾

Issue and manage electronic VAT invoices through the modern JSON API, including the full
buyer/seller approval lifecycle.

**What you can do** — the **full lifecycle**
- **Issue / save** a VAT invoice (line items, VAT & excise); **activate** it (assigns the
  registration number, making it legally binding); **delete** a draft.
- **Fetch** one; **list/search** by date/party/status; **list goods** for several invoices.
- **As a buyer:** confirm or refuse — singly or in **batch**.
- **As a seller:** cancel.
- **Declarations:** allocate a sequence number and **link confirmed invoices to a VAT declaration**.
- **Reference:** excise goods + rates, saved barcodes, status/action codes.

**Business uses:** automate sales invoicing from your ERP/orders, AP/AR reconciliation, bulk
confirm/refuse at period end, VAT-declaration prep.

| Tool | Action |
|---|---|
| `rsge_save_invoice` · `rsge_activate_invoice` · `rsge_activate_invoices` | Create/save · activate (single/batch) |
| `rsge_get_invoice` · `rsge_list_invoices` · `rsge_list_goods` | Fetch · list · full goods detail |
| `rsge_confirm_invoice` / `rsge_refuse_invoice` · `rsge_confirm_invoices` / `rsge_refuse_invoices` | Buyer confirm/refuse (single · batch) |
| `rsge_cancel_invoice` · `rsge_delete_invoice` | Seller cancel · delete draft |
| `rsge_get_seqnum` · `rsge_create_decl` | Declaration number · link invoices |
| `rsge_list_excise` · `rsge_list_barcodes` · `rsge_get_barcode` · `rsge_clear_barcodes` · `rsge_get_actions` | Reference data |

---

## 3. Electronic VAT invoices — legacy ntos service 🧾

The same VAT-invoice domain via the **older SOAP service** that most Georgian accounting
products integrate with — so this MCP works with both API generations.

**What you can do**
- **Save an invoice header**, then **add line items** one at a time.
- **Fetch** an invoice; **list invoices you issued** (seller) or **received** (buyer), with
  date/number/party filters.
- **Change an invoice's status** — saved → sent → confirmed, or delete a draft.

**Business uses:** integrate with legacy accounting workflows, seller/buyer invoice registers.

| Tool | Action |
|---|---|
| `rsge_ntos_save_invoice` | Save invoice header |
| `rsge_ntos_save_invoice_desc` | Add one line item |
| `rsge_ntos_get_invoice` | Fetch one invoice |
| `rsge_ntos_get_seller_invoices` / `rsge_ntos_get_buyer_invoices` | List issued / received |
| `rsge_ntos_change_invoice_status` | Confirm/reject/cancel/delete |
| `rsge_ntos_check_service_user` | Validate your service credentials |

---

## 4. Waybills (ზედნადები) — electronic transport documents 🚚

Waybills are **legally required to move goods within Georgia**. This is the highest-value
automation area, and the MCP covers the complete lifecycle.

**What you can do** — the **full lifecycle + supporting data**
- **Create a draft**, **activate ("send")** (assigns the binding number), **close** on delivery,
  **delete** a draft — plus **send/close with an explicit date** and **cancel** (`ref`).
- **Buyer side:** confirm or reject a waybill.
- **Validate parties before issuing** — name / VAT-payer / payer-type by TIN or un_id.
- **Reference catalogs** to build a *valid* waybill — waybill types, units, transport types,
  wood/timber types, excise (akciz) codes, error codes, saved barcodes & car numbers.
- **Fetch** by id, by number, or as a **printable PDF**; **search** by date/status/buyer/car/driver.
- **Issue a VAT invoice from a waybill**.

**Business uses:** generate transport documents from orders/ERP, complete the buyer/seller flow,
track outstanding vs. delivered shipments, validate counterparties, print/issue downstream docs.

| Tool | Action |
|---|---|
| `rsge_save_waybill` · `rsge_send_waybill` / `rsge_send_waybill_vd` · `rsge_close_waybill` / `rsge_close_waybill_vd` · `rsge_del_waybill` | Create · activate · close · delete (± explicit date) |
| `rsge_confirm_waybill` · `rsge_reject_waybill` · `rsge_ref_waybill` / `rsge_ref_waybill_vd` | Buyer confirm/reject · cancel |
| `rsge_get_waybill` · `rsge_get_waybills` · `rsge_get_waybill_by_number` · `rsge_get_waybill_pdf` | Fetch / search / by number / PDF |
| `rsge_get_waybill_types` · `_units` · `rsge_get_transport_types` · `_wood_types` · `rsge_get_akciz_codes` · `rsge_get_waybill_error_codes` · `rsge_get_bar_codes` · `rsge_get_car_numbers` | Reference catalogs |
| `rsge_get_name_from_tin` · `rsge_is_vat_payer(_tin)` · `rsge_get_tin_from_un_id` · `rsge_get_payer_type_from_un_id` | Party validation |
| `rsge_waybill_to_invoice` · `rsge_waybill_check_service_user` | Issue invoice · validate creds |

---

## 5. Employee registry 👥

Register and manage a taxpayer's employees (eAPI).

**What you can do**
- **Register or update an employee** (Georgian or foreign; full-time/part-time; active/terminated/suspended).
- **Fetch** one employee; **list/search** the registry by TIN, name, status, citizenship, dates.
- **List countries** (reference for foreign employees).

| Tool | Action |
|---|---|
| `rsge_save_employee` | Register/update an employee |
| `rsge_get_employee` · `rsge_list_employees` | Fetch · list/search |
| `rsge_get_countries` | Country reference |

---

## 6. Customs declarations 🛃

Read your ASYCUDA customs declarations (eAPI), for importers/exporters.

**What you can do**
- **Fetch customs declarations** for a date range (≤ 20 days) where your TIN is importer or
  exporter — customs code, regime, registration/assessment numbers, HS code, weights, GEL value,
  goods description, …

| Tool | Action |
|---|---|
| `rsge_get_customs_declarations` | List ASYCUDA declarations for a date range |

---

## 7. Cash-register Z-reports 🧾

Fiscal cash-register totals (SOAP `taxpayerservice`) — for accounting and audit.

**What you can do**
- **Detailed Z-reports** — one row per device per day: receipt count, total, cash vs non-cash, Z number.
- **Aggregate totals** — cash + non-cash across all devices for a period.

| Tool | Action |
|---|---|
| `rsge_get_z_report_details` | Per-device Z-report rows for a date range |
| `rsge_get_z_report_sum` | Aggregate cash / non-cash totals |

---

## 8. Reference data, transactions & session 🔧

Supporting tools the others build on.

| Tool | Action |
|---|---|
| `rsge_get_units` | List measurement units (piece, kg, litre…) for invoices/waybills |
| `rsge_get_transaction_result` | Resolve an async submission by its TransactionId |
| `rsge_signout` | End the eAPI session |
| `rsge_submit_pin` | Submit an SMS 2FA code (only shown when 2FA tool-mode is on) |

---

## What you need to use each area

| Capability | Credentials required |
|---|---|
| **Public taxpayer lookup** | **None** — works out of the box |
| **eAPI** (org lookups, modern VAT invoices) | rs.ge eAPI username/password (+ 2FA if enabled) |
| **SOAP** (waybills, legacy invoices) | a **service user** created inside your rs.ge account (user / TIN / password) |

Auth is handled automatically — lazy bearer-token login, token caching, SMS-PIN support. The
server runs over **stdio** for any MCP client. Configure via env / `.env` (see `.env.example`):
`RSGE_ENV`, `RSGE_EAPI_USERNAME`/`PASSWORD`, `RSGE_SOAP_USER`/`TIN`/`PASSWORD`, and the test-host
overrides `RSGE_SOAP_BASE` / `RSGE_XDATA_BASE`.

> 🔒 **Read-only by default.** Every mutating tool (issue/confirm/cancel invoices,
> create/activate/close/delete waybills, change status) is **refused** unless you set
> `RSGE_ALLOW_WRITES=1`. Reads always work. This makes it safe to point the server at production
> for lookups without any risk of an accidental write.

---

## Maturity / verification status

- ✅ **Production-verified live:** public taxpayer lookups, org info, VAT-payer status, units, the
  entire eAPI bearer-token auth flow, and eAPI reads added since — invoice actions/excise, employee
  registry, customs declarations.
- 🧪 **Built + unit-tested, not yet live-verified:** all **write** actions (issue invoice,
  create/activate waybill, status changes). Safe-by-design — never auto-retried, draft-first. A
  live round-trip is gated on a working rs.ge test host / service-user (the SOAP test backend
  `services-test.rs.ge` is currently faulting on rs.ge's side).

---

## Coverage vs. the full rs.ge API

The rs.ge surface is **287 documented operations** (251 SOAP across 6 services + 36 REST across
7 groups). We've shipped **68 tools** (~64 raw ops, ~22%) — but that **understates** real coverage:
the shipped tools deliver **~55–60% of business value**, because they now complete the two
highest-traffic domains end-to-end (the full modern VAT-invoice lifecycle and the waybill workflow
incl. reference + party validation), plus employee registry, customs reads, cash-register Z-reports,
and company/TIN due diligence. The remaining gap is mostly whole new domains (NSAF fuel invoices,
duty-free) and low-value long-tails (diagnostics, portal-only helpers).

| Surface | Implemented | Total |
|---|---|---|
| REST / eAPI | ~26 | 36 |
| SOAP — waybill | 29 | 56 |
| SOAP — ntos (VAT) | 7 | 54 |
| SOAP — taxpayer (Z-reports) | 2 | 20 |
| SOAP — NSAF / duty-free / parcels | 0 | 121 |

> **The honest target is ~95% *business-value* coverage (≈150–170 ops), not 100% raw-op parity.**
> The long tail is deprecated forms, portal-only helpers, headless-impossible SMS/OTP flows, and
> niche carrier/customs-seal workflows — wrapping them adds maintenance surface for near-zero value.

## Roadmap to (near-)complete coverage

| Phase | Scope | New tools | Value | Effort |
|---|---|---|:--:|:--:|
| ✅ **P0** | **Safety guardrails (blocker)** — read-only by default + `RSGE_ALLOW_WRITES` opt-in gating every mutating op; per-service SOAP test-host table; HTTP 429 backoff. **Shipped.** | 0 (infra) | High | Med |
| ✅ **P1** | Finish the **modern eAPI invoice** state machine (activate/delete/batch confirm-refuse/declarations/excise/barcodes → 19/19). **Shipped (+13).** | ~13 | High | Low |
| ✅ **P2** | **eAPI Employees** (registry CRUD) + **Customs** declarations + cash-register **Z-reports**. **Shipped (+7).** | ~7 | High | Low |
| ✅ **P3** | **Waybill** long-tail — reference catalogs (valid payloads), lifecycle completers (confirm/reject/cancel + send/close-with-date), identity helpers, by-number/PDF reads, waybill→invoice (→ 29/56). **Shipped (+22).** | ~22 | High | Med |
| **P3b** | **Waybill** role-based + goods-list reads (`get_buyer_waybills`, `get_waybill_goods_list`, transporter views) with an order-preserving filter helper | ~6 | Med | Low |
| **P4** | **ntos invoice** long-tail — advance/prepayment netting, corrections (credit/debit notes), accept/refuse, identity glue (un_id↔TIN) | ~18 | High | High |
| **P5** | **NSAF oil/fuel special invoices** (new domain — every petroleum wholesaler) | ~28 | High | High |
| **P6** | **Duty-Free** goods journals (new — high value but only for licensed free-trade operators) | ~26 | Med | High |
| **P7** | Income / taxpayer-profile / comparison-acts + personal income (some need an SMS OTP → human-in-the-loop) | ~12 | Med | Med |
| **P8** | Cosmetic long-tail + OAuth delegation — *only if literal 100% is contractually required* (drive via WSDL codegen, don't hand-author) | ~80+ | Low | High |

**"Complete" = P0–P5 (+ the documented half of P7) ≈ 150–170 ops ≈ ~95% of business value.**

### Cross-cutting prerequisites
- **Write guardrails (P0)** — there is currently *no* read-only/allow-write gate; `RSGE_ENV=test`
  only swaps in the test account, it doesn't stop a write hitting production. Must land first.
- **A working test host + service-user** — the 6 SOAP services span 4 production hosts, so the
  single `RSGE_SOAP_BASE` override can't route them all; a per-service test-endpoint table is needed
  (and rs.ge's `services-test.rs.ge` backend is currently down).
- **WSDL-driven codegen for the thin long-tail** — don't hand-author ~260 wrappers; generate the
  one-id lifecycle/lookup calls from the WSDLs, reserving hand-written Pydantic models for the heavy
  stateful payloads (sub-waybills, advance/correction invoices, NSAF `save_invoice_b_n`, duty-free forms).
- **429 backoff + identity (TIN↔un_id) layer + REST/SOAP dedup** — shared infra for the write phases.

### Out of scope for an HTTP MCP
SAM smartcard fiscal-device module (hardware/APDU), the Windows desktop apps, the OAuth browser
login popup (belongs in a frontend), deprecated duty-free `form4_*`/`form5_*`, portal-only waybill
templates, fully-headless SMS/OTP flows, the niche cargo-carrier customs-seal flow, and pure
diagnostics (`what_is_my_ip`, `get_server_time`).

### Recommended sequence
**P0 immediately** (it's a correctness/safety fix, not a feature), then **P1 → P2 → P3 → P4** to
finish the started domains and bank the high-ROI REST wins, then **P5** for the fuel sector. Gate
**P6** on whether your users serve the duty-free niche. Treat ~150–170 ops as "done" and call that
complete — and invest what you'd spend on P8's cosmetic wrappers into the WSDL codegen path so the
long tail becomes cheap to generate on demand rather than a hand-maintained liability.

# rsge-mcp — Features & Capabilities

This MCP server turns the **Georgian Revenue Service (rs.ge) e-services API** into tools an
AI assistant can call. From any MCP client (Claude Desktop/Code, IDE extensions), you can do
rs.ge tax & logistics paperwork conversationally — *"is this company a VAT payer?"*, *"create a
waybill for this shipment"*, *"list my unconfirmed invoices"* — instead of clicking through the
rs.ge portal or writing API integration code.

It currently exposes **147 tools** across 10 business areas, bridging both rs.ge API generations
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
products integrate with — now with the full accounting workflow, so this MCP works with both
API generations end-to-end.

**What you can do**
- **Issue** an invoice header (+ note variant), **add / read / delete line items**.
- **Correct** an invoice (credit/debit notes) and **cancel** it.
- **Buyer side:** accept or refuse a received invoice. **Seller side:** change status.
- **Advance / prepayment netting:** issue an advance invoice, find attachable advances,
  **attach / update / detach** them to net prepayments against a delivery invoice.
- **Invoice requests:** buyer asks a seller to issue an invoice; seller lists & accepts; buyer withdraws.
- **Fetch / list** issued (seller) or received (buyer) invoices with date/number/party filters.
- **Identity glue:** resolve TIN ↔ `un_id`, your own `un_id`, and an org's name from `un_id`.

**Business uses:** integrate with legacy accounting workflows, prepayment/advance accounting,
credit/debit-note corrections, seller/buyer invoice registers and request flows.

| Tool | Action |
|---|---|
| `rsge_ntos_save_invoice` · `rsge_ntos_save_invoice_a` · `rsge_ntos_save_invoice_n` | Issue invoice · advance invoice · with note |
| `rsge_ntos_save_invoice_desc` · `rsge_ntos_get_invoice_desc` · `rsge_ntos_delete_invoice_desc` | Line items (add · read · delete) |
| `rsge_ntos_correct_invoice` · `rsge_ntos_cancel_invoice` | Correction (credit/debit note) · cancel |
| `rsge_ntos_change_invoice_status` · `rsge_ntos_accept_invoice_status` · `rsge_ntos_refuse_invoice_status` | Seller status · buyer accept / refuse |
| `rsge_ntos_get_attachable_advance_invoices` · `rsge_ntos_attach_advance_invoice` · `rsge_ntos_get_attached_advance_invoices` · `rsge_ntos_update_advance_invoice` · `rsge_ntos_detach_advance_invoices` | Advance/prepayment netting |
| `rsge_ntos_save_invoice_request` · `rsge_ntos_get_invoice_request(s)` · `rsge_ntos_get_requested_invoices` · `rsge_ntos_accept_invoice_request` · `rsge_ntos_del_invoice_request` | Invoice-request lifecycle |
| `rsge_ntos_get_invoice` · `rsge_ntos_get_seller_invoices` / `rsge_ntos_get_buyer_invoices` | Fetch · list issued / received |
| `rsge_ntos_get_un_id_from_tin` · `rsge_ntos_get_un_id_from_user_id` · `rsge_ntos_get_org_name_from_un_id` | Identity resolution |
| `rsge_ntos_check_service_user` | Validate your service credentials |

---

## 4. NSAF special (oil/fuel) invoices ⛽

Special invoices for the **petroleum/fuel sector** (NSAF — ნავთობპროდუქტების სპეციალური
ანგარიშ-ფაქტურა) via the dedicated `SpecInvoicesService` — the full lifecycle with fuel-specific
transport tracking and customs/excise sub-documents.

**What you can do**
- **Issue** a special invoice (the oil/transport header) and add / read / delete **line items**.
- Attach **SSD (customs)** and **SSAF (excise)** sub-documents.
- Run the **transport flow** — start transport, correct driver/vehicle in transit.
- **Buyer** accept/refuse; **seller** status; **correct** (credit/debit note) and **cancel**.
- **Advance/prepayment netting**; buyer↔seller **invoice requests**.
- **Lookups** — oil/fuel products (for line items), org facilities (load/unload points), seller/buyer
  invoice registers, printable form.

**Business uses:** petroleum wholesale/retail invoicing, fuel transport documentation, excise/customs
sub-document management.

| Tool | Action |
|---|---|
| `rsge_spec_save_invoice` · `rsge_spec_save_line_item` / `rsge_spec_get_line_items` / `rsge_spec_delete_line_item` | Issue header · line items |
| `rsge_spec_add_ssd` / `rsge_spec_add_ssaf` · `rsge_spec_get_ssds` / `rsge_spec_get_ssafs` · `rsge_spec_delete_ssd` / `rsge_spec_delete_ssaf` | SSD/SSAF sub-documents |
| `rsge_spec_start_transport` · `rsge_spec_correct_driver_info` · `rsge_spec_correct_transport_mark` | Transport flow |
| `rsge_spec_change_status` · `rsge_spec_accept_status` / `rsge_spec_refuse_status` · `rsge_spec_correct_invoice` · `rsge_spec_cancel_reason` | Status · correct · cancel |
| `rsge_spec_attach_advance` / `rsge_spec_update_advance` / `rsge_spec_detach_advance` · `rsge_spec_get_attached_advances` / `rsge_spec_get_attachable_advances` | Advance netting |
| `rsge_spec_get_invoice` · `rsge_spec_get_seller_invoices` / `rsge_spec_get_buyer_invoices` · `rsge_spec_print_invoice` | Reads |
| `rsge_spec_get_products` / `rsge_spec_get_product` · `rsge_spec_get_org_objects` / `rsge_spec_get_my_org_objects` | Lookups |
| `rsge_spec_save_invoice_request` · `rsge_spec_get_correction` · `rsge_spec_check_users` | Request · correction check · creds |

---

## 5. Waybills (ზედნადები) — electronic transport documents 🚚

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

## 6. Employee registry 👥

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

## 7. Customs declarations 🛃

Read your ASYCUDA customs declarations (eAPI), for importers/exporters.

**What you can do**
- **Fetch customs declarations** for a date range (≤ 20 days) where your TIN is importer or
  exporter — customs code, regime, registration/assessment numbers, HS code, weights, GEL value,
  goods description, …

| Tool | Action |
|---|---|
| `rsge_get_customs_declarations` | List ASYCUDA declarations for a date range |

---

## 8. Cash-register Z-reports 🧾

Fiscal cash-register totals (SOAP `taxpayerservice`) — for accounting and audit.

**What you can do**
- **Detailed Z-reports** — one row per device per day: receipt count, total, cash vs non-cash, Z number.
- **Aggregate totals** — cash + non-cash across all devices for a period.

| Tool | Action |
|---|---|
| `rsge_get_z_report_details` | Per-device Z-report rows for a date range |
| `rsge_get_z_report_sum` | Aggregate cash / non-cash totals |

---

## 9. Duty-free goods journals 🛍️

Goods journals for licensed **duty-free** shops/warehouses (free-trade operators), via `wsdutyfree`.

**What you can do**
- **Incoming journal (FormGoodsIn):** record goods entering the point, edit, **send** to rs.ge,
  confirm receipt, reject, or delete.
- **Outgoing journal (FormGoodsOut):** record goods sold to travellers (passport / air-ticket) or
  transferred to another point, edit, send, delete.
- **Reference:** unit types, point codes, goods statuses, and per-journal operation types.

**Business uses:** duty-free inventory in/out reporting, traveller-sale documentation, point transfers.

| Tool | Action |
|---|---|
| `rsge_df_save_goods_in` · `rsge_df_update_goods_in` · `rsge_df_send_goods_in` · `rsge_df_send_receive_goods_in` / `rsge_df_update_receive_goods_in` · `rsge_df_reject_goods_in` · `rsge_df_delete_goods_in` | Incoming journal lifecycle |
| `rsge_df_save_goods_out` · `rsge_df_update_goods_out` · `rsge_df_send_goods_out` · `rsge_df_delete_goods_out` | Outgoing journal lifecycle |
| `rsge_df_get_goods_in` / `rsge_df_list_goods_in` · `rsge_df_get_goods_out` / `rsge_df_list_goods_out` | Fetch / list |
| `rsge_df_get_units` · `rsge_df_get_point_codes` · `rsge_df_get_goods_statuses` · `rsge_df_get_goods_in_operations` / `rsge_df_get_goods_out_operations` | Reference lookups |

---

## 10. Reference data, transactions & session 🔧

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

The rs.ge surface is **289 documented operations** (253 SOAP across 6 services + 36 REST across
7 groups). We've shipped **147 tools** (~140 raw ops, ~49%) — but that **understates** real coverage:
the shipped tools deliver **~85% of business value**, because **all five SOAP record-domains plus the
modern eAPI invoice flow are now wired end-to-end** — the modern eAPI VAT-invoice lifecycle, the
waybill workflow, the legacy ntos VAT-invoice flows, the NSAF oil/fuel special invoices, and the
duty-free goods journals — plus employee registry, customs reads, cash-register Z-reports, and
company/TIN due diligence. **No new domains remain**; the gap is now intra-domain long-tails
(batch/Oil variants, deprecated forms, diagnostics) and the income/taxpayer-profile group.

| Surface | Implemented | Total |
|---|---|---|
| REST / eAPI | ~26 | 36 |
| SOAP — waybill | 29 | 56 |
| SOAP — ntos (VAT) | 30 | 55 |
| SOAP — specinvoices (NSAF fuel) | 35 | 46 |
| SOAP — dutyfree | 20 | 72 |
| SOAP — taxpayer (income / Z-reports) | 2 | 20 |
| SOAP — custompost (parcels) | 0 | 4 |

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
| ✅ **P4** | **ntos invoice** long-tail — advance/prepayment netting, corrections (credit/debit notes) + cancel, buyer accept/refuse, line items, invoice-request flow, identity glue (→ 29/54). **Shipped (+22).** | ~22 | High | High |
| ✅ **P5** | **NSAF oil/fuel special invoices** (new domain) — issue header + line items, SSD/SSAF sub-docs, transport flow, accept/refuse, correction/cancel, advance netting, lookups (→ 34/45). **Shipped (+34).** | ~34 | High | High |
| ✅ **P6** | **Duty-Free** goods journals (new domain) — FormGoodsIn/FormGoodsOut lifecycles (save/send/receive/reject/delete) + reference lookups (→ 20/72; List/Oil/barcode variants deferred). **Shipped (+20).** | ~20 | Med | High |
| **P7** | Income / taxpayer-profile / comparison-acts + personal income (some need an SMS OTP → human-in-the-loop) | ~12 | Med | Med |
| **P8** | Cosmetic long-tail + OAuth delegation — *only if literal 100% is contractually required* (drive via WSDL codegen, don't hand-author) | ~80+ | Low | High |

**P0–P6 are shipped (147 tools, ~85% of business value). All new domains are now covered** — what
remains is "harden & ship" (end-user README + publish + live verification), the small **P3b** waybill
reads, and the **P7** income/taxpayer-profile group; **P8** (cosmetic + OAuth) stays out of scope.

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

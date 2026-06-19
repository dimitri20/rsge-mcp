# rs.ge (Georgian Revenue Service) API — Documentation Summary

> Source: <https://eservices.rs.ge/app/Downloads> ("სერვისების დოკუმენტაცია" / "Services documentation").
> Support contact listed on the page: **api-support@rs.ge**.
> All 18 documents + 6 Postman collections were downloaded and parsed; see [`docs/`](docs/).
> Generated 2026-06-19.

---

## 1. What this is

**rs.ge** is the e-services portal of the **Georgian Revenue Service** (შემოსავლების სამსახური,
part of the Ministry of Finance). It exposes a set of machine-to-machine APIs that let accounting
software, ERPs, and integrators automate Georgian tax/customs paperwork: **waybills, VAT invoices,
employee registration, customs/duty-free declarations, taxpayer lookups, income data**, and more.

The "Downloads" page is the **only public API catalog**. It is a JavaScript SPA — the file list and
the files themselves are served by a backend API (`https://eapi.rs.ge/Downloads/*`). Each entry is a
**protocol document** (PDF or HTML) and, for the newer services, a **Postman collection** with working
example requests.

### How the docs are served (reverse-engineered — useful for keeping docs in sync)

| Purpose | Call |
|---|---|
| List all docs | `POST https://eapi.rs.ge/Downloads/GetProtocols` (empty body) → `{DATA:[…], STATUS}` |
| Download a doc | `POST https://eapi.rs.ge/Downloads/GetProtocolFile?fileName=<DocName>&id=<ID>` |
| Download a Postman collection | `POST https://eapi.rs.ge/Downloads/GetPostmanFile?fileName=postman.json&id=<ID>` |

No authentication is needed to download documentation. Re-fetch anytime with
[`scripts/fetch_docs.py`](scripts/fetch_docs.py).

---

## 2. The big picture: two API generations

The RS API surface evolved over ~15 years and splits into two clearly different styles:

### A. Legacy **SOAP / `.asmx`** web services (XML)
The bulk of the functionality. One ASMX endpoint per domain, many operations each (`?op=Name`).
Auth is via a **service user** (a sub-user you create inside your rs.ge account) — username/password
passed in the SOAP body (`su`, `sp` / `user_id`). These are the most widely-used integrations in
Georgia (every accounting product talks to WayBillService and ntosservice).

### B. Modern **REST / JSON** services (`eapi.rs.ge`, `xdata.rs.ge`)
Newer services (Tax Document/eAPI, Employee registry, Customs, Taxpayer public info). Clean JSON,
**bearer-token** auth: call `Users/Authenticate` once → get an access token (API key) → send
`Authorization: bearer {ACCESS_TOKEN}` on every request. Uniform response envelope:
`{ "DATA": …, "STATUS": { "ID": 0, "TEXT": "…" } }`. The customs doc even ships an **OpenAPI spec**
(Redocly-generated HTML).

> **Environments:** production is `eapi.rs.ge` / `services.rs.ge`; the SPA bundle also references a
> test host `etest1.rs.ge`. The SOAP services expose `?WSDL` for machine-readable contracts.

---

## 3. How many endpoints?

Counting the **authoritative** sources (SOAP `?WSDL` operation lists + the REST docs), **not** just the
Postman samples:

| Transport | Services / groups | Operations / endpoints |
|---|---|---|
| **SOAP (`.asmx`)** | 6 services | **251 operations** |
| **REST/JSON** (`eapi.rs.ge`, `xdata.rs.ge`, OAuth) | 7 groups | **36 endpoints** |
| **Total documented** | 13 | **≈ 287** |

SOAP breakdown (from each service's WSDL):

| Service | Endpoint | Ops |
|---|---|---:|
| WayBillService | `services.rs.ge/WayBillService/WayBillService.asmx` | 56 |
| ntosservice (VAT invoices) | `www.revenue.mof.ge/ntosservice/ntosservice.asmx` | 54 |
| SpecInvoicesService (NSAF) | `webserv.rs.ge/specinvoices/SpecInvoicesService.asmx` | 45 |
| wsdutyfree (Duty-Free) | `webserv.rs.ge/dutyfree/wsdutyfree.asmx` | 72 |
| taxpayerservice (income / Z-reports / info) | `services.rs.ge/taxservice/taxpayerservice.asmx` | 20 |
| custompostservice (parcels / cargo) | `services.rs.ge/taxservice/custompostservice.asmx` | 4 |

> The 6 **Postman collections** ship **78 sample requests** total — these are a *subset* (working
> examples) of the full operation lists above. Full per-service operation lists are in
> [`endpoints.json`](endpoints.json).

---

## 4. Authentication models (4 of them)

1. **SOAP service-user** — create a "service user" (სერვისის მომხმარებელი) in your RS account; pass its
   credentials in each SOAP call. Used by Waybill / ntos / SpecInvoices / Duty-Free / taxpayer / parcels.
2. **eAPI bearer token** — `POST eapi.rs.ge/Users/Authenticate` (or `AuthenticatePin`) → token; send
   `Authorization: bearer {token}`; `Users/SignOut` to end. Used by Invoice/Employees/Customs (eAPI).
3. **Two-step (SMS) authorization** (doc id 12) — OTP-based second factor (`Tp_sms_verification`,
   `Gita_Sms_Verification` on taxpayerservice / xdata `SmsVerification`).
4. **Open Authorization / OAuth** (doc id 13, `RSoAuth.html`) — delegated auth via
   `eservices.rs.ge/WebServices/oAuth.ashx`, for letting third-party apps act on a taxpayer's behalf.

---

## 5. Service catalog (all 18 documented items)

Legend — **Transport**: SOAP / REST / Other. **PM** = Postman collection shipped.

| # | Service (GE → EN) | Doc | Transport | Endpoint | PM |
|--|--|--|--|--|:--:|
| 1 | ზედნადები → **Waybills** | waybill_protocol.pdf | SOAP | WayBillService.asmx (56 ops) | ✅ |
| 2 | ანგარიშ-ფაქტურა → **VAT invoices** | invoice-protocol.pdf | SOAP | ntosservice.asmx (54 ops) | ✅ |
| 3 | ნსაფ → **NSAF special invoices** | NSAF_PROTOKOL.pdf | SOAP | SpecInvoicesService.asmx (45 ops) | ✅ |
| 4 | საფოსტო გზავნილები → **Postal parcels** | ParcelProtocol.pdf | SOAP | custompostservice.asmx (4 ops) | — |
| 5 | **Duty-Free** | dutyfree_protocol.pdf | SOAP | wsdutyfree.asmx (72 ops) | — |
| 6 | ტვირთების გადაზიდვა → **Cargo** | Cargo-Delivery.pdf | SOAP | custompostservice.asmx (shared) | — |
| 7 | ნსაფ ელ. ჟურნალები → **NSAF e-journals guide** | ejournal-protocol.pdf | Guide | (NSAF desktop app) | — |
| 8 | **SAM module** | SAM-Module-Protocol.pdf | Hardware | ISO 7816-4 APDU over TCP/IP (fiscal device, **not an HTTP API**) | — |
| 9 | **Duty-Free guide** | duti-free.pdf | Guide | (companion to #5) | — |
| 10 | სალარო აპარატ. დღის ჯამური → **Cash-register Z-report totals** | ITC…SALAROAPARATEBI…pdf | SOAP | taxpayerservice.asmx `Get_Z_Report_*` | — |
| 11 | ერთობლივი შემოსავალი → **Aggregate income** | ITC…ERTOBLIVI…pdf | SOAP | taxpayerservice.asmx `Get_Income_Amount` | — |
| 12 | ორბიჯიანი (SMS) ავტორიზაცია → **2-step SMS auth** | 2_step_auth.pdf | Auth | SMS OTP mechanism | — |
| 13 | ღია ავტორიზაცია → **Open auth / OAuth** | RSoAuth.html | Auth | eservices.rs.ge/WebServices/oAuth.ashx | — |
| 14 | ფ/პ შემოსავლები → **Individual income** | ITC…F.P_SHEOSAVLEBI…pdf | SOAP | taxpayerservice.asmx `GetPersonIncomeData` | — |
| 15 | საგადასახადო დოკუმენტი → **Tax Document (eAPI)** | eAPI_RS.pdf | REST | eapi.rs.ge `Invoice/*`, `Org/*`, `Common/*` (~19 ops) | ✅ |
| 16 | დაქირავებულ პირთა რეესტრი → **Employee registry** | Employee_API 1.0.1.pdf | REST | eapi.rs.ge/Employees (4 ops) | ✅ |
| 17 | გადამხდელის საჯარო ინფ. → **Taxpayer public info** | TaxPayerPublicInfoDoc_v2.html | REST | xdata.rs.ge/TaxPayer (RSPublicInfo …) | ✅ |
| 18 | საბაჟო დეკლარაციები → **Customs declarations** | CustomsDeclarations_v1.html | REST | eapi.rs.ge/CustomsDeclarations (OpenAPI) | — |

(Items 1, 3, 5 and the NSAF app also reference Windows **desktop applications** via `AppUrl` in the
manifest — noted, not part of the API.)

---

## 6. What you can actually do with it

Grouped by domain:

- **Waybills (ზედნადები)** — the electronic goods-transport document. Create/save/send/close/confirm/
  reject waybills (incl. sub-waybills, corrections, transporter waybills), print to PDF, list your /
  buyer / transporter waybills, look up TIN→name, excise (akciz) codes, transport types, units, bar codes.
- **VAT invoices (ანგარიშ-ფაქტურა)** — issue/save/correct VAT invoices, change status (confirm/reject/
  cancel), list seller/buyer invoices, manage advance invoices and declarations, sequence numbers,
  invoice requests, ID↔TIN↔un_id lookups.
- **NSAF special invoices (ნსაფ)** — special (e.g. fuel/excise) invoice issuance & lifecycle, product
  catalogs, SSAF/SSD forms, transport marks, driver info.
- **Tax Document / eAPI (modern)** — the REST re-implementation of invoicing: `SaveInvoice`,
  Activate/Confirm/Cancel/Refuse, `ListInvoices`, excise & barcode lists, `CreateDecl`, plus org lookup
  (`Org/GetVatPayerStatus`, `Org/GetOrgInfoByTin`) and units/transaction-result helpers.
- **Employee registry** — register/update employees, list them, get an employee, country reference list.
- **Customs declarations** — read ASYCUDA customs-declaration data (`GetAsycudaDeclarations`).
- **Duty-Free** — manage in/out goods forms (incl. oil/fuel variants), balances, barcodes, point/unit refs.
- **Postal parcels & cargo** — declaration numbers and ASYCUDA post declarations for shipments.
- **Taxpayer info & income** — public taxpayer info, person/legal income data, income amounts,
  cash-register **Z-report** sums/details, comparison acts, NACE/activity info, payer activation.
- **Auth/identity** — service users, bearer tokens, 2-step SMS verification, OAuth delegation.

---

## 7. Implications for the MCP build (next step)

The "create an rs.ge MCP" goal will need to bridge **two transports**:

- **Easy wins first — the REST/JSON eAPI** (`eapi.rs.ge`): Tax Document/Invoice, Employees, Customs,
  plus taxpayer public info (`xdata.rs.ge`). JSON in/out, single bearer-token auth, uniform `{DATA,STATUS}`
  envelope, and customs even has an OpenAPI spec → these map almost 1:1 to MCP tools with little glue.
- **High-value but heavier — the SOAP services** (Waybill, ntos, NSAF, Duty-Free, taxpayer): need a
  SOAP/XML client and per-call service-user credentials. Waybill + ntos are the most-requested in
  practice. The WSDLs in [`docs/wsdl/`](docs/wsdl/) are the machine-readable contracts to generate from.
- **Out of scope for an HTTP MCP:** SAM module (#8, smartcard hardware protocol) and the desktop apps.

**Open questions to resolve before building:** which auth credentials the user will supply (service user
vs eAPI login), prod vs `etest1.rs.ge` test environment, and rate-limit / fair-use expectations (these
are live government endpoints).

---

## 8. Files in this repo

```
docs/
  manifest.json            raw GetProtocols response (18 entries)
  download_report.json     per-file download status + magic-byte validation (24 files, 0 errors)
  extract_report.json      text-extraction status per doc (all 18 extracted; none scanned)
  protocols/               18 original PDF/HTML documents (ID-prefixed)
  postman/                 6 Postman collections (ids 1,2,3,15,16,17)
  wsdl/                    6 SOAP WSDLs (waybill, ntos, specinvoices, dutyfree, taxpayer, custompost)
  text/                    plain-text extraction of every doc (greppable, Georgian preserved)
endpoints.json             unified machine-readable inventory (SOAP ops + REST endpoints + Postman)
scripts/                   fetch_docs.py · fetch_wsdl.py · parse_docs.py · build_inventory.py
SUMMARY.md                 this file
```

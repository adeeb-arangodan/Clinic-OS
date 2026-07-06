# 02 — Architecture Document
## SehaERP — Django + React + PostgreSQL, multi-tenant SaaS with single-tenant deploy profile

---

## 1. System context

```
                         ┌──────────────────────────────────────────────┐
                         │                 SehaERP SaaS                 │
 Browser (Reception,     │  ┌─────────┐   ┌───────────────────────────┐ │      ┌─────────────┐
 Doctor, Lab, Pharmacy,  │  │ React   │   │ Django API (DRF)          │ │◄────►│ Nphies GW   │ FHIR R4
 Owner)  ───────────────►│  │ SPA     │──►│  domain services          │ │      ├─────────────┤
                         │  └─────────┘   │  + Channels (ws queues)   │ │◄────►│ ZATCA       │ UBL XML
 Waiting-room display ──►│                └─────────┬─────────────────┘ │      ├─────────────┤
 Label/receipt printers  │        Celery workers ◄──┤    Redis (queue,  │◄────►│ SFDA RSD    │ GS1 events
 (browser print / QZ)    │        (integration jobs)│    cache, ws)     │      ├─────────────┤
                         │                          ▼                   │◄────►│ SMS/WhatsApp│
 Modalities/PACS ◄──DICOM MWL──  interface svc   PostgreSQL 16          │      ├─────────────┤
                         │        (pynetdicom)  + S3-compatible objects │◄────►│ Payment/mada│ (S)
                         └──────────────────────────────────────────────┘      └─────────────┘
```

## 2. Tenancy model (key decision)

**Decision: shared database, shared schema, `tenant_id` on every row, enforced by PostgreSQL Row-Level Security (RLS) + application-layer scoping.**

Rationale:
- One migration path for hundreds of tenants (schema-per-tenant/django-tenants makes migrations and cross-tenant vendor analytics painful at scale).
- RLS gives DB-level defense-in-depth: even a buggy query cannot leak across tenants.
- Single-tenant on-prem = same schema with exactly one tenant row; zero code divergence.

Implementation rules:
- `Tenant`, `Branch` tables; abstract base model `TenantModel(tenant_id FK, branch_id FK nullable)`; **every** domain table inherits it.
- Middleware resolves tenant from subdomain (`{tenant}.sehaerp.sa`) or JWT claim; sets `SET LOCAL app.tenant_id` per request/transaction; RLS policies filter on it. Celery tasks receive `tenant_id` explicitly and set it the same way.
- Platform-admin access uses a separate DB role bypassing RLS, gated + audited.
- Unique constraints are always composite with `tenant_id` (e.g., MRN, invoice number sequences per tenant+branch via dedicated counter table with `SELECT ... FOR UPDATE`).
- Per-tenant entitlements cached (Redis) and enforced by a DRF permission class `RequiresEntitlement("nphies")` + frontend feature-flag context.

## 3. Backend structure (Django monolith, modular apps)

Monorepo layout:
```
/backend
  /config            settings (base/dev/saas/onprem), asgi, celery
  /core              tenancy, auth, RBAC, audit, i18n, numbering, notifications, entitlements
  /patients          registry, insurance profiles, documents, merge
  /scheduling        doctors' schedules, appointments, queues (Channels)
  /encounters        visits, vitals, clinical notes, sign-off        (EMR core)
  /orders            unified clinical order model (lab/rad/procedure)
  /billing           catalog, price lists, charges, invoices, payments, day-end
  /insurance         payers, contracts, eligibility, approvals, claims, recon, rejections
  /pharmacy          formulary, dispensing, POS
  /inventory         stores, batches, ledger, procurement
  /lab               catalog, samples, results, validation
  /radiology         studies, worklist, reports
  /dental            tooth chart, treatment plans (EMR specialty plugin pattern)
  /reports           query layer + saved reports + dashboard endpoints
  /integrations
     /nphies         FHIR builders/parsers, client, message log, state machines
     /zatca          UBL builder, signer, client, onboarding
     /rsd            GS1 parsing, event reporter
     /dicom          MWL SCP service (runs as separate process)
     /messaging      SMS/WhatsApp/email adapters
/frontend            React app (see §5)
/deploy              docker-compose (dev, onprem), k8s manifests (saas), backup CLI
/docs                these documents + ADRs
```

Architectural rules:
- **Service layer:** each app exposes `services.py` (commands) and `selectors.py` (queries). Views/serializers never contain business logic. Cross-app calls go through services, not model imports of another app's internals.
- **Domain events:** lightweight in-process event bus (`order.finalized`, `invoice.finalized`, `claim.rejected`, `result.validated`) — apps subscribe (e.g., billing listens to orders; notifications listen to results). Events also enqueue Celery jobs for integrations. This is the seam where AI agents attach later.
- **State machines:** explicit status enums + guarded transition functions for Encounter, Order, Invoice, Approval, Claim, Sample, Study, DispenseTask. Illegal transitions raise; every transition audit-logged.
- **Immutability:** finalized invoices/claims/reports never updated; amendments create linked records (`replaces_id`).
- **API:** DRF + OpenAPI schema (drf-spectacular) → generated TypeScript client. URL shape `/api/v1/{app}/...`. Cursor pagination on large tables; consistent error envelope `{code, message_en, message_ar, field_errors}`.
- **Async:** Celery queues: `integrations` (Nphies/ZATCA/RSD, with per-integration rate limits), `notifications`, `reports` (heavy exports), `default`. All tasks idempotent via `dedup_key`. Task outcomes written to an `IntegrationTransaction` table powering UI status chips and the poison-message worklist.
- **Websockets:** Channels groups per `tenant:branch:queue:{department}` for live token boards; per `tenant:user` for personal alerts (critical lab value, claim response).

## 4. Data platform

- PostgreSQL 16. Conventions: UUID PKs; `created_at/updated_at/created_by`; soft-delete only where clinically safe (`is_active`) — transactional records are never deleted.
- Column encryption (pgcrypto or app-layer) for national ID numbers; documents in S3-compatible storage with tenant-prefixed keys + signed URLs.
- Big tables (`nphies_message_log`, `audit_log`, `stock_ledger`) partitioned by month from day one.
- Reporting reads from the same DB in v1 via optimized selectors + a few materialized views (`mv_daily_revenue`, `mv_claim_aging`) refreshed by Celery beat; read-replica planned when tenant count grows (no code change — DB router ready).
- Full-text search: Postgres `tsvector` for patients (name/ID/mobile) and ICD/drug/service catalogs with trigram fallback for misspellings.

## 5. Frontend architecture

- React 19 (ADR-0001) + TypeScript + Vite. Feature-folder structure mirroring backend apps (`/features/reception`, `/features/emr`…).
- **Server state:** TanStack Query only (no Redux); websocket messages invalidate/patch query caches (e.g., queue updates).
- **Forms:** react-hook-form + zod schemas generated/kept in sync with API types.
- **Design system:** Tailwind + shadcn/ui wrapped in `/ui` package with SehaERP tokens (see 03-DESIGN.md §5); every component RTL-tested; i18next with `ar` default for Saudi tenants; number/date formatting via Intl with Hijri secondary display component `<DualDate/>`.
- **Role-based shells:** after login, users land on a role home (Reception board, Doctor list, Cashier, Lab bench, Pharmacy queue, Owner dashboard). Navigation is role-scoped; entitlement flags hide locked modules with a tasteful "upgrade" state.
- **Printing:** HTML print stylesheets for A4 documents (invoice, Rx, lab report, UCAF) and 80mm receipts + label printer templates; QZ Tray integration optional for silent printing (S).
- **Offline posture:** not offline-first, but reception/cashier screens keep last-loaded data visible with a connectivity banner; queued mutations are NOT attempted (avoid clinical risk) — clear retry UX instead.

## 6. Integration adapters (the critical pattern)

Every external system implements an interface + at least two impls: `Real` and `Mock` (deterministic, used in dev/demo/CI). Selected per tenant+environment via config.

### 6.1 Nphies (`integrations/nphies`)
- FHIR R4.0.1 messaging per the CHI Financial Services IG: request/response **Bundles** with `MessageHeader` event codes; synchronous request-response plus **polling** for deferred responses.
- Components: `FhirBundleBuilder` (eligibility, priorauth, claim, payment-recon poll, communication), `FhirParser`, `NphiesClient` (mTLS with tenant PKI cert, retries, correlation IDs), `MessageLog` (raw in/out JSON, immutable), per-flow **state machines** (`EligibilityCheck`, `Approval`, `Claim`).
- Mapping layer: internal service item → SBS/CHI code; internal diagnosis → ICD-10-AM; practitioner → SCFHS license; payer → Nphies payer ID. Mapping gaps surface as pre-submission validation errors, never runtime crashes.
- Environments: conformance/sandbox vs production per tenant. Golden-file tests: recorded sample bundles asserted byte-stable.

### 6.2 ZATCA (`integrations/zatca`)
- Phase 1: QR (TLV base64) rendering on invoice templates.
- Phase 2 pipeline: invoice → UBL 2.1 XML → canonicalize → hash chain (PIH) → sign (CSID) → **clearance** (standard) or **reporting** (simplified) API → store cleared XML + response; PDF/A-3 embed of XML for standard invoices. Onboarding module: CSR generation, compliance CSID, production CSID, device management per branch. Sequential invoice counter + hash chain integrity job.

### 6.3 SFDA RSD (`integrations/rsd`)
- `GS1Parser` for DataMatrix AIs (01 GTIN, 21 serial, 10 batch, 17 expiry); event reporter (receive/dispense/return/destroy) with queue, retry, and failure worklist; per-tenant credentials.

### 6.4 DICOM (`integrations/dicom`)
- Standalone MWL SCP process (pynetdicom) reading scheduled RIS studies from DB; per-branch AE config. On-prem: runs on clinic LAN. SaaS: lightweight **site agent** container deployed at clinic bridging LAN modalities to cloud API (also usable later for lab analyzers) — outbound-only connection, no inbound firewall holes.

### 6.5 Messaging
- Adapter interface `send(template, to, vars, channel)`; impls: local KSA SMS gateway(s), WhatsApp Business API, email; per-tenant sender identity; delivery-status webhook ingestion.

## 7. Deployment profiles

| | SaaS | On-prem single clinic |
|---|---|---|
| Orchestration | Kubernetes (or managed containers) | Docker Compose on a clinic server (spec sheet provided) |
| Hosting | In-Kingdom region/DC (PDPL health-data residency) | Clinic premises |
| DB | Managed Postgres, PITR | Local Postgres + nightly encrypted backup CLI + off-site copy |
| Tenants | Many (RLS) | One tenant row |
| Updates | Continuous, feature-flagged | Versioned releases, remote-assisted upgrade |
| DICOM/devices | Site agent container | Direct LAN |
| Licensing | Subscription entitlements from control plane | Signed offline license file with expiry + entitlements |

Vendor **control plane** (small separate Django project or admin-only app): tenant lifecycle, plans/entitlements, usage metering, license file signing, status page.

## 8. Security architecture

- AuthN: JWT access (short) + rotating refresh (httpOnly cookie); optional TOTP; login throttling; password policy; SSO later (L).
- AuthZ: permission codes checked in service layer (`@requires("claims.submit")`); object-level tenant/branch checks; RLS backstop.
- Audit middleware wraps all mutating requests; patient-record READ events logged in EMR (access log).
- Secrets: env/vault; tenant integration credentials encrypted at rest with app KMS key.
- Input hygiene: DRF serializers + zod both sides; file uploads virus-scanned (ClamAV) and content-type enforced; all documents served via signed URLs.
- Backups encrypted; restore drills scripted; on-prem license cannot silently disable access to data (read-only grace mode on expiry — contractual trust matters in this market).

## 9. Observability & operations

- Structured JSON logs (request id, tenant id, user id); Sentry-compatible error tracking; Prometheus metrics (per-integration success rates, queue depths, eligibility latency); Grafana dashboards; uptime checks per tenant subdomain.
- `IntegrationTransaction` UI (admin) = first support tool: filter by tenant/type/status, view raw payloads, requeue.
- Feature flags + entitlements let support reproduce tenant config in staging.

## 10. Key ADRs (summarized)

1. **Shared-schema RLS multi-tenancy** over django-tenants — migration scalability + single-tenant parity (see §2).
2. **Modular monolith** over microservices — one team, transactional consistency across billing/claims; integrations isolated via Celery + adapters; DICOM MWL is the only separate process.
3. **TanStack Query, no global client store** — server is source of truth; websockets patch caches.
4. **Mock-first integrations** — sales demos, CI, and on-prem installs must run with zero external dependencies.
5. **Postgres for search & reporting in v1** — no Elasticsearch/warehouse until proven need; partitioning + matviews first.
6. **Event bus in-process** — upgrade path to outbox+broker documented; AI agents will consume the same events.

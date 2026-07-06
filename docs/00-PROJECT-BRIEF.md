# SehaERP — Clinic ERP for Saudi Arabia
## Project Brief & Master Document (read this first)

> **Audience:** Claude Code and human developers. This is the entry point. Read this, then `01-SRS.md`, `02-ARCHITECTURE.md`, `03-DESIGN.md`, `04-USE-CASES.md` in that order.
> **Working name:** "SehaERP" (placeholder — replace globally when branding is decided).

---

## 1. Vision

A cloud-native, multi-tenant clinic ERP sold on subscription (SaaS) to polyclinics, specialty clinics, and small medical centers in Saudi Arabia, with an optional single-clinic self-hosted edition sold at a premium. The system covers the full clinic value chain — reception, appointments, billing, insurance (Nphies), EMR, laboratory, pharmacy, radiology, inventory, and owner analytics — and is architected so AI/agentic features (claim-rejection management, voice-driven documentation, AI chat over results) can be layered on later as paid, per-tenant configurable add-ons.

**Version 1 goal:** a complete, compliant, *working* system good enough to run a pilot clinic end-to-end for a full billing cycle (visit → claim → payment reconciliation → ZATCA invoice), with a UI that staff love.

## 2. Business model

| Aspect | Decision |
|---|---|
| Primary model | SaaS subscription, priced per clinic + per active practitioner/module tier |
| Tiers | **Core** (reception, appointments, billing, EMR, reports) → **Plus** (+ Nphies RCM, ZATCA Phase 2, lab, pharmacy) → **Pro** (+ radiology/PACS, RSD, multi-branch, API access) → **AI add-on** (later, per-feature toggles) |
| Secondary model | Single-clinic on-prem/self-hosted install at significantly higher price + annual maintenance. Same codebase, single-tenant deployment profile. |
| Onboarding revenue | One-time setup fee: data migration, Nphies onboarding assistance, ZATCA device/CSR registration, training |
| Stickiness levers | Clinic's historical data, insurance contract/price-list configuration, trained staff, rejection analytics |

**Design consequence:** every feature must be **feature-flagged per tenant** (subscription entitlements), and the codebase must deploy identically as multi-tenant SaaS or single-tenant on-prem.

## 3. Market pain points this product must solve (requirements driver)

These are the real reasons clinics switch systems. Each maps to requirements in the SRS.

1. **Claim rejection bleeding.** Clinics lose 30–40% of claim value to rejections/delays when eligibility, approval, coding, and claim data are disconnected. → Built-in validation *before* submission (eligibility freshness, approval linkage, ICD-10-AM/service-code compatibility, mandatory-field checks per payer), rejection worklists, resubmission tracking, rejection-reason analytics per payer/doctor/code.
2. **Slow front desk = angry patients.** Eligibility checks, registration, and billing are slow in most legacy HIS. → Sub-3-second screens, keyboard-first reception, one-click eligibility (auto-run before appointment when configured), Saudi ID / Iqama scan-to-register.
3. **Doctors hate the EMR.** Too many clicks, ugly forms. → Single-screen consultation workspace, favorites/templates per doctor, ICD-10 smart search (code, English, common misspellings), auto-carried UCAF/DCAF data.
4. **Dual/complex coding.** KSA requires ICD-10-AM diagnoses and CHI/SBS billing codes mapped to internal service items. → First-class code-mapping engine (internal item ↔ SBS/CHI code ↔ payer-specific code and price).
5. **Pharmacy compliance burden.** SFDA RSD (track & trace) scanning, batch/expiry control, near-expiry losses. → GS1 DataMatrix parsing at purchase and dispense, RSD reporting queue, expiry dashboards, FEFO suggestions.
6. **Owner blindness.** Owners can't see revenue leakage, doctor productivity, insurance aging. → Owner dashboard as a headline feature, not an afterthought.
7. **ZATCA anxiety.** Phase 2 wave notifications scare small clinics. → ZATCA Phase 1/2 built-in and configurable per tenant status, with clear onboarding wizard.
8. **Arabic/RTL as second-class citizen.** → Full bilingual (AR/EN) UI, RTL-first layouts, Arabic patient-facing documents, Hijri/Gregorian dual dates where relevant.
9. **Data hostage-taking by vendors.** → Clean export tools; this builds trust and is a selling point (and PDPL expects it).

## 4. Regulatory & compliance surface (must-know)

| Body | Obligation | Impact |
|---|---|---|
| **CHI / Nphies** | All eClaims flows (eligibility, prior authorization/approval, claims, payment reconciliation, communication) via the Nphies gateway, HL7 FHIR R4.0.1, per the Nphies Financial Services Implementation Guide (portal.nphies.sa/ig). Provider onboarding requires CHI registration and certificate/PKI setup, conformance testing, then production go-live. | Entire `integrations/nphies` app; FHIR bundle builder/parser; message log; onboarding wizard |
| **ZATCA (Fatoora)** | E-invoicing: Phase 1 (compliant invoice generation, QR code) or Phase 2 (integration: XML UBL 2.1 invoices, cryptographic stamp, clearance for standard invoices, reporting ≤24h for simplified invoices) depending on the clinic's wave. VAT 15%; healthcare services to Saudi nationals in some contexts and specific exemption rules must be configurable per item. | `integrations/zatca` app; invoice XML generation, signing, API client; per-tenant phase config |
| **SFDA RSD (رصد)** | Drug track & trace: pharmacies scan GS1 DataMatrix (GTIN, serial, batch, expiry) and report supply-chain events (receive, dispense, return, destroy) to RSD. | Barcode parsing, RSD event queue with retry, dispense blocking rules |
| **PDPL** (Saudi Personal Data Protection Law) | Health data = sensitive data. Consent, purpose limitation, breach notification, data-subject rights, and **data residency in KSA** for health data (host in an in-Kingdom region/DC). | Hosting choice, audit trails, consent records, export/erasure tooling, DPA templates for clients |
| **MOH / SCFHS** | Practitioner license numbers (SCFHS) on clinical documents and claims; facility MOH license on invoices/claims. | Practitioner & facility registries with license validation fields and expiry alerts |
| **CHI paper forms** | UCAF (Unified Claim Form), DCAF (Dental), OCAF (Optical) — payers still require these as PDFs/attachments in approvals & claims. | Auto-filled printable/attachable form generation from encounter data |

## 5. Scope summary (modules)

1. **Reception & Front Desk** — registration, Saudi ID/Iqama capture, appointments, queues, eligibility check, visit creation
2. **Billing & Cashier** — charge capture, discounts, packages, split cash/insurance, payments, refunds, day-end close, ZATCA invoices
3. **Insurance RCM (Nphies)** — payer/contract/price-list setup, eligibility, prior authorization, claims batching & submission, payment reconciliation, rejection management, communications/attachments
4. **EMR (Doctor workspace)** — waiting list, patient dashboard, vitals, complaints/HPI, ICD-10-AM diagnosis, orders (lab/rad/procedures), prescriptions (generic/brand configurable), results viewing, history timeline, UCAF/DCAF/OCAF, sick leave & medical reports, specialty add-ons (dental tooth charting first)
5. **Laboratory (LIS)** — test catalog & panels, sample collection with barcodes, worklists, manual result entry with reference ranges & flags, validation/sign-off, reagent stock, (later: analyzer integration via ASTM/HL7)
6. **Pharmacy** — prescription queue, stock by batch/expiry, dispensing with substitution rules, POS billing, purchase orders/GRN, supplier management, RSD integration
7. **Radiology (RIS)** — modality worklists driven by billed orders, DICOM MWL to modality/PACS, image links/viewer handoff, structured report templates, sign-off
8. **Inventory & Procurement** — shared engine for pharmacy + lab reagents + consumables
9. **Owner Dashboard & Reports** — revenue, collections, insurance aging, rejections, doctor productivity, department P&L-lite, patient flow, no-show rates
10. **Platform/Admin** — tenant management, subscription entitlements, users/roles/permissions, branches, audit log, notifications (SMS/WhatsApp/email), backups, data export

**Explicitly deferred to Phase 2+ (do not build in v1, but don't block):** AI/agentic features, inpatient/IPD, HR/payroll, full accounting GL (v1 exports to accounting instead), telemedicine, patient mobile app (v1 ships WhatsApp/SMS notifications + a minimal public booking page), analyzer machine integration, Nphies Sehey (clinical exchange).

## 6. Technology stack (locked)

- **Backend:** Python 3.12, Django 5.x, Django REST Framework, Celery + Redis (async jobs: Nphies, ZATCA, RSD, notifications), Django Channels (websockets for live queues), PostgreSQL 16
- **Frontend:** React 19 (see ADR-0001) + TypeScript + Vite, TanStack Query, React Router, Tailwind CSS + shadcn/ui (Radix), Recharts, react-hook-form + zod, i18next (AR/EN, RTL)
- **Infra:** Docker Compose (dev & on-prem), Kubernetes or managed containers (SaaS), object storage (S3-compatible) for attachments/DICOM reports, in-Kingdom hosting for SaaS (PDPL)
- **Interop libs:** `fhir.resources` (FHIR R4 models), `python-barcode`/`treepoem` for barcodes, `lxml` + XAdES signing lib for ZATCA XML, `pydicom`/`pynetdicom` for DICOM MWL

## 7. Build order for Claude Code (milestones)

Build vertically — each milestone is demoable and testable end-to-end.

- **M0 — Foundation:** monorepo scaffold, tenant model + entitlements, auth (JWT + refresh, RBAC), audit log middleware, i18n/RTL shell, design system, seed data, CI, test harness.
- **M1 — Patient & Reception:** patient registry (Saudi ID/Iqama, duplicates check), appointments + calendar, visit/encounter creation, live queue (websocket).
- **M2 — Billing core + ZATCA Phase 1:** service catalog, price lists, cash invoicing, payments, day-end close, ZATCA Phase 1 QR invoices (PDF/A-3 later in Phase 2 work).
- **M3 — EMR core:** doctor waiting list, consultation workspace, vitals, ICD-10-AM search, orders, prescriptions, history timeline, printable UCAF.
- **M4 — Insurance & Nphies:** payers/contracts/price lists, eligibility (sandbox), prior authorization, claim build/validate/submit, payment reconciliation import, rejection worklist. (Develop against Nphies sandbox/conformance environment; abstract behind an adapter so mock mode works offline.)
- **M5 — Pharmacy + Inventory:** stock/batch/expiry engine, purchase cycle, dispensing queue, POS, RSD event queue.
- **M6 — Laboratory:** catalog, collection/barcodes, worklist, results entry & validation, printable/PDF reports, reagent stock hooks.
- **M7 — Radiology:** order-driven worklist, DICOM MWL, report templates, sign-off.
- **M8 — Owner dashboard + reports, ZATCA Phase 2**, notification center, data export, hardening, pilot readiness.
- **M9 (post-pilot) — AI add-ons behind entitlements:** rejection-management agent, voice/chat charting, results Q&A chat.

## 8. Non-negotiable engineering rules

1. Every domain write goes through a service layer (not fat views/serializers); every state change is audit-logged (who, when, before/after, tenant).
2. All external integrations (Nphies, ZATCA, RSD, SMS/WhatsApp, PACS) sit behind adapter interfaces with a **mock implementation** selectable per environment — the app must be fully demoable with zero external connectivity.
3. Money is `Decimal`, stored as `numeric(12,2)` SAR; VAT lines computed server-side only. Quantities `numeric(12,3)`.
4. All clinical/billing records are immutable after finalization — corrections happen via amendment/cancellation records, never UPDATE-in-place.
5. Every list screen ships with server-side pagination, search, and column filters from day one.
6. English + Arabic strings for every user-facing label from day one (i18n keys, no hardcoded text).
7. Feature flags/entitlements checked server-side (API) *and* used to hide UI client-side.
8. Nothing blocks the UI on an external call: eligibility, claims, ZATCA clearance, RSD all run as jobs with visible status chips and retry.

## 9. Success criteria for the pilot

- Front desk registers + checks eligibility + books in < 90 seconds for a returning patient.
- Doctor completes a standard consultation (diagnosis + 2 orders + prescription) in < 3 minutes, < 15 clicks.
- ≥ 98% of submitted claims pass Nphies gateway validation on first submission (technical rejections ~0).
- Day-end close reconciles cash/card/insurance with zero manual spreadsheets.
- Owner opens dashboard daily without being asked to (measure logins).

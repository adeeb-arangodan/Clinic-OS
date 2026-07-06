# 01 — Software Requirements Specification (SRS)
## SehaERP — Multi-tenant Clinic ERP for Saudi Arabia

Version 1.0 — Requirements are numbered `<MODULE>-<n>`. Priority: **M** = must (v1 pilot), **S** = should (v1 if time allows), **L** = later (post-pilot).

---

## 1. Actors & Roles

| Role | Description |
|---|---|
| Receptionist | Registration, appointments, eligibility, visit creation, basic billing |
| Cashier | Invoicing, payments, refunds, day-end close |
| Insurance Coordinator | Approvals, claims, reconciliation, rejections |
| Nurse | Vitals, triage, sample collection assist, queue management |
| Doctor (per specialty) | EMR, orders, prescriptions, reports; dental gets tooth charting |
| Lab Technician / Lab Supervisor | Sample processing, result entry / result validation & sign-off |
| Radiology Technician / Radiologist | Modality worklist / reporting & sign-off |
| Pharmacist | Dispensing, POS, stock, purchasing, RSD |
| Inventory/Purchase Officer | POs, GRN, suppliers, stock counts |
| Clinic Admin | Tenant-level config: users, price lists, services, templates, branches |
| Owner | Dashboards & reports (read-mostly) |
| Platform Admin (vendor = you) | Tenant lifecycle, subscriptions, entitlements, support access |
| Patient (indirect) | Receives notifications, prints, public booking page (S) |

Roles are permission bundles; tenants can clone and customize roles (granular permissions per module/action).

---

## 2. Platform & Tenancy (PLT)

- **PLT-1 (M):** Multi-tenant SaaS: strict tenant isolation of all data; a user belongs to exactly one tenant (platform admins excepted). Tenant may have multiple **branches**; most transactional data is branch-scoped, patients and catalogs are tenant-scoped with per-branch overrides (price lists, stock).
- **PLT-2 (M):** Subscription entitlements: modules and features toggle per tenant (e.g., `nphies`, `zatca_phase2`, `pharmacy`, `lab`, `radiology`, `rsd`, `ai_*`). Server enforces; UI hides.
- **PLT-3 (M):** Same codebase deploys single-tenant (on-prem) via configuration; no SaaS-only code paths in domain logic.
- **PLT-4 (M):** RBAC with granular permissions (`module.action`, e.g. `billing.refund`, `emr.sign`, `claims.submit`); role templates seeded per role above.
- **PLT-5 (M):** Full audit trail: every create/update/state-change stores actor, timestamp, tenant, branch, before/after diff; viewable by Clinic Admin (own tenant) with filters.
- **PLT-6 (M):** Authentication: email/username + password (strong policy), optional TOTP 2FA; session/JWT with refresh; idle timeout configurable (default 15 min for clinical roles); device/session list with revoke.
- **PLT-7 (M):** i18n: AR/EN for all UI; user-level language preference; RTL layout in Arabic; patient documents printable in Arabic, English, or bilingual per template config; Hijri date display alongside Gregorian where configured (storage is always Gregorian UTC).
- **PLT-8 (M):** Notification engine: templated SMS/WhatsApp/email for appointment confirm/reminder, results ready, invoice link; provider-pluggable (adapter); per-tenant sender config; consent-aware.
- **PLT-9 (M):** Working hours, holidays (incl. Ramadan schedule variant), and shift definitions per branch; drive appointment slots and day-end close periods.
- **PLT-10 (S):** In-app announcement/broadcast from vendor to tenants (maintenance notices).
- **PLT-11 (M):** Data export: Clinic Admin can export patients, visits, invoices, claims as CSV; full-tenant export available to vendor for offboarding (PDPL).
- **PLT-12 (M):** Vendor back-office: create tenant, set plan/entitlements, suspend (read-only grace mode, never silent data lock), usage metrics, impersonation with explicit consent flag + audit banner.

## 3. Patient Registry & Reception (REC)

- **REC-1 (M):** Register patient with: national identity (Saudi National ID / Iqama / Border number / GCC ID / Passport — type + number), full name (Arabic + English), DOB (Gregorian, Hijri input converter), gender, nationality, mobile (KSA format validated), address (short), marital status, emergency contact, allergies flag, VIP/notes flag, consent flags (SMS/WhatsApp marketing vs service messages).
- **REC-2 (M):** Duplicate prevention: search-before-create; hard warning on same ID-number, soft warning on same name+DOB+mobile; merge tool (Admin permission) preserving both audit trails.
- **REC-3 (M):** MRN auto-generated per tenant (configurable prefix/format).
- **REC-4 (M):** Insurance profile per patient: payer, policy/member number, class, expiry, relation (self/dependent), photo/scan of card; multiple concurrent policies allowed with a default.
- **REC-5 (M):** Appointments: calendar per doctor/resource; slot rules from doctor schedule; book/reschedule/cancel with reasons; walk-in fast path (register→visit in one screen); overbooking allowed with permission; color-coded statuses; waitlist for full days (S).
- **REC-6 (M):** Visit (encounter) creation: links patient, doctor, department, visit type (new/follow-up/procedure), payment mode (cash/insurance/split), and eligibility result if insured. Follow-up window (payer-configurable, e.g. 14 days) auto-suggests follow-up type and zero/reduced consult fee.
- **REC-7 (M):** Live queue: token per department/doctor; statuses (waiting, in-vitals, with-doctor, done); real-time updates (websocket); optional waiting-area display screen (S) and TV token board (S).
- **REC-8 (M):** One-click eligibility from booking/registration screens (see NPH-2); result summarized inline: eligible/not, class, co-pay %, deductible, network notes; stored on visit.
- **REC-9 (S):** Document scan/upload on patient file (ID, insurance card, referral) with type tags.
- **REC-10 (S):** Public self-booking page per tenant (choose department/doctor/slot; OTP-verified mobile); creates tentative appointment for reception confirmation.
- **REC-11 (M):** Appointment reminders via SMS/WhatsApp (T-24h and T-2h configurable); no-show auto-marking after grace period.

## 4. Billing & Cashier (BIL)

- **BIL-1 (M):** Service catalog: items with internal code, AR/EN names, department, type (consultation/procedure/lab/rad/pharmacy/package/consumable), default price, VAT category, active flags per branch, and **mappings to SBS/CHI billing codes** (and to payer-specific codes where contracts differ).
- **BIL-2 (M):** Price lists: default cash price list + per-payer/per-contract price lists with effective dates; discount ceilings per role; package/bundle items (e.g., dental scaling package) exploding to components for claims when required.
- **BIL-3 (M):** Charge capture: charges accrue on the visit from reception (consult), doctor orders (lab/rad/procedures), and pharmacy; cashier screen shows one consolidated visit bill with cash/insurance split per line (co-pay %, deductible, max limits from eligibility/contract).
- **BIL-4 (M):** Payments: cash, mada/card (amount + reference), bank transfer, mixed; partial payments; advance/deposit on patient account; refunds with reason + permission + original-payment link.
- **BIL-5 (M):** Invoice finalization is immutable; corrections via credit note referencing original; sequential per-branch invoice numbering (ZATCA-compliant counters).
- **BIL-6 (M):** ZATCA: Phase 1 — compliant simplified tax invoice with QR (base64 TLV: seller, VAT no., timestamp, total, VAT). Phase 2 (entitlement `zatca_phase2`) — UBL 2.1 XML generation, cryptographic stamp, onboarding (CSR/CCSID/PCSID), **reporting** of simplified invoices within 24h and **clearance** of standard invoices before issuance; failure queue with retry + human-readable errors. Per-tenant config: phase, VAT number, CR number, address, device credentials.
- **BIL-7 (M):** VAT handling per item (standard 15%, zero-rated, exempt) and per patient category where rules differ (configurable rule table — e.g., government-covered categories); VAT report by period.
- **BIL-8 (M):** Day-end close per cashier/shift: expected vs counted by method, over/short with reason, lock period; reprint pack (Z-report).
- **BIL-9 (S):** Doctor commission/revenue-share rules (percentage per service/department) computed into reports (payment happens outside system in v1).
- **BIL-10 (M):** Quotation/estimate document (esp. dental treatment plans) convertible to invoice.

## 5. Insurance RCM & Nphies (NPH)

- **NPH-1 (M):** Payer registry (HIC/TPA with Nphies IDs), contracts with: price list, co-pay/deductible rules per service type, approval-required rules (per service/amount threshold), follow-up window, claim submission window, and required attachments per service type.
- **NPH-2 (M):** **Eligibility** (CoverageEligibilityRequest/Response via Nphies FHIR R4 messaging): triggered from reception or auto-pre-appointment (config); store full response; show benefit summary; eligibility "freshness" rule (e.g., valid same-day) enforced before insurance billing.
- **NPH-3 (M):** **Prior authorization/approval**: build request from encounter (diagnoses, requested services with codes/prices, supporting info, attachments incl. auto-generated UCAF/DCAF/OCAF PDF); track statuses (queued, submitted, approved, partial, rejected, pended/more-info); approved quantities/amounts flow into billing limits; expiry tracking of approvals.
- **NPH-4 (M):** **Claims**: assemble claim per encounter (professional/institutional/pharmacy/dental/vision types as applicable) with diagnoses (ICD-10-AM), services (SBS/CHI codes), practitioner (SCFHS license), amounts, approval references, attachments; **pre-submission validator** (mandatory fields, code compatibility, eligibility & approval linkage, price-list match, duplicate check) that blocks technically-invalid claims; batch submission per payer/period; poll/receive responses.
- **NPH-5 (M):** **Payment reconciliation**: receive/import payment notices, match to claims line-by-line, book payer payments, compute variances (paid vs claimed), aging buckets per payer.
- **NPH-6 (M):** **Rejection management**: rejection worklist with payer reason codes, assignment to staff, correct-and-resubmit flow (new claim version linked to original), write-off with approval, and analytics (rejection rate by payer/doctor/service/reason). *(This worklist is the future AI-agent surface — keep data model rich.)*
- **NPH-7 (M):** **Communication/attachments** flow (payer requests more info → clinic responds with documents) tracked as threads on the claim/approval.
- **NPH-8 (M):** Full Nphies message log: every request/response bundle stored raw (JSON) + parsed status, correlation IDs, timing; searchable; exportable for CHI audits.
- **NPH-9 (M):** Onboarding config per tenant: Nphies provider ID, PKI certificate upload, endpoint environment (conformance/production), per-payer activation.
- **NPH-10 (M):** All Nphies calls are async jobs with retry/backoff and circuit breaker; UI shows per-transaction status chips; nothing blocks front-desk flow (allow "proceed as cash / pending eligibility" with permission).
- **NPH-11 (S):** Batch eligibility refresh for next-day appointments (nightly job).

## 6. EMR — Doctor Workspace (EMR)

- **EMR-1 (M):** Doctor waiting list: today's queue with token, patient, visit type, eligibility/payment badge, vitals-done flag; click to open consultation.
- **EMR-2 (M):** Patient dashboard (single screen): demographics + allergy banner (red, always visible), active problems, last visits, active medications, recent lab/rad results with flags, documents; timeline view of all history filterable by type.
- **EMR-3 (M):** Vitals capture (nurse or doctor): height, weight, BMI auto, BP, pulse, temp, SpO2, RR, pain score; pediatric percentile display (S).
- **EMR-4 (M):** Consultation note: chief complaint, HPI, examination, structured or free-text; per-doctor templates and favorite phrases; specialty templates (dental, derm, ENT…) configurable.
- **EMR-5 (M):** Diagnosis: ICD-10-AM search (code/description EN+AR, synonyms), primary + secondary, chronic flag (persists to problem list); recently-used and favorites per doctor.
- **EMR-6 (M):** Orders: lab tests/panels, radiology studies, procedures — searched from catalog, priced instantly with patient's coverage split shown, approval-required badge from contract rules; order priority (routine/urgent); orders flow to billing + department worklists.
- **EMR-7 (M):** Prescriptions: drug search from tenant formulary (generic name + brand + strength + form); **generic vs brand prescribing mode configurable per tenant/payer**; dose/frequency/duration/route with common-sig quick picks; quantity auto-calculation; refills; prints bilingual Rx; sends to internal pharmacy queue; duplicate-therapy and allergy hard-warning (interaction DB = L).
- **EMR-8 (M):** Prescription/service approval hand-off: doctor marks items needing insurance approval → generates UCAF/DCAF/OCAF pre-filled (complaint, duration, vitals, diagnosis codes, services, doctor + SCFHS license, signature block) as PDF; insurance coordinator submits via NPH-3. Nphies prescription-related transactions per current CHI IG scope where applicable (adapter-gated).
- **EMR-9 (M):** Results viewing: lab results inline with reference ranges/flags and cumulative table across dates; radiology reports + image link (opens PACS viewer URL).
- **EMR-10 (M):** Sick-leave certificate and medical report generation from templates (bilingual, with QR verification code — S); sick leave data captured in structured fields (from/to, diagnosis) for future GOSI/Seha platform integration (L).
- **EMR-11 (M):** Encounter sign-off: locks the note; addendum mechanism after lock; unsigned-encounter reminder list.
- **EMR-12 (M):** **Dental module:** graphical tooth chart (FDI numbering, permanent + deciduous), per-tooth/per-surface findings and procedures, treatment plan with phases and cost estimate (links BIL-10), completed-work history rendering on chart; DCAF uses tooth numbers.
- **EMR-13 (S):** Referral letters (internal cross-department and external).
- **EMR-14 (L):** Growth charts, antenatal flowsheets, ophthalmology visual-acuity module, and other specialty add-ons (design EMR as pluggable specialty panels).

## 7. Laboratory (LAB)

- **LAB-1 (M):** Test catalog: test code, AR/EN names, department (hematology, chemistry…), specimen type, container/tube color, result type (numeric, text, selection, multi-analyte panel), units, sex/age-specific reference ranges, critical limits, TAT, price link to BIL-1; panels/profiles bundling tests.
- **LAB-2 (M):** Order intake from EMR (or direct walk-in lab visit); billing-gate rule configurable (collect only after payment/approval, with override permission).
- **LAB-3 (M):** Sample collection: collection worklist, specimen barcode label printing (code128/QR; sample ID, patient, test, tube), collected-by/time, rejection at accession (hemolyzed etc.) with recollect flow.
- **LAB-4 (M):** Processing worklist per department/analyzer bench; result entry forms per test definition with delta-check vs previous (S), auto-flag H/L/critical; critical-value alert to ordering doctor (notification + acknowledge log).
- **LAB-5 (M):** Two-step validation: technician enters → supervisor/pathologist validates & signs; only validated results visible to doctors/patients; amended-report flow with strikethrough history.
- **LAB-6 (M):** Report output: cumulative and per-visit PDF, bilingual headers, method + reference ranges, signature block; auto-notify patient when configured (results-ready SMS with secure link — S).
- **LAB-7 (M):** Reagent/consumable stock: link tests to reagent consumption (simple per-test decrement factors), reorder-level alerts; uses shared inventory engine (INV).
- **LAB-8 (S):** Outsourced (referral) tests: mark test as send-out, track external lab, enter/attach external results.
- **LAB-9 (L):** Analyzer integration (ASTM E1381/1394, HL7 v2 ORU) via interface service; design result-entry pipeline so machine results enter the same validation queue.
- **LAB-10 (S):** QC module lite: Levey-Jennings data capture per analyte.

## 8. Pharmacy (PHA)

- **PHA-1 (M):** Drug master: SFDA-registered drug list fields (SFDA code, GTIN, generic/scientific name, brand, strength, form, pack size), pricing (public price, purchase cost), VAT category, controlled-substance schedule flag, storage flags (cold chain).
- **PHA-2 (M):** Inventory by **batch + expiry + branch/store**; FEFO pick suggestions; near-expiry dashboard (90/60/30 days); expired-stock quarantine + destruction record (RSD event).
- **PHA-3 (M):** Dispensing queue from EMR prescriptions: pharmacist verifies, substitutes brand↔generic per tenant/payer policy (substitution logged), scans GS1 DataMatrix per item (parses GTIN/serial/batch/expiry, validates against Rx and stock), partial dispense with remainder tracking.
- **PHA-4 (M):** POS: OTC direct sale, insurance dispense (uses eligibility + approval + payer drug price list), co-pay collection, returns with batch/serial validation.
- **PHA-5 (M):** **RSD integration:** report supply-chain events (receiving, dispensing, return, destroy) with serialized data; async queue with retry + failure worklist; per-tenant RSD credentials; dispense-time block/warn rules configurable when RSD rejects a serial (suspected counterfeit/duplicate).
- **PHA-6 (M):** Procurement: supplier registry, purchase orders, goods receipt (GRN) with barcode scan capturing batch/expiry/serials, purchase invoice recording, supplier returns; landed-cost-lite (S).
- **PHA-7 (M):** Stock operations: transfers between stores/branches, adjustments with reason + approval, periodic stock count (freeze, count sheets, variance posting).
- **PHA-8 (S):** Reorder planning: min/max per item per store, suggested PO from consumption velocity.
- **PHA-9 (M):** Controlled-drug handling: restricted permissions, separate register report, no dispense without prescription record.

## 9. Radiology (RAD)

- **RAD-1 (M):** Study catalog (modality, body part, prep instructions, TAT) linked to billing items.
- **RAD-2 (M):** Worklist driven by billed/approved orders; statuses: ordered → scheduled → arrived → in-progress → completed → reported → signed.
- **RAD-3 (M):** DICOM Modality Worklist (MWL) provider: push scheduled studies (patient demographics, accession number) to modalities/PACS; accession number generation.
- **RAD-4 (M):** Report editor with per-study templates (normal templates one-click), impression field, radiologist sign-off (locks; addendum flow); report PDF bilingual header.
- **RAD-5 (M):** Image access: store PACS study UID/link; open configured web viewer (e.g., tenant's PACS viewer or bundled OHIF pointed at tenant PACS) from EMR and RIS.
- **RAD-6 (S):** Critical-findings flag with notification to ordering doctor.
- **RAD-7 (L):** Built-in mini-PACS (Orthanc) offering for clinics without PACS.

## 10. Inventory shared engine (INV)

- **INV-1 (M):** Multi-store per branch (pharmacy store, lab store, general consumables); item categories; units of measure with conversions (box↔strip↔tablet).
- **INV-2 (M):** All movements ledgered (immutable stock ledger): GRN, issue, dispense, transfer, adjustment, return, destruction; running balance by item/batch/store.
- **INV-3 (M):** Valuation: weighted average cost; stock value report by store/category.
- **INV-4 (M):** Department requisitions (clinic room requests consumables from main store) with approval + issue.

## 11. Owner Dashboard & Reporting (RPT)

- **RPT-1 (M):** Owner home: today + MTD revenue (cash vs insurance), collections, visits, new patients, no-show rate, pending claims value, rejection rate, near-expiry stock value, top services/doctors — with trend sparklines and branch filter.
- **RPT-2 (M):** Revenue reports: by department/doctor/service/payer/branch/period; discounts report; refunds report.
- **RPT-3 (M):** Insurance reports: claims submitted/paid/rejected aging, payer scorecards (avg days to pay, rejection %, top rejection reasons), approval turnaround.
- **RPT-4 (M):** Operations: patient flow (visits by hour/day), appointment utilization per doctor, average wait time (token timestamps), lab TAT, pharmacy dispense time.
- **RPT-5 (M):** Inventory: stock value, consumption, near-expiry/expired losses, supplier purchase analysis.
- **RPT-6 (M):** All reports: on-screen table + chart, export CSV/PDF, save filter presets; scheduled email of key reports (S).
- **RPT-7 (M):** VAT return support report (output VAT by rate/period aligned to ZATCA filings).
- **RPT-8 (S):** Owner mobile-friendly dashboard (responsive is M; PWA install prompt is S).

## 12. AI/Agentic add-ons (Phase 2 — design hooks only in v1) (AI)

- **AI-1 (L):** Rejection-management agent: reads rejection worklist + claim + clinical note, proposes correction or appeal draft, human approves. *(v1 hook: rich structured rejection data + claim versioning.)*
- **AI-2 (L):** Voice/chat charting: dictation → structured complaint/exam/diagnosis suggestions into EMR-4/5 fields. *(v1 hook: all EMR fields addressable via API with draft state.)*
- **AI-3 (L):** Diagnosis/complaint validation: flags diagnosis-service mismatches pre-claim. *(v1 hook: pre-submission validator NPH-4 is rule-pluggable.)*
- **AI-4 (L):** Lab-results Q&A chat for doctors ("trend of HbA1c for this patient"). *(v1 hook: results stored structured with LOINC-mappable codes field.)*
- **AI-5 (L):** All AI features: per-tenant entitlement + per-feature toggle + PDPL-compliant processing disclosure; human-in-the-loop mandatory for anything clinical or financial.

## 13. Non-functional requirements (NFR)

- **NFR-1 Performance (M):** P95 API < 300ms for interactive endpoints; list screens < 1s first paint on 8 Mbps; eligibility round-trip surfaced ≤ 10s (async with live status).
- **NFR-2 Availability (M):** SaaS target 99.5% v1 (99.9% later); graceful degradation when Nphies/ZATCA/RSD are down (queue, don't block care).
- **NFR-3 Security (M):** TLS everywhere; encryption at rest (disk + column-level for national ID numbers); OWASP ASVS L2; per-tenant row isolation enforced in DB (RLS) + application; secrets in vault/env, never in repo; rate limiting; CSRF/XSS protections; signed URLs for documents.
- **NFR-4 Privacy/PDPL (M):** health data hosted in-Kingdom for SaaS; consent records; access logs on patient-record views ("break-glass" reason for accessing patients outside one's department — S); data-subject export; retention policy config; breach-notification runbook (ops doc).
- **NFR-5 Auditability (M):** immutable audit + Nphies/ZATCA/RSD raw message logs retained ≥ 6 years (configurable).
- **NFR-6 Usability (M):** full keyboard operability of reception & cashier screens; WCAG 2.1 AA contrast; Arabic RTL pixel-parity with LTR; max 3 clicks to any daily task from role home.
- **NFR-7 Reliability of jobs (M):** all integration jobs idempotent with dedup keys; poison-message worklist visible to admins.
- **NFR-8 Backup/DR (M):** SaaS: PITR ≤ 5 min RPO, ≤ 4h RTO; on-prem: bundled nightly encrypted backup + restore CLI + off-site copy instructions.
- **NFR-9 Observability (M):** structured logs with tenant/request IDs, error tracking (Sentry-compatible), metrics dashboards, per-tenant usage metering (for billing).
- **NFR-10 Testability (M):** every integration has a mock adapter; factory-based test data; e2e happy-path suite for the 10 core use cases (see 04-USE-CASES.md) run in CI.
- **NFR-11 Scalability (S):** 200 tenants / 2,000 concurrent users on v1 architecture without redesign; DB partitioning plan documented for message-log tables.
- **NFR-12 Maintainability (M):** service-layer architecture, typed API client generated from OpenAPI schema, ADRs for key decisions.

## 14. Out of scope for v1 (explicit)

Inpatient/ADT, operating theatre, HR & payroll, full general ledger (export journal summaries instead), telemedicine video, patient mobile app, insurance contract e-negotiation, Nphies Sehey clinical exchange, analyzer drivers, national e-prescription platforms beyond current CHI scope. Revisit each post-pilot.

# 03 — Design Document
## Data model, state machines, API design, and UI/UX design system

---

## 1. Core data model (ERD — entity level)

All entities implicitly carry `id (uuid), tenant_id, branch_id?, created_at, created_by, updated_at`. FKs shown as `→`.

### 1.1 Platform
- **Tenant** (name, subdomain, plan, status, locale defaults, VAT no., CR no., MOH license, Nphies provider id, timezone)
- **Entitlement** (→Tenant, feature_code, enabled, limits jsonb)
- **Branch** (→Tenant, name ar/en, address, ZATCA device config, working hours)
- **User** (→Tenant, identity, roles M2M, doctor_profile?), **Role**, **Permission**
- **AuditLog** (actor, action, entity, before/after jsonb, ip) — partitioned
- **NumberSequence** (→Tenant, →Branch?, key [mrn|invoice|claim|accession|sample], prefix, next)
- **NotificationTemplate / NotificationLog**

### 1.2 Patients & scheduling
- **Patient** (mrn, id_type, id_number [encrypted], name_ar, name_en, dob, gender, nationality, mobile, email?, address, allergy_summary, flags jsonb, consents jsonb)
- **PatientInsurance** (→Patient, →Payer, policy_no, member_no, class, relation, valid_to, is_default, card_document?)
- **PatientDocument** (→Patient, type, file, note)
- **Practitioner** (→User?, name ar/en, specialty, SCFHS license no + expiry, Nphies practitioner id, signature image)
- **Schedule** (→Practitioner, →Branch, weekday, start, end, slot_minutes, visit_types) / **ScheduleException**
- **Appointment** (→Patient, →Practitioner, slot start/end, type, status[booked|confirmed|arrived|no_show|cancelled|completed], source[desk|phone|web], reminder log)
- **Visit / Encounter** (→Patient, →Practitioner, →Appointment?, visit_type[new|followup|procedure|walkin_lab|walkin_pharmacy], payment_mode[cash|insurance|split], →PatientInsurance?, →EligibilityCheck?, status[open|in_consult|closed|cancelled], token_no, timestamps per stage)

### 1.3 Clinical (EMR)
- **VitalsRecord** (→Encounter, measurements jsonb typed, taken_by)
- **ClinicalNote** (→Encounter, sections jsonb [cc, hpi, exam, plan], template_id?, signed_at, signed_by, addenda[])
- **Diagnosis** (→Encounter, icd10am_code, description ar/en, is_primary, is_chronic → feeds **ProblemList** (→Patient))
- **ClinicalOrder** (→Encounter, order_type[lab|radiology|procedure], →ServiceItem, priority, status[draft|ordered|billed|in_progress|resulted|completed|cancelled], approval_required flag, →ApprovalItem?)
- **Prescription** (→Encounter, status) / **PrescriptionItem** (→Drug, prescribe_as[generic|brand], dose, route, frequency, duration, quantity, refills, notes)
- **DentalFinding / DentalProcedure** (→Encounter, tooth_fdi, surfaces[], condition/procedure code, status[planned|completed], →TreatmentPlan phase)
- **TreatmentPlan** (→Patient, phases[], estimate → Quotation)
- **MedicalCertificate** (→Encounter, kind[sick_leave|report], from/to, body, QR code, signed)

### 1.4 Catalogs & billing
- **ServiceItem** (code, name ar/en, dept, type, default_price, vat_category, sbs_code, active) + **ServiceCodeMap** (→ServiceItem, →Payer?, external_code, price_override?)
- **PriceList** (name, kind[cash|payer_contract], valid range) / **PriceListItem** (→ServiceItem, price)
- **ChargeLine** (→Encounter, →ServiceItem, qty, unit_price, discount, vat, patient_share, payer_share, source[reception|order|pharmacy], status[pending|invoiced|cancelled])
- **Invoice** (number, kind[simplified|standard], →Encounter?, →Patient?, totals, vat_total, status[draft|finalized|cleared|reported|credited], zatca jsonb [uuid, hash, pih, qr, cleared_xml_ref], counter refs) / **InvoiceLine**
- **CreditNote** (→Invoice, reason, lines)
- **Payment** (→Invoice/→PatientAccount, method[cash|mada|card|transfer|advance], amount, ref, shift_id) / **Refund**
- **CashierShift / DayEndClose** (expected vs counted per method, variance, locked)
- **Quotation** (→Patient, lines, valid_until, converted→Invoice?)

### 1.5 Insurance & Nphies
- **Payer** (name, kind[HIC|TPA], nphies_id, contacts) / **Contract** (→Payer, →PriceList, copay rules jsonb per service type, approval rules jsonb, followup_days, submission_window_days, required_attachments jsonb)
- **EligibilityCheck** (→Patient, →PatientInsurance, purpose, status[queued|sent|eligible|not_eligible|error], benefits jsonb, raw refs, checked_at, valid_until)
- **Approval** (→Encounter, →Payer, status[draft|queued|submitted|approved|partial|rejected|pended|expired|cancelled], nphies refs) / **ApprovalItem** (→ChargeLine/→ClinicalOrder/→PrescriptionItem, requested vs approved qty/amount, reason codes)
- **Claim** (→Encounter, →Payer, type[professional|dental|pharmacy|vision], version, replaces→Claim?, status[draft|validated|queued|submitted|accepted|paid|partially_paid|rejected|cancelled], totals, nphies refs, batch_id) / **ClaimLine** (links ChargeLine, codes, amounts, adjudication jsonb)
- **ClaimBatch** (→Payer, period, counts, submitted_at)
- **PaymentReconciliation** (→Payer, notice ref, total) / **ReconLine** (→ClaimLine, paid_amount, variance, status)
- **RejectionTask** (→Claim/→Approval, reason_codes[], assigned_to, status[open|in_progress|resubmitted|appealed|written_off], resolution notes) ← *AI agent surface*
- **NphiesMessageLog** (direction, event_code, correlation_id, request jsonb, response jsonb, http meta, timing) — partitioned, immutable
- **CommunicationThread / CommunicationMessage** (→Claim/→Approval, attachments)

### 1.6 Pharmacy & inventory
- **Drug** (sfda_code, gtin, generic_name, brand_name, strength, form, pack_size, unit conversions, price, vat, controlled_schedule, cold_chain) 
- **Store** (→Branch, kind[pharmacy|lab|general]) / **StockBatch** (→Drug/→StockItem, batch_no, expiry, qty_on_hand, avg_cost) / **StockLedgerEntry** (movement_type, qty ±, →batch, ref doc, running_balance) — immutable, partitioned
- **Supplier**, **PurchaseOrder / POLine**, **GoodsReceipt / GRNLine** (batch, expiry, serials[]), **SupplierReturn**
- **DispenseTask** (→Prescription, status[queued|verifying|ready|dispensed|partial|cancelled], pharmacist, substitutions jsonb) / **DispenseLine** (→PrescriptionItem, →StockBatch, serials[], qty)
- **RsdEvent** (kind[receive|dispense|return|destroy], payload jsonb, status[queued|sent|failed], attempts, error)
- **StockCount / StockAdjustment / StockTransfer / Requisition**

### 1.7 Lab & radiology
- **LabTest** (code, names, dept, specimen, container, result_schema jsonb [analytes, types, units, ref ranges by sex/age, critical limits], tat_minutes, loinc_code?) / **LabPanel** (M2M tests)
- **LabSample** (sample_no barcode, →ClinicalOrder(s), specimen, status[pending_collection|collected|received|rejected|in_process|resulted|validated], collected_by/at, rejection reason)
- **LabResult** (→LabSample, →LabTest, analyte values jsonb, flags, entered_by, validated_by, status[entered|validated|amended], previous_version→)
- **CriticalAlert** (→LabResult, notified_to, acknowledged_at)
- **RadStudy** (accession_no, →ClinicalOrder, modality, status[ordered|scheduled|arrived|in_progress|completed|reported|signed], pacs_study_uid?)
- **RadReport** (→RadStudy, template_id, body, impression, signed_by/at, addenda)
- **ReportTemplate** (dept, modality/test, body ar/en)

## 2. Key state machines (enforce with guarded transitions)

```
Encounter:  open → in_consult → closed          (cancel from open only; addendum after closed)
Order:      draft → ordered → billed → in_progress → resulted/completed   (cancel: before in_progress; after billing requires credit-note path)
Invoice:    draft → finalized → [cleared|reported] → (credited via CreditNote)
Approval:   draft → queued → submitted → {approved|partial|rejected|pended} ; pended→submitted(resend info) ; approved→expired
Claim:      draft → validated → queued → submitted → {accepted → paid|partially_paid | rejected} ; rejected→(new version draft, replaces link)
LabSample:  pending_collection → collected → received → in_process → resulted → validated ; any→rejected(recollect spawns new sample)
DispenseTask: queued → verifying → ready → dispensed (partial loops)
RadStudy:   ordered → scheduled → arrived → in_progress → completed → reported → signed
```
Cross-cutting rules: billing gate before lab collection/rad scheduling/dispense is **configurable per tenant** (`bill_before_service: strict|warn|off` per department); approval gate enforced when contract rules demand.

## 3. API design conventions

- Base `/api/v1/`. Resources plural, kebab-case: `/api/v1/insurance/claims/{id}/submit/` (state transitions are POST sub-actions, not PATCH of status).
- Auth: `Authorization: Bearer`; tenant from subdomain or `X-Tenant` (on-prem single value).
- List endpoints: `?search=`, `?ordering=`, field filters, cursor pagination `{results, next, prev, count?}`.
- Errors: `{"code":"claim.validation_failed","message_en":...,"message_ar":...,"field_errors":{...},"details":[rule results]}` — validation rule results are structured so UI renders a checklist (and later AI can read it).
- Long operations return `{transaction_id}`; poll `/api/v1/integrations/transactions/{id}` or receive websocket event `integration.status`.
- Websocket topics: `queue.{dept}`, `user.alerts`, `integration.status`.
- OpenAPI schema published; TS client generated in CI; breaking changes require `/v2`.

## 4. Critical algorithms & rules (spec level)

1. **Coverage split calculator:** input (ChargeLine, Contract, EligibilityCheck, Approval) → output (patient_share, payer_share, applied rule trace). Order: contract service-type rule → eligibility benefit overrides → approval caps → co-pay % + deductible + max-limit. Trace stored on the line (dispute/AI fodder).
2. **Claim pre-submission validator:** pluggable rule pipeline (mandatory demographics, ICD present & billable, service↔SBS mapping exists, price matches contract ±0, approval linked where required, eligibility fresh, practitioner license valid, attachment checklist met, duplicate-claim probe). Each rule returns pass/fail/warn + fix-hint. Claims can't queue with fails.
3. **FEFO allocation:** dispense picks batches by earliest expiry with sufficient qty; serial scan must belong to picked batch else re-allocate; expiry < configurable min-shelf-days blocks with override permission.
4. **Follow-up detection:** same patient+practitioner+specialty within contract `followup_days` and prior visit had consult → suggest follow-up visit type with contract-defined price (often zero).
5. **Token & wait-time:** token per dept per day; timestamps at each queue stage; wait-time metrics derived, never manually entered.
6. **Invoice numbering + ZATCA hash chain:** per-branch counter table locked in the finalization transaction; previous-invoice-hash stored; integrity checker job validates chain nightly.

## 5. UI/UX design system ("customer experience is a feature")

### 5.1 Principles
1. **Role-first:** each role logs into *their* workspace, not a generic menu. Zero navigation for the 5 most common tasks.
2. **Speed feels like quality:** optimistic UI where safe, skeletons not spinners, sub-100ms interactions, keyboard-first at desk roles (global shortcuts: `F2` new patient, `F4` search patient, `F8` take payment — configurable, discoverable via `?` overlay).
3. **Bilingual with dignity:** Arabic is not a translation afterthought — RTL mirrored layouts, Arabic-optimized numerals option, high-quality Arabic type.
4. **Status is always visible:** every async thing (eligibility, approval, claim, ZATCA, RSD) shows a colored chip with plain-language state + tap-for-detail; never a silent failure.
5. **Calm clinical screens:** whitespace, one primary action per screen, destructive actions double-confirmed and permission-gated.

### 5.2 Visual language
- **Typography:** `IBM Plex Sans Arabic` (AR + Latin support) primary; fallback `Noto Sans Arabic`. Type scale: 12/14/16/20/24/30. Numbers in tables use tabular figures.
- **Color tokens (Tailwind CSS variables):**
  - `--primary`: teal-700 `#0F766E` (healthcare-trust, distinct from the blue everyone uses); hover teal-800
  - `--bg`: near-white `#F8FAFC`; surfaces white; borders slate-200
  - Semantic: success emerald-600, warning amber-500, danger rose-600, info sky-600
  - Insurance chip palette: eligible=emerald, pending=amber, rejected=rose, cash=slate
  - Dark mode: S (owner dashboard first)
- **Density:** compact tables (40px rows) for worklists; comfortable forms; cards only on dashboards, never for data entry.
- **Iconography:** lucide icons only; no emoji in clinical UI.
- **Charts:** Recharts, max 2 colors + gray per chart, always show numbers on hover and totals.

### 5.3 Signature screens (build to these specs)
- **Reception board:** left = today's appointments (live statuses), center = patient quick search + `New Patient/Visit` split button, right = live department queues. Registration form is a single vertical column, ID-scan button on top, eligibility chip appears inline after check. Target: returning-patient check-in ≤ 4 fields touched.
- **Doctor consultation workspace:** header = patient banner (photo, age/sex, allergy red pill, coverage chip). Left rail = history timeline. Center tabs: Note → Diagnosis → Orders → Rx → Forms. Right rail = live cart (everything ordered this visit with patient/payer split and approval badges). One `Sign & Close` primary button; blocking issues listed inline before sign.
- **Dental chart:** SVG FDI odontogram; click tooth → radial surface picker → condition/procedure palette; planned=outline, completed=filled; auto-syncs to plan/estimate.
- **Cashier:** invoice composition left, big-numbers payment panel right (numpad-friendly), method tabs; prints on finalize; refund behind permission.
- **Rejection worklist:** claims table with reason chips, assignee, age; side panel shows claim vs response diff and one-click "create corrected version".
- **Owner dashboard:** 6 KPI cards + revenue trend + payer scorecard + today's live ops (waiting now, avg wait) + alerts (near-expiry value, unsubmitted claims aging). Branch switcher top-right.

### 5.4 UX rules for forms & tables
- Labels above fields; inline validation on blur; server errors mapped to fields; Arabic error text.
- Every table: sticky header, column search, saved views, CSV export, row density toggle.
- Empty states teach ("No claims yet — submit your first batch" + doc link).
- Confirmation toasts include undo where safe (non-financial, non-clinical).
- Mobile: owner dashboard + reports fully responsive; operational screens optimized for ≥1280px (declare this; don't half-support phones at the front desk).

### 5.5 Document templates (print/PDF)
Bilingual header (clinic logo, name AR/EN, CR, VAT no., MOH license) on: tax invoice (ZATCA QR), receipt 80mm, prescription, lab report, radiology report, UCAF/DCAF/OCAF, sick leave (QR verify), quotation. Template variables documented; per-tenant logo/footer config.

## 6. Testing design

- Unit: services + calculators (coverage split, validator rules, FEFO, VAT) at ≥90% branch coverage — these carry the money.
- Contract: golden-file FHIR bundles and ZATCA XML snapshots per scenario.
- E2E (Playwright): the 10 core flows in 04-USE-CASES.md, run in CI against mock adapters, in both `en` and `ar` locales.
- Load: k6 script for reception search + queue websockets at 2,000 concurrent users.

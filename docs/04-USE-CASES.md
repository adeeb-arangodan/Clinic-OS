# 04 — Use Case Document
## SehaERP — Core use cases with main & alternate flows

These 10 core use cases (UC-1…UC-10) are the CI e2e suite and the pilot acceptance script. UC-11+ are secondary.

---

### UC-1 — Register patient & check insurance eligibility
**Actor:** Receptionist. **Trigger:** patient at desk. **Pre:** none.
**Main flow:**
1. Receptionist presses `F4`, searches by ID number/mobile/name → no match → `F2` New Patient.
2. Enters ID type+number, names (AR/EN), DOB, gender, nationality, mobile; system validates KSA mobile & ID checksum; MRN auto-assigned.
3. Adds insurance: selects payer, policy/member no., class, expiry; scans card image.
4. Clicks **Check Eligibility** → async Nphies CoverageEligibilityRequest; chip shows *Checking…* → *Eligible — Class B, 20% co-pay, deductible 0*.
5. Books visit (UC-2) or appointment.
**Alternates:** A1 duplicate ID found → open existing record, offer update. A2 eligibility returns not-eligible → chip red; receptionist offers cash or patient contacts insurer; proceeding as insurance blocked (permission override logs reason). A3 Nphies timeout → status *Pending*; receptionist may proceed as cash-pending-eligibility per tenant policy; job retries and updates visit automatically.
**Post:** patient exists, eligibility stored with freshness timestamp.

### UC-2 — Insured consultation visit, end-to-end (the golden path)
**Actors:** Receptionist, Nurse, Doctor, Cashier. **Pre:** UC-1 done, doctor scheduled.
**Main flow:**
1. Receptionist creates Visit (type New, mode Insurance) → consult ChargeLine auto-added with payer/patient split from contract → token issued → appears in dept queue (websocket).
2. Cashier collects patient co-pay share for consult (tenant policy: collect-first) → simplified invoice printed with ZATCA QR.
3. Nurse selects token → records vitals → status *in-vitals* → *waiting doctor*.
4. Doctor opens patient from waiting list; reviews history; writes note; adds Diagnosis (ICD-10-AM search); orders 2 lab tests + 1 radiology study; prescribes 2 drugs (generic mode); right-rail cart shows each item's split + *Approval required* badge on the MRI per contract rule.
5. Doctor clicks **Sign & Close** → validation checklist passes → encounter signed; lab/rad orders → worklists; Rx → pharmacy queue; approval-required items → insurance coordinator queue.
**Alternates:** A1 follow-up within contract window → visit auto-suggested as follow-up, consult fee 0. A2 doctor cancels an ordered-but-billed item → credit-note path with cashier involvement. A3 patient is cash → all lines patient-share 100%, no approval steps.
**Post:** signed encounter; downstream queues populated; charges consistent.

### UC-3 — Prior authorization (approval) with UCAF
**Actor:** Insurance Coordinator. **Pre:** UC-2 created approval-required items.
**Main flow:**
1. Coordinator opens Approvals queue → selects encounter → system pre-builds request: diagnoses, requested services with codes/prices, vitals/complaint from note, auto-generated UCAF PDF attached (DCAF if dental).
2. Reviews, submits → Nphies prior-auth bundle sent; status *Submitted*.
3. Response: *Approved* items get approved qty/amount caps; billing limits update automatically; doctor/reception notified.
**Alternates:** A1 *Partial* → coordinator sees per-item adjudication; informs patient of self-pay difference; patient accepts (billed) or declines (order cancelled). A2 *Pended — more info* → Communication thread opens; coordinator attaches report; resubmits. A3 *Rejected* → RejectionTask created (UC-6 handles). A4 approval expires before service → warning at billing; re-approval shortcut.
**Post:** approval state + caps stored, linked to lines.

### UC-4 — Claim submission batch & payment reconciliation
**Actor:** Insurance Coordinator. **Pre:** closed insured encounters in period.
**Main flow:**
1. Coordinator opens Claims → *Ready to build* list → builds claims (one per encounter) → each runs pre-submission validator → *Validated*.
2. Selects payer + period → creates ClaimBatch → submits; per-claim status chips update via polling job.
3. Weeks later: payment reconciliation notice retrieved/imported → system matches claim lines, books paid amounts, computes variances, updates aging.
**Alternates:** A1 validator fails a claim → structured fix-list (e.g., "Service X has no SBS mapping for payer Y") → fix → revalidate. A2 line-level partial payment → variance flagged → coordinator accepts (write-off w/ permission) or opens RejectionTask. A3 duplicate submission attempt → blocked by dedup probe.
**Post:** claims lifecycle and payer aging accurate; owner dashboard reflects.

### UC-5 — Pharmacy dispensing with RSD
**Actor:** Pharmacist. **Pre:** UC-2 sent Rx to queue; stock exists.
**Main flow:**
1. Pharmacist opens DispenseTask → verifies items vs allergies/duplicates → FEFO batch suggestions shown.
2. Scans each pack's GS1 DataMatrix → system parses GTIN/serial/batch/expiry, validates against Rx item and suggested batch.
3. Insurance items: payer share per drug price list; collects patient co-pay at POS → invoice (ZATCA QR).
4. Confirms dispense → stock ledger entries posted; RSD *dispense* events queued and sent async; task *Dispensed*.
**Alternates:** A1 brand out of stock → substitution per policy (generic allowed) logged. A2 serial fails RSD check → item blocked, quarantine flow, alternative pack scanned. A3 partial stock → partial dispense, remainder tracked. A4 OTC walk-in → direct POS sale, no Rx (blocked for controlled drugs).
**Post:** stock, RSD, billing consistent; Rx remainder visible.

### UC-6 — Rejection management & resubmission
**Actor:** Insurance Coordinator. **Pre:** claim rejected (UC-4/A).
**Main flow:**
1. RejectionTask appears in worklist with payer reason codes decoded to plain language; auto-assigned by rule (payer owner).
2. Coordinator opens side-by-side claim vs adjudication; identifies fix (e.g., wrong ICD pairing); edits new claim **version** (replaces link preserved).
3. Revalidates → resubmits → outcome tracked; task closed as *Resubmitted→Paid*.
**Alternates:** A1 non-recoverable → *Write-off* with approval permission + reason (feeds analytics). A2 dispute → Communication thread appeal with attachments.
**Post:** every rejection reaches a terminal state; analytics by reason/payer/doctor update. *(This exact surface is where the Phase-2 AI agent plugs in: it drafts step 2.)*

### UC-7 — Lab order lifecycle
**Actors:** Lab Tech, Lab Supervisor, Doctor. **Pre:** UC-2 ordered tests, billing gate satisfied.
**Main flow:**
1. Collection worklist shows patient; tech collects, prints barcode labels, marks collected.
2. Sample received in lab → bench worklist → tech enters results in test-defined form; system flags H/L; one value critical → CriticalAlert fires to ordering doctor (must acknowledge).
3. Supervisor validates & signs → results visible in EMR with cumulative view; PDF report available; patient notified (if configured).
**Alternates:** A1 sample rejected (hemolyzed) → recollect flow spawns new sample, TAT clock annotated. A2 amended result → versioned amendment, report watermarked *Amended*. A3 send-out test → external lab tracking, manual entry/attach.
**Post:** validated results immutable-versioned; reagent decrements posted.

### UC-8 — Radiology order → DICOM worklist → signed report
**Actors:** Rad Tech, Radiologist. **Pre:** UC-2 rad order billed/approved.
**Main flow:**
1. Study appears in RIS worklist → tech schedules/arrives patient → MWL exposes demographics + accession to modality.
2. Modality performs study → tech marks completed (PACS study UID linked).
3. Radiologist opens report editor → loads template → edits findings/impression → **Sign** → report locked, visible in EMR with image link.
**Alternates:** A1 no PACS at clinic → images on modality/workstation; report-only flow, link optional. A2 critical finding → flag + notify ordering doctor. A3 addendum after sign.

### UC-9 — Cashier day-end close
**Actor:** Cashier (+ Admin). **Main flow:** open shift report → system shows expected totals per method from payments → cashier enters counted amounts → variance & reason → close (locks shift) → Z-report prints → Admin reviews variances. **Alternates:** unclosed-invoice warning list must be resolved/carried with permission.

### UC-10 — Owner monthly review
**Actor:** Owner. **Main flow:** opens dashboard → filters branch/month → reviews revenue split, payer scorecard (days-to-pay, rejection %), doctor productivity, no-show %, near-expiry value → drills into rejection reasons → exports board pack PDF. **Alternates:** schedules weekly email of KPI pack.

---

### Secondary use cases (short form)
- **UC-11 Tenant onboarding (vendor):** create tenant → plan/entitlements → admin invite → guided setup wizard (branches, doctors, services, price lists, payers, templates, integration credentials) with progress checklist → demo-data toggle → go-live checklist (Nphies conformance passed, ZATCA onboarded, printers tested).
- **UC-12 Appointment reminder & no-show:** T-24h WhatsApp confirm (reply-to-cancel — S), T-2h SMS; grace-period auto no-show; reception reschedule flow.
- **UC-13 Dental treatment plan:** chart findings → multi-phase plan → quotation → patient approves phase 1 → procedures convert to orders/charges per session; DCAF per session.
- **UC-14 Purchase cycle:** low-stock suggestion → PO → supplier delivers → GRN with barcode scans (batch/expiry/serials, RSD receive events) → purchase invoice recorded → stock live.
- **UC-15 Stock count:** freeze store → count sheets/scan → variance report → approval → adjustment posted.
- **UC-16 Walk-in lab/pharmacy customer:** direct visit types skipping doctor; lab: order+bill+collect; pharmacy: POS.
- **UC-17 Patient merge:** admin merges duplicates; all children re-pointed; audit preserved.
- **UC-18 Refund/credit note:** permissioned; reason-coded; ZATCA credit note issued referencing original.
- **UC-19 Break-glass access (S):** doctor opens patient outside own department → reason prompt → access logged & reportable.
- **UC-20 Data export/offboarding:** admin exports datasets; vendor produces full export within contractual SLA.

---

### Traceability
| UC | Primary SRS reqs |
|---|---|
| UC-1 | REC-1..4, REC-8, NPH-2 |
| UC-2 | REC-5..7, BIL-1..7, EMR-1..8, EMR-11 |
| UC-3 | NPH-3, NPH-7, EMR-8 |
| UC-4 | NPH-4, NPH-5, NPH-8 |
| UC-5 | PHA-1..5, BIL-6 |
| UC-6 | NPH-6 |
| UC-7 | LAB-1..7 |
| UC-8 | RAD-1..5 |
| UC-9 | BIL-8 |
| UC-10 | RPT-1..7 |

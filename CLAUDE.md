# CLAUDE.md — SehaERP

Multi-tenant clinic ERP for Saudi Arabia. Django 5 + DRF + Celery backend, React 18 + TypeScript frontend, PostgreSQL 16. Sold as SaaS with a single-tenant on-prem deploy profile.

## Read these before writing code
- `docs/00-PROJECT-BRIEF.md` — vision, business model, build order (M0–M9), non-negotiable engineering rules
- `docs/01-SRS.md` — numbered requirements (`REC-1`, `NPH-4`, …). Reference requirement IDs in commits and PR descriptions.
- `docs/02-ARCHITECTURE.md` — tenancy (shared schema + RLS), app layout, adapter pattern, ADRs
- `docs/03-DESIGN.md` — data model, state machines, API conventions, UI design system
- `docs/04-USE-CASES.md` — UC-1…UC-10 are the e2e test suite and acceptance script

When docs and code disagree, docs win — or propose an ADR in `docs/adr/` and update the docs in the same PR.

## Repository layout
```
/backend      Django project (apps per docs/02 §3)
/frontend     React app (feature folders mirroring backend apps)
/deploy       docker-compose.dev.yml, docker-compose.onprem.yml, k8s/
/docs         specification docs + /adr
```

## Commands
```bash
# Dev environment (Postgres, Redis, backend, frontend, celery, mock adapters)
docker compose -f deploy/docker-compose.dev.yml up

# Backend
cd backend
python manage.py migrate
python manage.py seed_demo          # demo tenant + sample data (create this command in M0)
pytest                              # unit + integration tests
ruff check . && ruff format .       # lint/format
python manage.py spectacular --file schema.yml   # OpenAPI schema

# Frontend
cd frontend
npm run dev
npm run test                        # vitest
npm run lint
npm run generate:api                # TS client from backend schema.yml
npm run e2e                         # Playwright (UC-1..UC-10, en + ar locales)
```

## Non-negotiable rules (enforced in review)
1. **Tenancy:** every domain model inherits `TenantModel`. Every unique constraint is composite with `tenant_id`. Never write a query that isn't tenant-scoped; RLS is a backstop, not the mechanism. Celery tasks take `tenant_id` explicitly.
2. **Service layer:** business logic lives in `services.py` (writes) and `selectors.py` (reads). Views/serializers stay thin. Cross-app access only via services.
3. **State machines:** status changes go through guarded transition functions (see docs/03 §2). Never `obj.status = X; obj.save()`.
4. **Immutability:** finalized invoices, signed notes, validated results, submitted claims are never updated in place — amendments/credit notes/versions with `replaces_id`.
5. **Money:** `Decimal`, `numeric(12,2)` SAR, VAT computed server-side only. Quantities `numeric(12,3)`.
6. **Audit:** every mutation audit-logged (actor, tenant, before/after). It's middleware + service-layer hooks; don't bypass.
7. **Integrations:** everything external (Nphies, ZATCA, RSD, SMS, DICOM) goes through an adapter interface with a working `Mock` implementation. No feature may require live credentials to develop, demo, or test. All external calls are Celery jobs — never inline in a request — idempotent via `dedup_key`, surfaced through `IntegrationTransaction`.
8. **i18n:** no hardcoded user-facing strings. Every label gets `en` + `ar` keys in the same PR. All new UI must render correctly in RTL.
9. **Entitlements:** feature access checked server-side via `RequiresEntitlement("...")` permission and hidden client-side via the feature-flag context.
10. **API:** state transitions are POST sub-actions (`/claims/{id}/submit/`), cursor pagination, error envelope `{code, message_en, message_ar, field_errors}` per docs/03 §3. Regenerate the TS client whenever the schema changes.

## Testing expectations
- Money-path code (coverage split calculator, claim validator, FEFO, VAT, day-end) ≥ 90% branch coverage.
- Golden-file tests for FHIR bundles and ZATCA XML — snapshot changes require explicit justification in the PR.
- Each milestone ends with its UC e2e test passing in CI against mock adapters, in both locales.
- Factories (factory_boy) for all models; no fixtures-by-hand.

## Style
- Python: ruff (line length 100), type hints on all service/selector signatures, no bare `except`.
- TypeScript: strict mode, no `any`, TanStack Query for all server state (no Redux), react-hook-form + zod for forms.
- Naming: models singular (`Claim`), tables plural, API resources plural kebab-case.
- Commits: `feat(insurance): claim pre-submission validator [NPH-4]`.

## Definition of done (per feature)
Code + tests + i18n keys (en/ar) + audit coverage + OpenAPI updated + TS client regenerated + docs/SRS ID referenced + demo-able via `seed_demo` data with mock adapters.

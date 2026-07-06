# 0002 — RLS enforcement roles and isolation-testing strategy

- **Status:** accepted
- **Date:** 2026-07-06
- **Context:** docs/02 §2 mandates shared-schema multi-tenancy with RLS as the
  DB-level backstop and "a separate DB role bypassing RLS" for platform admin,
  but leaves the concrete role layout open. Postgres superusers always bypass
  RLS, and table owners bypass it unless `FORCE ROW LEVEL SECURITY` is set —
  so *who connects as what* determines whether RLS does anything at all.
- **Decision:**
  - Migrations, `manage.py`, and vendor/platform jobs run as the DB owner
    role (dev/CI: the compose superuser) — RLS bypassed by design.
  - A `sehaerp_app` **NOLOGIN** role is created in migration `core.0002`; it
    holds CRUD grants (+ default privileges for future tables) and is subject
    to RLS. In production the application's login user is a member of
    `sehaerp_app` (or `SET ROLE`s into it); it must never be superuser or hold
    `BYPASSRLS`.
  - Every tenanted table gets `ENABLE` + `FORCE ROW LEVEL SECURITY` and a
    `tenant_isolation` policy comparing `tenant_id` to the transaction-local
    GUC `app.tenant_id` (set via `set_config(..., true)` ≡ `SET LOCAL` by
    `core.tenancy`). Unset GUC ⇒ zero rows: fail closed. SQL builders live in
    `core/db.py` and are reused by every future migration that adds a
    tenanted table.
  - `core_tenant` carries no policy (needed to resolve subdomain → tenant
    before a scope exists; it contains no clinical data). `core_user` allows
    `tenant_id IS NULL` rows (platform admins) to remain visible in any scope.
  - Isolation tests create fixtures on the owner connection, then
    `SET LOCAL ROLE sehaerp_app` and assert that deliberately unscoped ORM
    queries only see the scoped tenant's rows, and that cross-tenant
    INSERT/UPDATE are rejected by the policy's `WITH CHECK`.
- **Consequences:** RLS protection is only as real as the production
  connection config — deploy manifests must connect the app as the member
  login user, and this must be verified in the go-live checklist. Requests
  resolved to a tenant run inside one DB transaction (scope = transaction),
  which is acceptable because external calls never happen inline (CLAUDE.md
  rule 7).

"""RLS policy SQL builders, used by every migration that creates a tenanted table.

Enforcement model (ADR-0002):
- Migrations and manage.py run as the DB owner (dev/CI: superuser) and bypass RLS.
- The application executes as `sehaerp_app`, a NOLOGIN role that is granted to
  the app's login user in production (`SET ROLE` / role membership). It has no
  BYPASSRLS, so policies apply.
- Policies compare `tenant_id` to the `app.tenant_id` GUC set per transaction
  by core.tenancy. Unset GUC ⇒ NULL ⇒ zero rows: fail closed.
"""

APP_ROLE = "sehaerp_app"

CREATE_APP_ROLE_SQL = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        CREATE ROLE {APP_ROLE} NOLOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO {APP_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};
"""

_TENANT_GUC = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def rls_enable_sql(table: str, *, allow_null_tenant: bool = False) -> str:
    """Enable + force RLS and add the tenant isolation policy for `table`.

    allow_null_tenant: rows with tenant_id IS NULL stay visible in every scope
    (only for platform-level rows, e.g. vendor platform admins in core_user).
    """
    condition = f"tenant_id = {_TENANT_GUC}"
    if allow_null_tenant:
        condition = f"(tenant_id IS NULL OR {condition})"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {table}
    USING ({condition})
    WITH CHECK ({condition});
"""


def rls_disable_sql(table: str) -> str:
    return f"""
DROP POLICY IF EXISTS tenant_isolation ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def month_partition_sql(table: str, year: int, month: int) -> str:
    """CREATE ... PARTITION OF for one month of a RANGE(created_at) table.
    Idempotent (IF NOT EXISTS); rows outside any month partition land in the
    table's DEFAULT partition, so a missed month never loses writes.
    """
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return f"""
CREATE TABLE IF NOT EXISTS {table}_y{year}m{month:02d} PARTITION OF {table}
    FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{next_year}-{next_month:02d}-01');
"""

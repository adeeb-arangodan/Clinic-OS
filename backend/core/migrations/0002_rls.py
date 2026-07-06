"""RLS backstop for tenant isolation (PLT-1, NFR-3; docs/02 §2, ADR-0002).

Creates the `sehaerp_app` NOLOGIN role (RLS-subject; production app login users
are granted membership) and enables forced RLS with tenant policies on every
tenanted core table. `core_tenant` itself carries no policy: it must be
readable to resolve subdomain → tenant before the scope GUC exists.
"""

from django.db import migrations

from core.db import CREATE_APP_ROLE_SQL, rls_disable_sql, rls_enable_sql


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_APP_ROLE_SQL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(
            sql=rls_enable_sql("core_branch"),
            reverse_sql=rls_disable_sql("core_branch"),
        ),
        migrations.RunSQL(
            sql=rls_enable_sql("core_entitlement"),
            reverse_sql=rls_disable_sql("core_entitlement"),
        ),
        # Platform admins have tenant IS NULL and stay visible in every scope.
        migrations.RunSQL(
            sql=rls_enable_sql("core_user", allow_null_tenant=True),
            reverse_sql=rls_disable_sql("core_user"),
        ),
    ]

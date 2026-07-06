"""RLS policies for the D3 auth/RBAC tables (PLT-1, ADR-0002).

core_authsession mirrors core_user: platform admin sessions have tenant NULL
and stay visible in every scope (queries still filter by user).
"""

from django.db import migrations

from core.db import rls_disable_sql, rls_enable_sql


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_authsession_role_userrole_role_uniq_role_name_tenant_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=rls_enable_sql("core_role"),
            reverse_sql=rls_disable_sql("core_role"),
        ),
        migrations.RunSQL(
            sql=rls_enable_sql("core_userrole"),
            reverse_sql=rls_disable_sql("core_userrole"),
        ),
        migrations.RunSQL(
            sql=rls_enable_sql("core_authsession", allow_null_tenant=True),
            reverse_sql=rls_disable_sql("core_authsession"),
        ),
    ]

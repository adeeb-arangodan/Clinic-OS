"""AuditLog (PLT-5, NFR-5; docs/03 §1, docs/02 §5).

The database side is raw DDL, not CreateModel: audit_log is partitioned by
month on created_at from day one (docs/02 §5), which Django's schema editor
cannot express. Ongoing month partitions come from `manage.py
ensure_audit_partitions`; a DEFAULT partition catches anything else so writes
never fail. Immutability (NFR-5): the app role gets SELECT/INSERT only, and
strict tenant RLS applies (Clinic Admin sees own tenant; vendor access uses
the RLS-bypassing role per docs/02 §2).
"""

import uuid
from datetime import date

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

from core.db import APP_ROLE, month_partition_sql, rls_disable_sql, rls_enable_sql

_today = date.today()
_this_month = month_partition_sql("core_auditlog", _today.year, _today.month)
_next = (_today.year + 1, 1) if _today.month == 12 else (_today.year, _today.month + 1)
_next_month = month_partition_sql("core_auditlog", *_next)

CREATE_SQL = f"""
CREATE TABLE core_auditlog (
    id uuid NOT NULL,
    created_at timestamptz NOT NULL,
    tenant_id uuid NULL REFERENCES core_tenant(id) ON DELETE RESTRICT,
    branch_id uuid NULL REFERENCES core_branch(id) ON DELETE RESTRICT,
    actor_id uuid NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    action varchar(50) NOT NULL,
    entity_type varchar(100) NOT NULL,
    entity_id uuid NULL,
    before jsonb NULL,
    after jsonb NULL,
    ip inet NULL,
    user_agent varchar(300) NOT NULL,
    request_id uuid NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE INDEX auditlog_tenant_created_idx ON core_auditlog (tenant_id, created_at DESC);
CREATE INDEX auditlog_entity_idx ON core_auditlog (tenant_id, entity_type, entity_id);

CREATE TABLE core_auditlog_default PARTITION OF core_auditlog DEFAULT;
{_this_month}
{_next_month}

REVOKE UPDATE, DELETE, TRUNCATE ON core_auditlog FROM {APP_ROLE};
{rls_enable_sql("core_auditlog")}
"""

DROP_SQL = f"""
{rls_disable_sql("core_auditlog")}
DROP TABLE core_auditlog;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_rls_auth"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AuditLog",
                    fields=[
                        ("pk", models.CompositePrimaryKey("id", "created_at", blank=True, editable=False, primary_key=True, serialize=False)),
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False)),
                        ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                        ("action", models.CharField(max_length=50)),
                        ("entity_type", models.CharField(blank=True, max_length=100)),
                        ("entity_id", models.UUIDField(blank=True, null=True)),
                        ("before", models.JSONField(blank=True, null=True)),
                        ("after", models.JSONField(blank=True, null=True)),
                        ("ip", models.GenericIPAddressField(blank=True, null=True)),
                        ("user_agent", models.CharField(blank=True, max_length=300)),
                        ("request_id", models.UUIDField(blank=True, null=True)),
                        ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
                        ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.branch")),
                        ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.tenant")),
                    ],
                    options={
                        "indexes": [
                            models.Index(fields=["tenant", "-created_at"], name="auditlog_tenant_created_idx"),
                            models.Index(fields=["tenant", "entity_type", "entity_id"], name="auditlog_entity_idx"),
                        ],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(sql=CREATE_SQL, reverse_sql=DROP_SQL),
            ],
        ),
    ]

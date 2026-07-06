"""PLT-5 / NFR-5: audit hooks, request-context stamping, diff-only updates,
DB-level immutability, tenant isolation, and the Clinic Admin viewer."""

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client

from core import audit, services
from core.db import APP_ROLE
from core.models import AuditLog
from core.tests.factories import RoleFactory, TenantFactory, UserFactory, UserRoleFactory

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-9!"


# --- hooks ------------------------------------------------------------------


def test_login_via_http_writes_audit_row_with_request_context() -> None:
    tenant = TenantFactory(subdomain="alpha")
    user = UserFactory(tenant=tenant, username="cashier1")

    response = Client().post(
        "/api/v1/auth/login/",
        {"username": "cashier1", "password": PASSWORD},
        content_type="application/json",
        headers={"X-Tenant": "alpha"},
    )
    assert response.status_code == 200

    entry = AuditLog.objects.get(action="auth.login")
    assert entry.actor == user
    assert entry.tenant_id == tenant.id
    assert entry.entity_type == "core.user"
    assert entry.entity_id == user.id
    assert entry.ip == "127.0.0.1"
    assert str(entry.request_id) == response.headers["X-Request-ID"]


def test_log_update_stores_only_changed_fields() -> None:
    role = RoleFactory(name_en="Cashier", permissions=["billing.view"])

    before = audit.snapshot(role)
    role.permissions = ["billing.view", "billing.refund"]
    role.save()
    entry = audit.log_update(role, before=before)

    assert entry is not None
    assert entry.before == {"permissions": ["billing.view"]}
    assert entry.after == {"permissions": ["billing.view", "billing.refund"]}
    assert entry.entity_type == "core.role"


def test_log_update_returns_none_when_nothing_changed() -> None:
    role = RoleFactory()
    before = audit.snapshot(role)
    role.save()  # touches updated_at only, which the diff ignores
    assert audit.log_update(role, before=before) is None


def test_snapshot_never_contains_password() -> None:
    user = UserFactory()
    assert "password" not in audit.snapshot(user)


def test_service_writes_are_audited() -> None:
    tenant = TenantFactory()
    services.seed_role_templates(tenant=tenant)
    seeded = AuditLog.objects.get(action="roles.seeded", tenant_id=tenant.id)
    assert len(seeded.after["created"]) == 13

    role = services.create_role(
        tenant=tenant, name_en="Auditor", name_ar="مدقق", permissions=["reports.view"]
    )
    created = AuditLog.objects.get(action="create", entity_type="core.role", entity_id=role.id)
    assert created.after["name_en"] == "Auditor"


# --- immutability + isolation (NFR-5, PLT-1) --------------------------------


def as_app_role() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {APP_ROLE}")


def scope_to(tenant_id) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.tenant_id', %s, true)", [str(tenant_id)])


def test_app_role_cannot_update_or_delete_audit_rows() -> None:
    tenant = TenantFactory()
    entry = audit.log_event("probe", tenant_id=tenant.id)

    as_app_role()
    scope_to(tenant.id)

    with pytest.raises(DatabaseError, match="permission denied"):
        with transaction.atomic():
            AuditLog.objects.filter(id=entry.id).update(action="tampered")
    with pytest.raises(DatabaseError, match="permission denied"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM core_auditlog")


def test_audit_rows_are_tenant_isolated() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    audit.log_event("a.event", tenant_id=tenant_a.id)
    audit.log_event("b.event", tenant_id=tenant_b.id)

    as_app_role()
    scope_to(tenant_a.id)

    assert [e.action for e in AuditLog.objects.all()] == ["a.event"]


def test_monthly_partitions_exist_and_command_is_idempotent() -> None:
    from django.core.management import call_command

    call_command("ensure_audit_partitions", "--ahead", "1")
    call_command("ensure_audit_partitions", "--ahead", "1")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_inherits WHERE inhparent = 'core_auditlog'::regclass"
        )
        partition_count = cursor.fetchone()[0]
    assert partition_count >= 3  # DEFAULT + current month + at least one ahead


# --- viewer (PLT-5: Clinic Admin, own tenant, filters) -----------------------


@pytest.fixture
def admin_client_and_tenant():
    tenant = TenantFactory(subdomain="alpha")
    admin = UserFactory(tenant=tenant, username="admin1")
    UserRoleFactory(
        tenant=tenant, user=admin, role=RoleFactory(tenant=tenant, permissions=["admin.view_audit"])
    )
    client = Client()
    access = client.post(
        "/api/v1/auth/login/",
        {"username": "admin1", "password": PASSWORD},
        content_type="application/json",
        headers={"X-Tenant": "alpha"},
    ).json()["access"]
    headers = {"X-Tenant": "alpha", "Authorization": f"Bearer {access}"}
    return client, tenant, headers


def test_audit_view_lists_own_tenant_with_filters(admin_client_and_tenant) -> None:
    client, tenant, headers = admin_client_and_tenant
    audit.log_event("claim.submitted", tenant_id=tenant.id)
    audit.log_event("claim.submitted", tenant_id=TenantFactory().id)  # other tenant

    response = client.get("/api/v1/audit-logs/", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"results", "next", "prev"}
    actions = [row["action"] for row in body["results"]]
    assert actions.count("claim.submitted") == 1  # other tenant's row invisible
    assert "auth.login" in actions  # the admin's own login

    filtered = client.get("/api/v1/audit-logs/?action=claim.submitted", headers=headers)
    assert [row["action"] for row in filtered.json()["results"]] == ["claim.submitted"]

    bad = client.get("/api/v1/audit-logs/?date_from=not-a-date", headers=headers)
    assert bad.status_code == 400
    assert bad.json()["code"] == "validation.invalid"


def test_audit_view_requires_permission(admin_client_and_tenant) -> None:
    client, tenant, headers = admin_client_and_tenant
    UserFactory(tenant=tenant, username="nobody1")
    access = (
        Client()
        .post(
            "/api/v1/auth/login/",
            {"username": "nobody1", "password": PASSWORD},
            content_type="application/json",
            headers={"X-Tenant": "alpha"},
        )
        .json()["access"]
    )
    response = client.get(
        "/api/v1/audit-logs/",
        headers={"X-Tenant": "alpha", "Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "auth.permission_denied"

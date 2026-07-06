"""Cross-tenant isolation proof (PLT-1): with the app DB role active, a
deliberately unscoped ORM query can never see another tenant's rows — RLS is
the backstop even when application scoping is bypassed entirely.

Test data is created first on the default (owner/superuser) connection, which
bypasses RLS; assertions then run under `SET LOCAL ROLE sehaerp_app`.
"""

import uuid

import pytest
from django.db import DatabaseError, connection, transaction

from core.db import APP_ROLE
from core.models import Branch, Entitlement
from core.tests.factories import BranchFactory, EntitlementFactory, TenantFactory, UserFactory

pytestmark = pytest.mark.django_db


def as_app_role() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {APP_ROLE}")


def scope_to(tenant_id: uuid.UUID | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )


def test_unscoped_query_only_sees_current_tenant() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    branch_a = BranchFactory(tenant=tenant_a)
    branch_b = BranchFactory(tenant=tenant_b)

    as_app_role()

    scope_to(tenant_a.id)
    visible = list(Branch.objects.all())  # deliberately unscoped ORM call
    assert visible == [branch_a]

    scope_to(tenant_b.id)
    visible = list(Branch.objects.all())
    assert visible == [branch_b]


def test_no_tenant_scope_fails_closed() -> None:
    BranchFactory()
    EntitlementFactory()

    as_app_role()
    scope_to(None)

    assert Branch.objects.count() == 0
    assert Entitlement.objects.count() == 0


def test_entitlements_isolated_per_tenant() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    EntitlementFactory(tenant=tenant_a, feature_code="pharmacy")
    EntitlementFactory(tenant=tenant_b, feature_code="lab")

    as_app_role()
    scope_to(tenant_a.id)

    codes = list(Entitlement.objects.values_list("feature_code", flat=True))
    assert codes == ["pharmacy"]


def test_insert_for_other_tenant_is_rejected() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()

    as_app_role()
    scope_to(tenant_a.id)

    with pytest.raises(DatabaseError, match="row-level security"):
        with transaction.atomic():
            Branch.objects.create(tenant=tenant_b, name_en="Smuggled", name_ar="مهرب")


def test_update_cannot_move_row_to_other_tenant() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    branch_a = BranchFactory(tenant=tenant_a)

    as_app_role()
    scope_to(tenant_a.id)

    with pytest.raises(DatabaseError, match="row-level security"):
        with transaction.atomic():
            Branch.objects.filter(pk=branch_a.pk).update(tenant=tenant_b)


def test_platform_admins_visible_in_any_scope_but_tenant_users_isolated() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    user_a = UserFactory(tenant=tenant_a)
    UserFactory(tenant=tenant_b)
    platform_admin = UserFactory(tenant=None)

    from core.models import User

    as_app_role()
    scope_to(tenant_a.id)

    visible = set(User.objects.all())
    assert visible == {user_a, platform_admin}

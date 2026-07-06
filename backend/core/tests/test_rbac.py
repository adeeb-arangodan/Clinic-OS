"""PLT-4: role templates, permission resolution, RequiresPermission /
RequiresEntitlement (PLT-2, CLAUDE.md rule 9)."""

import pytest
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from core import selectors, services
from core.errors import ApiError
from core.models import Role
from core.permissions import RequiresEntitlement, RequiresPermission
from core.rbac import ALL_PERMISSION_CODES, ROLE_TEMPLATES
from core.tests.factories import (
    EntitlementFactory,
    RoleFactory,
    TenantFactory,
    UserFactory,
    UserRoleFactory,
)

pytestmark = pytest.mark.django_db


def _view_requiring(permission_class) -> type[APIView]:
    class _View(APIView):
        permission_classes = [permission_class]

        def get(self, request):
            return Response({"ok": True})

    return _View


def _get(view: type[APIView], user=None, tenant=None):
    request = APIRequestFactory().get("/probe/")
    request.tenant = tenant
    if user is not None:
        force_authenticate(request, user=user)
    return view.as_view()(request)


# --- role templates -------------------------------------------------------


def test_seed_role_templates_creates_all_srs_roles_idempotently() -> None:
    tenant = TenantFactory()
    services.seed_role_templates(tenant=tenant)
    services.seed_role_templates(tenant=tenant)  # second run must not duplicate

    roles = Role.objects.filter(tenant=tenant)
    assert roles.count() == len(ROLE_TEMPLATES) == 13
    assert all(role.is_system and role.name_ar for role in roles)


def test_template_codes_are_all_registered() -> None:
    for _, _, codes in ROLE_TEMPLATES:
        assert set(codes) <= ALL_PERMISSION_CODES


def test_permission_codes_union_across_roles() -> None:
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    UserRoleFactory(
        tenant=tenant, user=user, role=RoleFactory(tenant=tenant, permissions=["billing.view"])
    )
    UserRoleFactory(
        tenant=tenant,
        user=user,
        role=RoleFactory(tenant=tenant, permissions=["billing.refund", "reports.view"]),
    )

    assert selectors.permission_codes_for_user(user) == {
        "billing.view",
        "billing.refund",
        "reports.view",
    }


def test_create_role_rejects_unknown_codes() -> None:
    tenant = TenantFactory()
    with pytest.raises(ApiError) as excinfo:
        services.create_role(
            tenant=tenant, name_en="X", name_ar="س", permissions=["billing.teleport"]
        )
    assert excinfo.value.envelope_code == "validation.invalid"


def test_assign_role_rejects_cross_tenant() -> None:
    role = RoleFactory()
    outsider = UserFactory()  # different tenant
    with pytest.raises(ApiError):
        services.assign_role(user=outsider, role=role)


# --- DRF permission classes ------------------------------------------------


def test_requires_permission_allows_and_denies() -> None:
    tenant = TenantFactory()
    cashier = UserFactory(tenant=tenant)
    UserRoleFactory(
        tenant=tenant,
        user=cashier,
        role=RoleFactory(tenant=tenant, permissions=["billing.refund"]),
    )
    nurse = UserFactory(tenant=tenant)

    view = _view_requiring(RequiresPermission("billing.refund"))
    assert _get(view, user=cashier, tenant=tenant).status_code == 200
    assert _get(view, user=nurse, tenant=tenant).status_code == 403


def test_requires_permission_rejects_unregistered_code_at_definition() -> None:
    with pytest.raises(ValueError):
        RequiresPermission("billing.teleport")


def test_requires_entitlement_checks_tenant_feature() -> None:
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    EntitlementFactory(tenant=tenant, feature_code="nphies", enabled=True)
    view = _view_requiring(RequiresEntitlement("nphies"))

    assert _get(view, user=user, tenant=tenant).status_code == 200

    bare_tenant = TenantFactory()
    response = _get(view, user=UserFactory(tenant=bare_tenant), tenant=bare_tenant)
    assert response.status_code == 403
    assert response.data["code"] == "entitlement.not_enabled"

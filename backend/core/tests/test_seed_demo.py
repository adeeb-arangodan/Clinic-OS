"""seed_demo: idempotent demo data (CLAUDE.md M0 / definition of done)."""

import pytest
from django.core.management import call_command
from django.test import Client

from core.management.commands.seed_demo import DEMO_PASSWORD, DEMO_SUBDOMAIN
from core.models import Branch, Entitlement, Role, Tenant, User, UserRole
from core.rbac import ROLE_TEMPLATES

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_everything_idempotently() -> None:
    call_command("seed_demo")
    call_command("seed_demo")  # rerun must not duplicate or crash

    tenant = Tenant.objects.get(subdomain=DEMO_SUBDOMAIN)
    assert Branch.objects.filter(tenant=tenant).count() == 2
    assert Entitlement.objects.filter(tenant=tenant, enabled=True).count() >= 13
    assert Role.objects.filter(tenant=tenant).count() == len(ROLE_TEMPLATES)
    assert UserRole.objects.filter(tenant=tenant).count() == len(ROLE_TEMPLATES)
    assert User.objects.filter(tenant=tenant).count() == len(ROLE_TEMPLATES)
    assert User.objects.filter(username="platform.admin", tenant=None, is_superuser=True).exists()


def test_seeded_user_can_log_in_with_permissions() -> None:
    call_command("seed_demo")

    response = Client().post(
        "/api/v1/auth/login/",
        {"username": "demo.receptionist", "password": DEMO_PASSWORD},
        content_type="application/json",
        headers={"X-Tenant": DEMO_SUBDOMAIN},
    )

    assert response.status_code == 200
    permissions = response.json()["user"]["permissions"]
    assert "reception.register_patient" in permissions
    assert "emr.sign" not in permissions

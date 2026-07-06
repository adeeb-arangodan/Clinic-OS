"""Demo tenant + sample data (CLAUDE.md M0; definition-of-done requires every
feature to be demo-able on this data with mock adapters).

Idempotent — safe to rerun after every milestone; later milestones extend it
(patients, appointments, catalogs, …). Creates:
- tenant `demo` (PRO plan, all v1 entitlements enabled)
- two branches (Riyadh Main / Olaya)
- the 13 seeded role templates (PLT-4)
- one demo user per role (demo.<slug> / SehaDemo-1234) + a platform admin
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from core import services
from core.entitlements import ALL_V1_FEATURES
from core.models import Branch, Entitlement, Tenant, User
from core.rbac import ROLE_TEMPLATES

DEMO_SUBDOMAIN = "demo"
DEMO_PASSWORD = "SehaDemo-1234"  # dev/demo only — printed on completion


def _slug(role_name: str) -> str:
    return role_name.lower().replace(" ", "-")  # "Lab Supervisor" → demo.lab-supervisor


class Command(BaseCommand):
    help = "Create the demo tenant with branches, entitlements, roles and demo users."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        tenant, _ = Tenant.objects.get_or_create(
            subdomain=DEMO_SUBDOMAIN,
            defaults={
                "name": "Al-Shifa Clinics — عيادات الشفاء",
                "plan": Tenant.Plan.PRO,
                "vat_number": "310000000000003",
                "cr_number": "1010101010",
            },
        )

        for name_en, name_ar in [("Riyadh Main", "الرياض الرئيسي"), ("Olaya", "العليا")]:
            Branch.objects.get_or_create(
                tenant=tenant, name_en=name_en, defaults={"name_ar": name_ar}
            )

        for feature_code in ALL_V1_FEATURES:
            Entitlement.objects.get_or_create(
                tenant=tenant, feature_code=feature_code, defaults={"enabled": True}
            )

        roles = {role.name_en: role for role in services.seed_role_templates(tenant=tenant)}

        usernames = []
        for name_en, _, _ in ROLE_TEMPLATES:
            username = f"demo.{_slug(name_en)}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "tenant": tenant,
                    "email": f"{username}@demo.sehaerp.sa",
                    "first_name": name_en,
                    "last_name": "Demo",
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            services.assign_role(user=user, role=roles[name_en])
            usernames.append(username)

        platform_admin, created = User.objects.get_or_create(
            username="platform.admin",
            defaults={
                "tenant": None,  # vendor user (PLT-1)
                "email": "platform.admin@sehaerp.sa",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            platform_admin.set_password(DEMO_PASSWORD)
            platform_admin.save(update_fields=["password"])

        self.stdout.write(self.style.SUCCESS(f"Demo tenant ready: subdomain '{DEMO_SUBDOMAIN}'"))
        self.stdout.write(f"Users (password: {DEMO_PASSWORD}):")
        for username in [*usernames, "platform.admin"]:
            self.stdout.write(f"  {username}")

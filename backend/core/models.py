import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class UUIDModel(models.Model):
    """Platform-wide conventions: UUID PK + created/updated timestamps (docs/03 §1)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(UUIDModel):
    """A clinic (SaaS) or the single on-prem installation (PLT-1, PLT-3)."""

    class Plan(models.TextChoices):
        CORE = "core", "Core"
        PLUS = "plus", "Plus"
        PRO = "pro", "Pro"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        # Suspension is read-only grace mode, never a silent data lock (PLT-12).
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=200)
    subdomain = models.SlugField(max_length=63, unique=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.CORE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    default_locale = models.CharField(
        max_length=5, choices=[("en", "English"), ("ar", "العربية")], default="ar"
    )
    timezone = models.CharField(max_length=50, default="Asia/Riyadh")
    vat_number = models.CharField(max_length=20, blank=True)
    cr_number = models.CharField(max_length=20, blank=True)
    moh_license = models.CharField(max_length=50, blank=True)
    nphies_provider_id = models.CharField(max_length=50, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.subdomain})"


class User(AbstractUser, UUIDModel):
    """A user belongs to exactly one tenant; platform admins have tenant=NULL (PLT-1)."""

    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.PROTECT, related_name="users"
    )

    def __str__(self) -> str:
        return self.username


class Branch(UUIDModel):
    """Physical branch of a tenant; most transactional data is branch-scoped (PLT-1)."""

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="branches")
    name_en = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    zatca_config = models.JSONField(default=dict, blank=True)
    working_hours = models.JSONField(default=dict, blank=True)  # PLT-9
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name_en"], name="uniq_branch_name_tenant"),
        ]

    def __str__(self) -> str:
        return self.name_en


class Entitlement(UUIDModel):
    """Per-tenant feature toggle; server enforces, UI hides (PLT-2)."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="entitlements")
    feature_code = models.CharField(max_length=50)
    enabled = models.BooleanField(default=True)
    limits = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "feature_code"], name="uniq_entitlement_tenant_feature"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.feature_code}={'on' if self.enabled else 'off'}"


class AuthSession(UUIDModel):
    """One refresh-token lineage = one device/session; drives the PLT-6
    session list with revoke. `refresh_jti` follows the token across rotations.

    Platform-level like User (platform admins have tenant NULL), so not a
    TenantModel; `refresh_jti` is a token-issued UUID, unique by construction.
    """

    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_sessions"
    )
    refresh_jti = models.CharField(max_length=64, unique=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user_id}:{self.refresh_jti[:8]}"


class TenantModel(UUIDModel):
    """Abstract base for every domain model (CLAUDE.md rule 1).

    Every unique constraint on a subclass must be composite with tenant.
    RLS policies (core/db.py) are the backstop; queries must still be
    tenant-scoped in selectors.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="+")
    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class Role(TenantModel):
    """Permission bundle (PLT-4). Seeded from rbac.ROLE_TEMPLATES per tenant;
    tenants clone and customize (docs/01 §1). Codes validated against
    rbac.ALL_PERMISSION_CODES in the service layer.
    """

    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    permissions = models.JSONField(default=list)
    is_system = models.BooleanField(default=False)  # seeded template — rename/delete blocked

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name_en"], name="uniq_role_name_tenant"),
        ]

    def __str__(self) -> str:
        return self.name_en


class UserRole(TenantModel):
    """User↔Role assignment; explicit join model so the row is tenant-scoped."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user", "role"], name="uniq_userrole_tenant_user_role"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.role_id}"

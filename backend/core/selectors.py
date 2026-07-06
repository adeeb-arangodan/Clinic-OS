"""Read-side service layer for core (CLAUDE.md rule 2)."""

import uuid

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from core.models import AuthSession, Entitlement, Role, User


def permission_codes_for_user(user: User) -> frozenset[str]:
    """Union of permission codes across the user's roles, cached per instance
    (one DB hit per request even with several RequiresPermission checks)."""
    cached = getattr(user, "_permission_codes", None)
    if cached is not None:
        return cached
    role_permissions = Role.objects.filter(
        tenant_id=user.tenant_id, user_roles__user=user
    ).values_list("permissions", flat=True)
    codes = frozenset(code for permissions in role_permissions for code in permissions)
    user._permission_codes = codes
    return codes


def entitlement_enabled(tenant_id: uuid.UUID, feature_code: str) -> bool:
    return Entitlement.objects.filter(
        tenant_id=tenant_id, feature_code=feature_code, enabled=True
    ).exists()


def active_sessions_for_user(user: User) -> QuerySet[AuthSession]:
    """Sessions that can still refresh: not revoked, refresh not yet expired."""
    cutoff = timezone.now() - settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return user.auth_sessions.filter(
        revoked_at__isnull=True, last_refreshed_at__gte=cutoff
    ).order_by("-last_refreshed_at")

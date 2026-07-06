"""Read-side service layer for core (CLAUDE.md rule 2)."""

import uuid
from datetime import datetime

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from core.models import AuditLog, AuthSession, Entitlement, Role, User


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


def audit_logs(
    tenant_id: uuid.UUID,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> QuerySet[AuditLog]:
    """Clinic Admin audit view, own tenant only (PLT-5)."""
    logs = AuditLog.objects.filter(tenant_id=tenant_id)
    if action:
        logs = logs.filter(action=action)
    if entity_type:
        logs = logs.filter(entity_type=entity_type)
    if entity_id:
        logs = logs.filter(entity_id=entity_id)
    if actor_id:
        logs = logs.filter(actor_id=actor_id)
    if date_from:
        logs = logs.filter(created_at__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__lt=date_to)
    return logs

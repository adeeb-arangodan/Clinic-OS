"""DRF permission classes: RBAC (PLT-4) and entitlements (PLT-2, CLAUDE.md rule 9).

Usage on a view:
    permission_classes = [RequiresPermission("billing.refund")]
    permission_classes = [RequiresEntitlement("nphies"), RequiresPermission("claims.submit")]

The exception handler (core.errors) turns the denial `code` into the
bilingual error envelope.
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from core import selectors
from core.rbac import ALL_PERMISSION_CODES


def RequiresPermission(code: str) -> type[BasePermission]:  # noqa: N802 (class factory)
    if code not in ALL_PERMISSION_CODES:
        raise ValueError(f"Unknown permission code: {code}")

    class _RequiresPermission(BasePermission):
        code = "permission_denied"

        def has_permission(self, request: Request, view: APIView) -> bool:
            user = request.user
            if not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            return code in selectors.permission_codes_for_user(user)

    return _RequiresPermission


def RequiresEntitlement(feature_code: str) -> type[BasePermission]:  # noqa: N802 (class factory)
    class _RequiresEntitlement(BasePermission):
        code = "entitlement.not_enabled"

        def has_permission(self, request: Request, view: APIView) -> bool:
            tenant = getattr(request, "tenant", None)
            if tenant is None:
                return False
            return selectors.entitlement_enabled(tenant.id, feature_code)

    return _RequiresEntitlement

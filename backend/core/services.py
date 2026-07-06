"""Write-side service layer for core (CLAUDE.md rule 2).

Auth design (PLT-6, docs/02 §7): short-lived access JWT carrying `tenant`
(subdomain, read by TenantMiddleware) and `sid` (AuthSession id) claims;
rotating refresh token delivered in an httpOnly cookie by the view layer.
Every refresh blacklists the old token and moves the AuthSession's
`refresh_jti` forward, so one session row = one device, revocable from the
session list.
"""

import uuid
from dataclasses import dataclass

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core import audit
from core.errors import ApiError
from core.models import (
    AuthSession,
    IntegrationTransaction,
    NumberSequence,
    Role,
    Tenant,
    User,
    UserRole,
)
from core.rbac import ALL_PERMISSION_CODES, ROLE_TEMPLATES


@dataclass(frozen=True)
class TokenPair:
    user: User
    session: AuthSession
    access: str
    refresh: str


def _issue_tokens(user: User, session: AuthSession) -> TokenPair:
    refresh = RefreshToken.for_user(user)
    session.refresh_jti = refresh["jti"]
    session.last_refreshed_at = timezone.now()
    session.save(update_fields=["refresh_jti", "last_refreshed_at", "updated_at"])

    refresh["sid"] = str(session.id)
    if user.tenant_id is not None:
        refresh["tenant"] = user.tenant.subdomain
    return TokenPair(
        user=user, session=session, access=str(refresh.access_token), refresh=str(refresh)
    )


def login(
    *,
    request: HttpRequest,
    username: str,
    password: str,
    user_agent: str = "",
    ip_address: str | None = None,
) -> TokenPair:
    """Authenticate by username or email and open a new session.

    A tenant-resolved request only accepts that tenant's users (platform
    admins, tenant NULL, may log in anywhere). Mismatches answer exactly like
    bad credentials so tenant membership is never leaked.
    """
    if "@" in username:
        # RLS scopes this lookup to the resolved tenant + platform admins.
        match = User.objects.filter(email__iexact=username).values_list("username", flat=True)
        username = match.first() or username

    user = authenticate(request, username=username, password=password)
    invalid = ApiError("auth.invalid_credentials", status.HTTP_401_UNAUTHORIZED)
    if user is None:
        raise invalid
    tenant: Tenant | None = getattr(request, "tenant", None)
    if tenant is not None and user.tenant_id is not None and user.tenant_id != tenant.id:
        raise invalid

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    session = AuthSession.objects.create(
        tenant_id=user.tenant_id,
        user=user,
        refresh_jti=uuid.uuid4().hex,  # placeholder; _issue_tokens sets the real jti
        user_agent=user_agent[:300],
        ip_address=ip_address,
    )
    audit.log_event("auth.login", instance=user, actor=user, tenant_id=user.tenant_id)
    return _issue_tokens(user, session)


def refresh_session(*, request: HttpRequest, raw_refresh: str) -> TokenPair:
    """Rotate the refresh token: blacklist the old one, keep the same session."""
    invalid = ApiError("auth.token_invalid", status.HTTP_401_UNAUTHORIZED)
    try:
        old = RefreshToken(raw_refresh)  # verifies signature, expiry and blacklist
    except TokenError:
        raise invalid from None

    tenant: Tenant | None = getattr(request, "tenant", None)
    if tenant is not None and old.get("tenant") not in (None, tenant.subdomain):
        raise invalid

    user = User.objects.filter(id=old["user_id"], is_active=True).first()
    session = AuthSession.objects.filter(refresh_jti=old["jti"], revoked_at__isnull=True).first()
    if user is None or session is None or session.user_id != user.id:
        raise invalid

    old.blacklist()
    return _issue_tokens(user, session)


def logout(*, raw_refresh: str) -> None:
    """Blacklist the presented refresh token and close its session. Idempotent:
    an expired/garbage token still logs out cleanly (cookie gets cleared)."""
    try:
        token = RefreshToken(raw_refresh)
    except TokenError:
        return
    token.blacklist()
    session = AuthSession.objects.filter(refresh_jti=token["jti"], revoked_at__isnull=True).first()
    if session is not None:
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        audit.log_event(
            "auth.logout",
            instance=session.user,
            actor=session.user,
            tenant_id=session.tenant_id,
        )


def revoke_session(*, user: User, session_id: uuid.UUID) -> AuthSession:
    """Revoke one of the caller's own sessions (device list, PLT-6)."""
    session = AuthSession.objects.filter(id=session_id, user=user, revoked_at__isnull=True).first()
    if session is None:
        raise ApiError("session.not_found", status.HTTP_404_NOT_FOUND)

    outstanding = OutstandingToken.objects.filter(jti=session.refresh_jti).first()
    if outstanding is not None:
        BlacklistedToken.objects.get_or_create(token=outstanding)
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at", "updated_at"])
    audit.log_event("auth.session_revoked", instance=session, tenant_id=session.tenant_id)
    return session


def seed_role_templates(*, tenant: Tenant) -> list[Role]:
    """Create the standard role templates for a tenant (PLT-4). Idempotent:
    existing roles (matched on name_en) are left untouched — tenants customize."""
    roles = []
    created_names = []
    for name_en, name_ar, codes in ROLE_TEMPLATES:
        role, created = Role.objects.get_or_create(
            tenant=tenant,
            name_en=name_en,
            defaults={"name_ar": name_ar, "permissions": codes, "is_system": True},
        )
        roles.append(role)
        if created:
            created_names.append(name_en)
    if created_names:
        audit.log_event("roles.seeded", tenant_id=tenant.id, after={"created": created_names})
    return roles


def assign_role(*, user: User, role: Role) -> UserRole:
    if user.tenant_id is None or user.tenant_id != role.tenant_id:
        raise ApiError(
            "validation.invalid", field_errors={"role": ["Role belongs to another tenant."]}
        )
    user_role, created = UserRole.objects.get_or_create(
        tenant_id=role.tenant_id, user=user, role=role
    )
    if created:
        audit.log_create(user_role)
    return user_role


def next_number(*, tenant_id: uuid.UUID, key: str, branch_id: uuid.UUID | None = None) -> int:
    """Allocate the next value of a per-tenant/branch counter (docs/03 §4.6).

    SELECT ... FOR UPDATE serializes concurrent allocations on the same
    counter row: no duplicates, no gaps. Runs in its own transaction — call it
    inside the business transaction that consumes the number (e.g. invoice
    finalization) so an aborted caller doesn't burn a value silently.
    """
    with transaction.atomic():
        sequence = (
            NumberSequence.objects.select_for_update()
            .filter(tenant_id=tenant_id, key=key, branch_id=branch_id)
            .first()
        )
        if sequence is None:
            try:
                with transaction.atomic():  # savepoint: survive a create race
                    sequence = NumberSequence.objects.create(
                        tenant_id=tenant_id, key=key, branch_id=branch_id
                    )
            except IntegrityError:
                sequence = NumberSequence.objects.select_for_update().get(
                    tenant_id=tenant_id, key=key, branch_id=branch_id
                )
        sequence.last_value += 1
        sequence.save(update_fields=["last_value", "updated_at"])
        return sequence.last_value


# --- IntegrationTransaction state machine (rules 3 + 7) ----------------------
# queued → processing → success | failed. Illegal transitions raise.

_TX_TRANSITIONS = {
    IntegrationTransaction.Status.QUEUED: {IntegrationTransaction.Status.PROCESSING},
    IntegrationTransaction.Status.PROCESSING: {
        IntegrationTransaction.Status.SUCCESS,
        IntegrationTransaction.Status.FAILED,
    },
}


class IllegalTransition(Exception):
    pass


def transition_transaction(
    tx: IntegrationTransaction,
    to_status: str,
    *,
    response: dict | None = None,
    error: str = "",
    external_ref: str = "",
) -> IntegrationTransaction:
    allowed = _TX_TRANSITIONS.get(IntegrationTransaction.Status(tx.status), set())
    if IntegrationTransaction.Status(to_status) not in allowed:
        raise IllegalTransition(f"{tx.status} → {to_status}")

    before = audit.snapshot(tx)
    tx.status = to_status
    if response is not None:
        tx.response = response
    if error:
        tx.error = error
    if external_ref:
        tx.external_ref = external_ref
    if to_status in (IntegrationTransaction.Status.SUCCESS, IntegrationTransaction.Status.FAILED):
        tx.finished_at = timezone.now()
    tx.save()
    audit.log_update(tx, before=before, action=f"integration.{to_status}")
    return tx


def queue_message(
    *,
    tenant: Tenant,
    user: User,
    phone: str,
    body: str,
    dedup_key: str,
) -> IntegrationTransaction:
    """Queue an outbound message through the messaging adapter (PLT-8).
    Idempotent: the same (tenant, dedup_key) returns the existing transaction
    instead of sending twice (rule 7)."""
    from core import tasks  # local import — tasks imports services

    tx, created = IntegrationTransaction.objects.get_or_create(
        tenant=tenant,
        dedup_key=dedup_key,
        defaults={
            "adapter": "messaging",
            "operation": "send_message",
            "request": {"phone": phone, "body": body},
            "created_by": user,
        },
    )
    if created:
        audit.log_create(tx, action="integration.queued")
        tasks.process_integration_transaction.delay(
            tenant_id=str(tenant.id), transaction_id=str(tx.id)
        )
    return tx


def create_role(*, tenant: Tenant, name_en: str, name_ar: str, permissions: list[str]) -> Role:
    unknown = sorted(set(permissions) - ALL_PERMISSION_CODES)
    if unknown:
        raise ApiError(
            "validation.invalid",
            field_errors={"permissions": [f"Unknown permission codes: {', '.join(unknown)}"]},
        )
    role = Role.objects.create(
        tenant=tenant, name_en=name_en, name_ar=name_ar, permissions=permissions
    )
    audit.log_create(role)
    return role

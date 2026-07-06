"""Audit trail hooks (PLT-5, CLAUDE.md rule 6): middleware + service-layer.

AuditContextMiddleware stashes the current request in a contextvar; the hooks
below stamp every row with actor / ip / user_agent / request_id from it, so
services only say *what* changed:

    before = audit.snapshot(role)
    role.name_en = "..."; role.save()
    audit.log_update(role, before=before)

Rows are written in the caller's transaction — an audit failure rolls back the
mutation, never the other way around. Celery tasks have no request context;
they pass `actor=` explicitly (or leave it None for system actions).
"""

import json
import uuid
from contextvars import ContextVar, Token
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import HttpRequest

from core.models import AuditLog, User
from core.tenancy import get_current_tenant_id

_audit_request: ContextVar[HttpRequest | None] = ContextVar("audit_request", default=None)


def set_request(request: HttpRequest | None) -> Token:
    return _audit_request.set(request)


def reset_request(token: Token) -> None:
    _audit_request.reset(token)


def snapshot(instance: models.Model) -> dict[str, Any]:
    """JSON-safe dict of the instance's concrete fields; take one *before*
    mutating, pass it to log_update afterwards."""
    data = {
        field.attname: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if field.attname != "password"  # never audit credential hashes
    }
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def log_create(instance: models.Model, *, action: str = "create") -> AuditLog:
    return _write(action=action, instance=instance, after=snapshot(instance))


def log_update(
    instance: models.Model, *, before: dict[str, Any], action: str = "update"
) -> AuditLog | None:
    """Diff against a pre-mutation snapshot; stores changed fields only.
    Returns None when nothing changed (timestamps excluded)."""
    current = snapshot(instance)
    changed = {
        field
        for field in before.keys() | current.keys()
        if before.get(field) != current.get(field) and field != "updated_at"
    }
    if not changed:
        return None
    return _write(
        action=action,
        instance=instance,
        before={field: before.get(field) for field in sorted(changed)},
        after={field: current.get(field) for field in sorted(changed)},
    )


def log_delete(instance: models.Model, *, action: str = "delete") -> AuditLog:
    return _write(action=action, instance=instance, before=snapshot(instance))


def log_event(
    action: str,
    *,
    instance: models.Model | None = None,
    actor: User | None = None,
    tenant_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    """Free-form event (state transitions, auth events): action is
    `module.event`, e.g. "auth.login", "claim.submitted"."""
    return _write(
        action=action,
        instance=instance,
        actor=actor,
        tenant_id=tenant_id,
        branch_id=branch_id,
        before=before,
        after=after,
    )


def _write(
    *,
    action: str,
    instance: models.Model | None = None,
    actor: User | None = None,
    tenant_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    request = _audit_request.get()
    if actor is None and request is not None:
        request_user = getattr(request, "user", None)
        if request_user is not None and request_user.is_authenticated:
            actor = request_user

    if instance is not None:
        tenant_id = tenant_id or getattr(instance, "tenant_id", None)
        branch_id = branch_id or getattr(instance, "branch_id", None)

    return AuditLog.objects.create(
        tenant_id=tenant_id or get_current_tenant_id(),
        branch_id=branch_id,
        actor=actor,
        action=action,
        entity_type=instance._meta.label_lower if instance is not None else "",
        entity_id=instance.pk if instance is not None else None,
        before=before,
        after=after,
        ip=request.META.get("REMOTE_ADDR") if request is not None else None,
        user_agent=(request.headers.get("User-Agent", "") if request is not None else "")[:300],
        request_id=getattr(request, "request_id", None),
    )

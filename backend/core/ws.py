"""Websocket foundation (docs/02 §4, docs/03 §3).

Browsers cannot set an Authorization header on websocket connects, so the
access JWT travels as a `?token=` query parameter and is validated here by
JWTAuthMiddleware before any consumer runs.

Group naming: channel-layer group names forbid `:`; the docs' conceptual
`tenant:user` group is spelled `user-alerts.{tenant_hex}.{user_hex}`.
`push_user_alert` is the sync entry point services and Celery tasks use to
deliver `user.alerts` / `integration.status` events.
"""

import uuid
from typing import Any
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from core.models import User


def user_alerts_group(tenant_id: uuid.UUID | None, user_id: uuid.UUID) -> str:
    tenant_part = tenant_id.hex if tenant_id else "platform"
    return f"user-alerts.{tenant_part}.{user_id.hex}"


def push_user_alert(
    *, tenant_id: uuid.UUID | None, user_id: uuid.UUID, topic: str, payload: dict[str, Any]
) -> None:
    """Send an event to one user's sockets. topic: "user.alerts" or
    "integration.status" (docs/03 §3). Fire-and-forget: no-op if offline."""
    async_to_sync(get_channel_layer().group_send)(
        user_alerts_group(tenant_id, user_id),
        {"type": "alert", "data": {"topic": topic, **payload}},
    )


@database_sync_to_async
def _user_for_token(raw_token: str) -> User | None:
    try:
        access = AccessToken(raw_token)
    except TokenError:
        return None
    return User.objects.filter(id=access["user_id"], is_active=True).first()


class JWTAuthMiddleware:
    """Populates scope["user"] from the `?token=` access JWT (None if absent
    or invalid — consumers decide to reject, mirroring DRF's flow)."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def __call__(self, scope: dict, receive: Any, send: Any) -> Any:
        params = parse_qs(scope.get("query_string", b"").decode())
        raw_token = (params.get("token") or [""])[0]
        scope["user"] = await _user_for_token(raw_token) if raw_token else None
        return await self.inner(scope, receive, send)

"""Websocket consumers (docs/02 §4). The queue.{dept} consumer for live token
boards lands with the live queue in M1 (REC-7)."""

from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from core.ws import user_alerts_group

WS_CLOSE_UNAUTHORIZED = 4401  # app-level close code, mirrors HTTP 401


class UserAlertsConsumer(AsyncJsonWebsocketConsumer):
    """Personal event stream: `user.alerts` + `integration.status` topics
    delivered to the caller's `tenant:user` group. Server-push only."""

    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None:
            await self.close(code=WS_CLOSE_UNAUTHORIZED)
            return
        self.group = user_alerts_group(user.tenant_id, user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def alert(self, event: dict[str, Any]) -> None:
        await self.send_json(event["data"])

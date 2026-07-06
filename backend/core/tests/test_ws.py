"""D6 websocket foundation: JWT handshake auth, personal alert delivery,
cross-user isolation (docs/02 §4, docs/03 §3).

transaction=True because consumer DB lookups run on another thread's
connection; scenarios run via asyncio.run to stay on the stock test stack.
"""

import asyncio

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from core.consumers import WS_CLOSE_UNAUTHORIZED
from core.tests.factories import UserFactory
from core.ws import push_user_alert

pytestmark = pytest.mark.django_db(transaction=True)


def access_token_for(user) -> str:
    return str(RefreshToken.for_user(user).access_token)


def test_unauthenticated_connect_is_rejected() -> None:
    async def scenario() -> None:
        for path in ["/ws/alerts/", "/ws/alerts/?token=garbage"]:
            communicator = WebsocketCommunicator(application, path)
            connected, close_code = await communicator.connect()
            assert not connected
            assert close_code == WS_CLOSE_UNAUTHORIZED
            await communicator.disconnect()

    asyncio.run(scenario())


def test_authenticated_user_receives_pushed_alert() -> None:
    user = UserFactory()
    token = access_token_for(user)

    async def scenario() -> None:
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, _ = await communicator.connect()
        assert connected

        # push_user_alert is the sync API services/Celery use; call it as they would
        await sync_to_async(push_user_alert)(
            tenant_id=user.tenant_id,
            user_id=user.id,
            topic="user.alerts",
            payload={"kind": "lab.critical_value", "order_id": "123"},
        )

        message = await communicator.receive_json_from()
        assert message == {
            "topic": "user.alerts",
            "kind": "lab.critical_value",
            "order_id": "123",
        }
        await communicator.disconnect()

    asyncio.run(scenario())


def test_alerts_are_not_delivered_to_other_users() -> None:
    user, other = UserFactory(), UserFactory()
    token = access_token_for(user)

    async def scenario() -> None:
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, _ = await communicator.connect()
        assert connected

        await sync_to_async(push_user_alert)(
            tenant_id=other.tenant_id,
            user_id=other.id,
            topic="integration.status",
            payload={"kind": "claim.response"},
        )

        assert await communicator.receive_nothing(timeout=0.2)
        await communicator.disconnect()

    asyncio.run(scenario())


def test_inactive_user_token_is_rejected() -> None:
    user = UserFactory(is_active=False)
    token = access_token_for(user)

    async def scenario() -> None:
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == WS_CLOSE_UNAUTHORIZED
        await communicator.disconnect()

    asyncio.run(scenario())

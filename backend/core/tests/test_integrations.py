"""IntegrationTransaction + mock adapter (rule 7): idempotent queueing, the
queued→processing→success/failed state machine (rule 3), audit coverage, and
the async status-chip pattern delivered over the integration.status websocket
topic — end to end with Celery eager mode."""

import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from core import services
from core.adapters import get_adapter
from core.adapters.mock import MockMessagingAdapter
from core.models import AuditLog, IntegrationTransaction
from core.services import IllegalTransition, transition_transaction
from core.tests.factories import TenantFactory, UserFactory

pytestmark = pytest.mark.django_db

Status = IntegrationTransaction.Status


@pytest.fixture
def tenant():
    return TenantFactory()


@pytest.fixture
def user(tenant):
    return UserFactory(tenant=tenant)


def test_mock_adapter_is_configured() -> None:
    get_adapter.cache_clear()
    assert isinstance(get_adapter("messaging"), MockMessagingAdapter)


def test_queue_message_runs_to_success(tenant, user) -> None:
    tx = services.queue_message(
        tenant=tenant, user=user, phone="+966500000001", body="Reminder", dedup_key="appt-1-remind"
    )

    tx.refresh_from_db()
    assert tx.status == Status.SUCCESS  # CELERY_TASK_ALWAYS_EAGER
    assert tx.external_ref.startswith("mock-msg-")
    assert tx.attempts == 1
    assert tx.finished_at is not None


def test_queue_message_is_idempotent_on_dedup_key(tenant, user) -> None:
    first = services.queue_message(
        tenant=tenant, user=user, phone="+966500000001", body="Hi", dedup_key="dup-1"
    )
    second = services.queue_message(
        tenant=tenant, user=user, phone="+966500000001", body="Hi", dedup_key="dup-1"
    )

    assert first.id == second.id
    assert IntegrationTransaction.objects.filter(tenant=tenant, dedup_key="dup-1").count() == 1
    first.refresh_from_db()
    assert first.attempts == 1  # the duplicate call did not re-send


def test_failure_scenario_marks_failed(tenant, user) -> None:
    tx = services.queue_message(
        tenant=tenant, user=user, phone="+966500009999", body="Hi", dedup_key="fail-1"
    )

    tx.refresh_from_db()
    assert tx.status == Status.FAILED
    assert "unreachable" in tx.error


def test_illegal_transitions_raise(tenant, user) -> None:
    tx = IntegrationTransaction.objects.create(
        tenant=tenant, adapter="messaging", operation="send_message", dedup_key="sm-1"
    )
    with pytest.raises(IllegalTransition):
        transition_transaction(tx, Status.SUCCESS)  # queued → success skips processing

    transition_transaction(tx, Status.PROCESSING)
    transition_transaction(tx, Status.SUCCESS)
    with pytest.raises(IllegalTransition):
        transition_transaction(tx, Status.FAILED)  # terminal states are final


def test_transitions_are_audit_logged(tenant, user) -> None:
    services.queue_message(
        tenant=tenant, user=user, phone="+966500000001", body="Hi", dedup_key="audit-1"
    )

    actions = set(
        AuditLog.objects.filter(
            tenant=tenant, entity_type="core.integrationtransaction"
        ).values_list("action", flat=True)
    )
    assert {"integration.queued", "integration.processing", "integration.success"} <= actions


@pytest.mark.django_db(transaction=True)
def test_status_chip_events_arrive_over_websocket() -> None:
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    token = str(RefreshToken.for_user(user).access_token)

    async def scenario() -> None:
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, _ = await communicator.connect()
        assert connected

        from asgiref.sync import sync_to_async

        tx = await sync_to_async(services.queue_message)(
            tenant=tenant, user=user, phone="+966500000001", body="Hi", dedup_key="ws-1"
        )

        first = await communicator.receive_json_from()
        second = await communicator.receive_json_from()
        assert [first["status"], second["status"]] == ["processing", "success"]
        assert first["topic"] == second["topic"] == "integration.status"
        assert second["transaction_id"] == str(tx.id)
        await communicator.disconnect()

    asyncio.run(scenario())

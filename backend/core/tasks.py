"""Celery tasks. Every task takes tenant_id explicitly and wraps its DB work
in tenant_scope (CLAUDE.md rule 1); external calls happen only here, never in
a request (rule 7)."""

import uuid

from celery import shared_task

from core import services
from core.adapters import get_adapter
from core.models import IntegrationTransaction
from core.tenancy import tenant_scope
from core.ws import push_user_alert


def _notify(tx: IntegrationTransaction) -> None:
    """integration.status websocket event → async status chip (docs/03 §3)."""
    if tx.created_by_id is None:
        return
    push_user_alert(
        tenant_id=tx.tenant_id,
        user_id=tx.created_by_id,
        topic="integration.status",
        payload={
            "transaction_id": str(tx.id),
            "adapter": tx.adapter,
            "operation": tx.operation,
            "status": tx.status,
        },
    )


@shared_task(bind=True, max_retries=3)
def process_integration_transaction(self, *, tenant_id: str, transaction_id: str) -> None:
    with tenant_scope(uuid.UUID(tenant_id)):
        tx = IntegrationTransaction.objects.get(id=transaction_id, tenant_id=tenant_id)
        if tx.status != IntegrationTransaction.Status.QUEUED:
            return  # idempotent: replayed deliveries are no-ops

        services.transition_transaction(tx, IntegrationTransaction.Status.PROCESSING)
        tx.attempts += 1
        tx.save(update_fields=["attempts", "updated_at"])
        _notify(tx)

        adapter = get_adapter(tx.adapter)
        result = adapter.send(**tx.request)

        if result.ok:
            services.transition_transaction(
                tx,
                IntegrationTransaction.Status.SUCCESS,
                response=result.response,
                external_ref=result.external_ref,
            )
        else:
            services.transition_transaction(
                tx, IntegrationTransaction.Status.FAILED, error=result.error
            )
        _notify(tx)

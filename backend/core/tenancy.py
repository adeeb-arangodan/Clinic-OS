"""Tenant scoping: request/task context + the `app.tenant_id` Postgres GUC.

The GUC drives the RLS policies (core/db.py). `set_config(..., is_local=true)`
is the parameterizable equivalent of `SET LOCAL app.tenant_id`, so scoping is
always transaction-bound: it can never leak onto a pooled connection.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import connection, transaction

_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> uuid.UUID | None:
    return _current_tenant_id.get()


def set_db_tenant(tenant_id: uuid.UUID) -> None:
    """SET LOCAL app.tenant_id — caller must already be inside a transaction."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.tenant_id', %s, true)", [str(tenant_id)])


@contextmanager
def tenant_scope(tenant_id: uuid.UUID) -> Iterator[None]:
    """Run a block tenant-scoped: contextvar + transaction + SET LOCAL.

    Celery tasks receive tenant_id explicitly (CLAUDE.md rule 1) and wrap
    their DB work in this; TenantMiddleware wraps each tenant request in it.
    """
    token = _current_tenant_id.set(tenant_id)
    try:
        with transaction.atomic():
            set_db_tenant(tenant_id)
            yield
    finally:
        _current_tenant_id.reset(token)

"""NumberSequence (docs/03 §4.6): per-tenant/branch counters, gapless and
collision-free under concurrency via SELECT ... FOR UPDATE."""

import threading

import pytest
from django.db import connection

from core import services
from core.tests.factories import BranchFactory, TenantFactory

pytestmark = pytest.mark.django_db


def test_sequences_increment_per_key_and_branch() -> None:
    tenant = TenantFactory()
    branch = BranchFactory(tenant=tenant)

    assert services.next_number(tenant_id=tenant.id, key="invoice") == 1
    assert services.next_number(tenant_id=tenant.id, key="invoice") == 2
    # a different key and a branch-scoped counter start fresh
    assert services.next_number(tenant_id=tenant.id, key="mrn") == 1
    assert services.next_number(tenant_id=tenant.id, key="invoice", branch_id=branch.id) == 1


def test_sequences_are_per_tenant() -> None:
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    services.next_number(tenant_id=tenant_a.id, key="invoice")
    services.next_number(tenant_id=tenant_a.id, key="invoice")

    assert services.next_number(tenant_id=tenant_b.id, key="invoice") == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_allocation_never_duplicates() -> None:
    """8 threads × 25 allocations on one counter: every value unique, none
    skipped. Each thread uses its own DB connection, so FOR UPDATE is doing
    the serialization — not Python."""
    tenant = TenantFactory()
    threads, per_thread = 8, 25
    allocated: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        values = []
        try:
            for _ in range(per_thread):
                values.append(services.next_number(tenant_id=tenant.id, key="invoice"))
        finally:
            connection.close()
        with lock:
            allocated.extend(values)

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for thread in pool:
        thread.start()
    for thread in pool:
        thread.join()

    expected = threads * per_thread
    assert len(allocated) == expected
    assert sorted(allocated) == list(range(1, expected + 1))  # unique AND gapless

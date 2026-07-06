"""Mock adapters: deterministic, offline, scenario-switchable through the
payload itself so tests and demos exercise failure paths (rule 7)."""

import uuid

from core.adapters.base import AdapterResult, MessagingAdapter

# Phone numbers ending in this suffix make the mock fail deterministically.
FAIL_SUFFIX = "9999"


class MockMessagingAdapter(MessagingAdapter):
    def send(self, *, phone: str, body: str) -> AdapterResult:
        if phone.endswith(FAIL_SUFFIX):
            return AdapterResult(ok=False, error="mock: destination unreachable")
        return AdapterResult(
            ok=True,
            external_ref=f"mock-msg-{uuid.uuid4().hex[:10]}",
            response={"delivered_to": phone, "length": len(body)},
        )

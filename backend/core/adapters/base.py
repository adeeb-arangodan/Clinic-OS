from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AdapterResult:
    """Uniform adapter outcome stored on IntegrationTransaction."""

    ok: bool
    external_ref: str = ""
    response: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class MessagingAdapter(ABC):
    """SMS/WhatsApp delivery (PLT-8). Real providers (M-later) implement this
    same interface; selection is per-deployment via settings.ADAPTERS."""

    @abstractmethod
    def send(self, *, phone: str, body: str) -> AdapterResult: ...

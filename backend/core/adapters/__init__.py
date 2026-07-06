"""Adapter registry (CLAUDE.md rule 7): every external system is reached
through an interface with a working Mock implementation, selected via
settings.ADAPTERS — no feature may require live credentials to develop,
demo, or test."""

from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string

from core.adapters.base import MessagingAdapter

__all__ = ["MessagingAdapter", "get_adapter"]


@cache
def get_adapter(name: str):
    """Instantiate the configured adapter, e.g. get_adapter("messaging")."""
    return import_string(settings.ADAPTERS[name])()

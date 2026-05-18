"""Context examples service.

Cache management has moved into each ContextProvider implementation.
This module is now a thin coordination layer.
"""
from __future__ import annotations

from typing import Any

from app.providers.provider import ProviderCapability
from app.providers.registry import get_provider_by_code
from app.providers.types.context import ContextProvider


async def get_context_examples(
    text: str,
    source_lang: str,
    target_lang: str,
    provider_code: str | None = None,
) -> list[dict[str, Any]]:
    """Return context examples for *text* from the given provider.

    Cache lookup and persistence are handled by the provider itself.
    Returns ``[]`` when the provider is unknown or unsupported.  Provider
    exceptions (network errors etc.) are caught and returned as empty so
    the UI degrades gracefully; the provider will have already stored a
    failure entry to prevent repeated hammering.
    """
    if provider_code is None:
        return []
    p = get_provider_by_code(provider_code)
    if p is None or ProviderCapability.CONTEXT not in p.supported_capabilities():
        return []
    if not isinstance(p, ContextProvider):
        return []
    return await p.get_context_examples(text, source_lang, target_lang)

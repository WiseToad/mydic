"""Definition service.

Cache management has moved into each DefinitionProvider implementation.
This module is now a thin coordination layer.
"""
from __future__ import annotations

from typing import Any

from app.providers.provider import ProviderCapability
from app.providers.registry import get_provider_by_code
from app.providers.types.definition import DefinitionProvider


async def get_definition(
    word: str,
    lang: str,
    provider_code: str | None = None,
) -> dict[str, Any] | None:
    """Return a definition for *word* in *lang* from the given provider.

    Cache lookup and persistence are handled by the provider itself.
    Returns ``None`` when the provider is unknown, unsupported, or the word
    was not found.  Re-raises provider exceptions (e.g. network errors) so
    callers can handle them appropriately.
    """
    if provider_code is None:
        return None
    p = get_provider_by_code(provider_code)
    if p is None or ProviderCapability.DEFINITION not in p.supported_capabilities():
        return None
    if not isinstance(p, DefinitionProvider) or not await p.can_define(lang):
        return None
    return await p.get_definition(word, lang)

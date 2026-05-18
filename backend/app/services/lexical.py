"""Lexical matches service.

Cache management has moved into each LexicalProvider implementation.
This module is now a thin coordination layer.
"""
from __future__ import annotations

from app.providers.provider import ProviderCapability
from app.providers.registry import get_provider_by_code
from app.providers.types.lexical import LexicalProvider


async def get_lexical_matches(
    word: str,
    source_lang: str,
    target_lang: str,
    provider_code: str | None = None,
) -> list[str]:
    """Return target-language equivalents for *word* from the given provider.

    Cache lookup and persistence are handled by the provider itself.
    Returns ``[]`` when the provider is unknown or unsupported.  Provider
    exceptions (network errors etc.) are caught and returned as empty so
    the UI degrades gracefully; the provider will have already stored a
    failure entry to prevent repeated hammering.
    """
    if provider_code is None:
        return []
    p = get_provider_by_code(provider_code)
    if p is None or ProviderCapability.LEXICAL not in p.supported_capabilities():
        return []
    if not isinstance(p, LexicalProvider) or not await p.can_provide_lexical_matches(
        source_lang, target_lang
    ):
        return []
    return await p.get_lexical_matches(word, source_lang, target_lang)

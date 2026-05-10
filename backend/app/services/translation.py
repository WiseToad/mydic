"""Translation service.

Cache management has moved into each TranslationProvider implementation.
This module is a thin coordination layer: it validates the provider and
delegates the actual translate call.
"""
from __future__ import annotations

from app.providers.provider import ProviderCapability
from app.providers.registry import get_provider_by_code
from app.providers.types.translation import TranslationProvider, TranslationResult


async def translate(
    text: str,
    source_lang: str,
    target_lang: str,
    provider_code: str,
) -> TranslationResult:
    """Translate *text* using the provider identified by *provider_code*.

    Raises:
        ValueError: if the provider code is unknown or not a translation provider.
        RuntimeError: if the provider is unavailable.
        Any exception raised by the provider's translate() call (e.g. network
        errors, or a RuntimeError when a cached failure is within the retry
        window).
    """
    p = get_provider_by_code(provider_code)
    if p is None or ProviderCapability.TRANSLATION not in p.supported_capabilities():
        raise ValueError(f"Unknown translation provider: {provider_code!r}")
    if not p.is_available:
        raise RuntimeError(
            f"Translation provider {provider_code!r} is not available: "
            f"{p.unavailable_reason or 'check server configuration'}"
        )
    provider: TranslationProvider = p  # type: ignore[assignment]
    return await provider.translate(text, source_lang, target_lang)

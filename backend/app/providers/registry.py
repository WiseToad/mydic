"""In-memory provider registry.

This module is the single source of truth for all available providers.
Adding a new provider: implement it, then add an instance to _build_providers().
No DB migrations or seeding required.

Lifecycle
---------
Call :func:`init_registry` once at application startup (FastAPI lifespan) with
the singleton :class:`~app.services.cache.CacheService`.  This injects the
cache into every provider that handles text capabilities (translation,
definition, context, lexical).  TTS providers are excluded because TTS caching
is handled separately by :mod:`app.services.tts_cache`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.providers.provider import Provider, ProviderCapability
from app.providers.api.libretranslate import LibreTranslateProvider
from app.providers.api.reverso import ReversoProvider
from app.providers.api.freedict import FreeDictionaryProvider
from app.providers.api.wiktionary import WiktionaryProvider
from app.providers.api.tatoeba import TatoebaProvider
from app.providers.api.yandex import YandexTranslateProvider
from app.providers.api.piper import PiperTtsProvider
from app.providers.api.kokoro import KokoroTtsProvider

if TYPE_CHECKING:
    from app.services.cache import CacheService

# Module-level cache service reference; set by init_registry() at startup.
_cache_service: CacheService | None = None


def init_registry(cache: CacheService) -> None:
    """Inject *cache* into providers and rebuild the singleton provider list.

    Must be called once during app startup before any request is served.
    Clears the :func:`get_all_providers` lru_cache so the new instances
    (with cache injected) replace any earlier call made without a cache.
    """
    global _cache_service
    _cache_service = cache
    get_all_providers.cache_clear()
    get_all_providers()  # eagerly build so the first request doesn't pay the cost


def _build_providers() -> list[Provider]:
    """Instantiate every configured provider, filtering out config-disabled ones.

    Text-capability providers receive the singleton CacheService so they can
    manage their own cache without a per-request session.  TTS providers are
    excluded from cache injection (TTS caching is owned by tts_cache.py).
    Piper is listed first among TTS providers so that
    :func:`app.services.tts_cache._first_tts_provider` keeps defaulting to it.
    """
    c = _cache_service  # capture once for consistency
    candidates: list[Provider] = [
        LibreTranslateProvider(cache=c),
        YandexTranslateProvider(cache=c),
        ReversoProvider(cache=c),
        FreeDictionaryProvider(cache=c),
        WiktionaryProvider(cache=c),
        TatoebaProvider(cache=c),
        PiperTtsProvider(),   # TTS — cache handled by tts_cache.py
        KokoroTtsProvider()  # TTS — cache handled by tts_cache.py
    ]
    return [p for p in candidates if p.enabled]


@lru_cache(maxsize=1)
def get_all_providers() -> list[Provider]:
    """Return all configured provider instances (cached for the process lifetime)."""
    return _build_providers()


def get_providers_by_capability(cap: ProviderCapability) -> list[Provider]:
    """Return all providers that support *cap*, in registry order."""
    return [p for p in get_all_providers() if cap in p.supported_capabilities()]


def get_provider_by_code(code: str) -> Provider | None:
    """Return the provider whose code matches *code* (case-sensitive), or None."""
    return next((p for p in get_all_providers() if p.code == code), None)

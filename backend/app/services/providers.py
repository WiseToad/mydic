"""Service: determine which providers can handle a given language pair / language.

Two caching levels:
1. Provider language lists – cached on each provider instance (TTL 30 min).
2. The final (user_id, source_lang, target_lang) → [ProviderItem] list –
   cached here at module level (TTL 5 min) to avoid repeated pair-check work
   on every UI-triggered fetch when the user changes language dropdowns quickly.
"""

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_prefs import UserProviderPref
from app.providers.provider import Provider, ProviderCapability
from app.providers.registry import get_providers_by_capability
from app.schemas.settings import ProviderItem

_PAIR_CACHE_TTL = 300  # 5 minutes

# (user_id, source_lang, target_lang) → (list[ProviderItem], expires_at)
_pair_cache: dict[tuple[int, str, str], tuple[list[ProviderItem], float]] = {}

async def get_providers_for_pair(
    user_id: int,
    source_lang: str,
    target_lang: str,
    db: AsyncSession,
) -> list[ProviderItem]:
    """Return the ordered list of translation providers for source→target.

    Includes disabled providers (enabled=False) so the UI has full metadata.
    Result is cached per (user_id, source_lang, target_lang) for 5 minutes.
    """
    cache_key = (user_id, source_lang.lower(), target_lang.lower())
    now = time.monotonic()

    cached = _pair_cache.get(cache_key)
    if cached is not None and now < cached[1]:
        return cached[0]

    result = await _build_providers_for_pair(user_id, source_lang, target_lang, db)

    _pair_cache[cache_key] = (result, now + _PAIR_CACHE_TTL)
    return result


async def _build_providers_for_pair(
    user_id: int,
    source_lang: str,
    target_lang: str,
    db: AsyncSession,
) -> list[ProviderItem]:
    all_providers = get_providers_by_capability(ProviderCapability.TRANSLATION)
    all_by_code: dict[str, Provider] = {p.code: p for p in all_providers}
    user_prefs = await _load_user_providers_ordered(user_id, "translation", db)
    ordered = _apply_user_prefs_full(all_providers, all_by_code, user_prefs)

    result: list[ProviderItem] = []
    for position, (provider, enabled) in enumerate(ordered):
        if not enabled:
            # Disabled providers: include with enabled=False, no pair-check needed.
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=False,
                available=provider.is_available,
                unavailable_reason=provider.unavailable_reason,
            ))
            continue
        if not provider.is_available:
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=True,
                available=False,
                unavailable_reason=provider.unavailable_reason,
            ))
            continue
        try:
            capable = await provider.can_translate_pair(source_lang, target_lang)  # type: ignore[union-attr]
        except Exception:
            capable = False
        if capable:
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=True,
                available=True,
            ))

    return result

async def _load_user_providers_ordered(
    user_id: int, capability: str, db: AsyncSession
) -> list[tuple[str | None, bool]]:
    """Return [(provider_code, enabled), ...] for *capability* in user-pref order."""
    rows = list(
        (
            await db.execute(
                select(UserProviderPref)
                .where(
                    UserProviderPref.user_id == user_id,
                    UserProviderPref.capability == capability,
                )
                .order_by(UserProviderPref.position)
            )
        )
        .scalars()
        .all()
    )
    return [(row.provider_code, row.enabled) for row in rows]

def invalidate_user_cache(user_id: int) -> None:
    """Evict all cached entries for a specific user (call when their settings change)."""
    keys_to_delete = [k for k in _pair_cache if k[0] == user_id]
    for k in keys_to_delete:
        del _pair_cache[k]


# ---------------------------------------------------------------------------
# Definition providers – per language
# ---------------------------------------------------------------------------

async def get_definition_providers_for_lang(
    user_id: int,
    lang: str,
    db: AsyncSession,
) -> list[ProviderItem]:
    """Return ordered definition providers for *lang*, including disabled ones.

    Disabled providers are included with ``enabled=False`` so the UI has full
    metadata for displaying previously-used providers.  Unavailable providers
    capable of the language are included with ``available=False``.
    """
    all_providers = get_providers_by_capability(ProviderCapability.DEFINITION)
    all_by_code: dict[str, Provider] = {p.code: p for p in all_providers}
    user_prefs = await _load_user_providers_ordered(user_id, "definition", db)
    ordered = _apply_user_prefs_full(all_providers, all_by_code, user_prefs)

    result: list[ProviderItem] = []
    for position, (provider, enabled) in enumerate(ordered):
        if not enabled:
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=False,
                available=provider.is_available,
                unavailable_reason=provider.unavailable_reason,
            ))
            continue
        from app.providers.types.definition import DefinitionProvider
        if not isinstance(provider, DefinitionProvider):
            continue
        if not await provider.can_define(lang):
            continue
        result.append(ProviderItem(
            code=provider.code,
            name=provider.name,
            abbrev=provider.abbrev,
            position=position,
            enabled=True,
            available=provider.is_available,
            unavailable_reason=provider.unavailable_reason if not provider.is_available else None,
        ))
    return result


# ---------------------------------------------------------------------------
# Context providers – per language pair
# ---------------------------------------------------------------------------

async def get_context_providers_for_pair(
    user_id: int,
    source_lang: str,
    target_lang: str,
    db: AsyncSession,
) -> list[ProviderItem]:
    """Return ordered context providers for *source_lang* → *target_lang*,
    including disabled ones.

    Disabled providers are included with ``enabled=False``.  Unavailable
    providers are included with ``available=False``.
    """
    all_providers = get_providers_by_capability(ProviderCapability.CONTEXT)
    all_by_code: dict[str, Provider] = {p.code: p for p in all_providers}
    user_prefs = await _load_user_providers_ordered(user_id, "context", db)
    ordered = _apply_user_prefs_full(all_providers, all_by_code, user_prefs)

    result: list[ProviderItem] = []
    for position, (provider, enabled) in enumerate(ordered):
        if not enabled:
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=False,
                available=provider.is_available,
                unavailable_reason=provider.unavailable_reason,
            ))
            continue
        from app.providers.types.context import ContextProvider
        if not isinstance(provider, ContextProvider):
            continue
        if not await provider.can_provide_context_examples(source_lang, target_lang):
            continue
        result.append(ProviderItem(
            code=provider.code,
            name=provider.name,
            abbrev=provider.abbrev,
            position=position,
            enabled=True,
            available=provider.is_available,
            unavailable_reason=provider.unavailable_reason if not provider.is_available else None,
        ))
    return result


# ---------------------------------------------------------------------------
# Lexical providers – per language pair
# ---------------------------------------------------------------------------

async def get_lexical_providers_for_pair(
    user_id: int,
    source_lang: str,
    target_lang: str,
    db: AsyncSession,
) -> list[ProviderItem]:
    """Return ordered lexical providers for *source_lang* → *target_lang*,
    including disabled ones.

    Disabled providers are included with ``enabled=False``.  Unavailable
    providers are included with ``available=False``.
    """
    all_providers = get_providers_by_capability(ProviderCapability.LEXICAL)
    all_by_code: dict[str, Provider] = {p.code: p for p in all_providers}
    user_prefs = await _load_user_providers_ordered(user_id, "lexical", db)
    ordered = _apply_user_prefs_full(all_providers, all_by_code, user_prefs)

    result: list[ProviderItem] = []
    for position, (provider, enabled) in enumerate(ordered):
        if not enabled:
            result.append(ProviderItem(
                code=provider.code,
                name=provider.name,
                abbrev=provider.abbrev,
                position=position,
                enabled=False,
                available=provider.is_available,
                unavailable_reason=provider.unavailable_reason,
            ))
            continue
        from app.providers.types.lexical import LexicalProvider
        if not isinstance(provider, LexicalProvider):
            continue
        if not await provider.can_provide_lexical_matches(source_lang, target_lang):
            continue
        result.append(ProviderItem(
            code=provider.code,
            name=provider.name,
            abbrev=provider.abbrev,
            position=position,
            enabled=True,
            available=provider.is_available,
            unavailable_reason=provider.unavailable_reason if not provider.is_available else None,
        ))
    return result


def _apply_user_prefs_full(
    all_providers: list[Provider],
    all_by_code: dict[str, Provider],
    user_prefs: list[tuple[str | None, bool]],
) -> list[tuple[Provider, bool]]:
    """Return [(provider, enabled), ...] in user-preference order, including disabled entries.

    Providers not yet in user prefs (newly registered) are appended last as active.
    """
    result: list[tuple[Provider, bool]] = []
    seen_codes: set[str] = set()

    if user_prefs:
        for provider_code, enabled in user_prefs:
            if not provider_code:
                continue
            seen_codes.add(provider_code)
            provider = all_by_code.get(provider_code)
            if provider is None:
                continue  # provider removed from registry; skip orphaned pref
            result.append((provider, enabled))
        for provider in all_providers:
            if provider.code not in seen_codes:
                result.append((provider, True))
    else:
        result = [(p, True) for p in all_providers]

    return result

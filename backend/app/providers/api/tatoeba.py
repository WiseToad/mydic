"""Tatoeba bilingual context examples provider.

Uses the Tatoeba REST API (https://api.tatoeba.org/v1/sentences) to fetch
sentence pairs with translations.  Tatoeba uses ISO 639-3 (three-letter)
language codes; this module derives the mapping from the shared ISO 639-1
reference data file via :data:`app.schemas.languages.ISO639_ALPHA3`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.context import ContextProvider
from app.schemas.languages import ISO639_ALPHA3

if TYPE_CHECKING:
    from app.services.cache import CacheService

_API_URL = "https://api.tatoeba.org/v1/sentences"
_HEADERS = {
    "User-Agent": "MyDic/1.0 (language learning app; https://github.com/wisetoad/mydic) httpx"
}
_MAX_RESULTS = 5

# Tatoeba-specific overrides: for some ISO 639-1 codes, Tatoeba uses a more
# specific ISO 639-3 code rather than the standard ISO 639-2/T collective.
# Example: "zh" → ISO 639-2/T "zho" (Chinese collective), but Tatoeba uses
# "cmn" (Mandarin Chinese).  Only deviations from ISO639_ALPHA3 are listed here.
_TATOEBA_OVERRIDES: dict[str, str] = {
    "zh": "cmn",  # Mandarin Chinese (cmn) vs. collective code (zho)
}


def _to_iso3(code: str) -> str | None:
    """Convert a two-letter ISO 639-1 code to the ISO 639-3 code used by Tatoeba.

    Applies provider-specific overrides on top of the standard ISO 639-2/T mapping.
    Returns None when the code is not in the reference data.
    """
    lc = code.lower()
    if lc in _TATOEBA_OVERRIDES:
        return _TATOEBA_OVERRIDES[lc]
    return ISO639_ALPHA3.get(lc)


class TatoebaProvider(Provider, ContextProvider):
    """
    ContextProvider backed by the Tatoeba sentence corpus API.

    Returns bilingual sentence pairs (source + target) for a given word or
    phrase.  Only language pairs covered by the ISO 639-1 → ISO 639-3 mapping
    are supported; ``can_provide_context_examples`` returns False for others.
    """

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)

    @property
    def code(self) -> str:
        return "TATOEBA"

    @property
    def name(self) -> str:
        return "Tatoeba"

    @property
    def abbrev(self) -> str:
        return "Tatoeba"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.CONTEXT})

    @property
    def enabled(self) -> bool:
        return get_settings().tatoeba_enabled

    # ------------------------------------------------------------------
    # ContextProvider
    # ------------------------------------------------------------------

    async def can_provide_context_examples(self, source_lang: str, target_lang: str) -> bool:
        return _to_iso3(source_lang) is not None and _to_iso3(target_lang) is not None

    async def get_context_examples(
        self, text: str, source_lang: str, target_lang: str
    ) -> list[dict[str, str]]:
        from app.services.cache import ContextKey
        from app.utils import normalize_text

        src3 = _to_iso3(source_lang)
        tgt3 = _to_iso3(target_lang)
        if not src3 or not tgt3:
            return []

        cache_text = normalize_text(text).lower()
        key = ContextKey(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=cache_text,
            provider_code=self.code,
        ) if self._cache else None

        if self._cache and key is not None:
            cached = await self._cache.get_context(key)
            if cached is not None:
                if cached.failed:
                    raise RuntimeError("Fetch error, please try again later")
                return cached.value if cached.value is not None else []

        params: dict[str, str | int] = {
            "lang": src3,
            "sort": "relevance",
            "q": text,
            "trans:lang": tgt3,
            "showtrans:lang": tgt3,
            "limit": _MAX_RESULTS,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(_API_URL, params=params, headers=_HEADERS)
                if resp.status_code == 404:
                    if self._cache and key is not None:
                        await self._cache.store_context(key, [])  # valid empty
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_context(key, None, failed=True)
            raise

        examples: list[dict[str, str]] = []
        for sentence in data.get("data", []):
            src_text: str = sentence.get("text", "")
            if not src_text:
                continue
            # translations is a flat list of dicts (API v1 format)
            translations: list[dict] = sentence.get("translations", [])
            tgt_text = ""
            for t in translations:
                if t.get("lang") == tgt3 and t.get("text"):
                    tgt_text = t["text"]
                    break
            if src_text and tgt_text:
                examples.append({"source": src_text, "target": tgt_text})
            if len(examples) >= _MAX_RESULTS:
                break

        if self._cache and key is not None:
            await self._cache.store_context(key, examples)

        return examples

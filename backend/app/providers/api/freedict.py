from __future__ import annotations

from typing import Any, TYPE_CHECKING

import httpx

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.definition import DefinitionProvider

if TYPE_CHECKING:
    from app.services.cache import CacheService

_FREE_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries"


class FreeDictionaryProvider(Provider, DefinitionProvider):
    """
    DefinitionProvider backed by the Free Dictionary API (dictionaryapi.dev).
    Supports English only; falls back gracefully for unsupported words.
    """

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)

    @property
    def code(self) -> str:
        return "FREEDICT"

    @property
    def name(self) -> str:
        return "Free Dictionary"

    @property
    def abbrev(self) -> str:
        return "FreeDict"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.DEFINITION})

    @property
    def enabled(self) -> bool:
        return get_settings().freedict_enabled

    # ------------------------------------------------------------------
    # DefinitionProvider
    # ------------------------------------------------------------------

    async def can_define(self, lang: str) -> bool:
        # Lang codes are always normalised to two chars at the API boundary.
        return lang.lower() == "en"

    async def _fetch_raw(self, word: str) -> list[Any]:
        """Return the raw API response list, or [] on 404; raises on other errors."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_FREE_DICT_URL}/en/{word}")
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            return resp.json()

    async def get_definition(self, word: str, lang: str) -> dict[str, Any] | None:
        from app.services.cache import DefinitionKey
        from app.utils import normalize_text

        cache_word = normalize_text(word).lower()
        key = DefinitionKey(
            word=cache_word, lang=lang, provider_code=self.code
        ) if self._cache else None

        if self._cache and key is not None:
            cached = await self._cache.get_definition(key)
            if cached is not None:
                if cached.failed:
                    raise RuntimeError("Fetch error, please try again later")
                return cached.value

        try:
            data = await self._fetch_raw(cache_word)
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_definition(key, None, failed=True)
            raise

        if not data:
            if self._cache and key is not None:
                await self._cache.store_definition(key, None)  # valid not-found
            return None

        entry = data[0]
        meanings = []
        for m in entry.get("meanings", []):
            defs = []
            for d in m.get("definitions", [])[:3]:
                defs.append({
                    "definition": d.get("definition", ""),
                    "example": d.get("example"),
                    "synonyms": d.get("synonyms", [])[:6],
                    "antonyms": d.get("antonyms", [])[:4],
                })
            meanings.append({
                "part_of_speech": m.get("partOfSpeech"),
                "definitions": defs,
                "synonyms": m.get("synonyms", [])[:6],
            })

        phonetics = [p["text"] for p in entry.get("phonetics", []) if p.get("text")]

        result = {
            "word": entry.get("word", cache_word),
            "phonetics": phonetics[:2],
            "meanings": meanings,
            "source": "freedictionaryapi",
        }

        if self._cache and key is not None:
            await self._cache.store_definition(key, result)

        return result

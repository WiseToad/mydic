from __future__ import annotations

import html
import re
from typing import Any, TYPE_CHECKING

import httpx

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.context import ContextProvider
from app.providers.types.definition import DefinitionProvider

if TYPE_CHECKING:
    from app.services.cache import CacheService

_WIKTIONARY_URL = "https://en.wiktionary.org/api/rest_v1/page/definition"
_HEADERS = {"User-Agent": "MyDic/1.0 (language learning app; https://github.com/wisetoad/mydic) httpx"}
_MAX_EXAMPLES = 5


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from Wiktionary definition strings."""
    return html.unescape(re.sub(r'<[^>]+>', '', text)).strip()


def _extract_examples(entries: list[dict]) -> list[dict[str, str]]:
    """Pull context examples out of raw Wiktionary entry objects.

    Wiktionary definitions may carry an ``examples`` list (plain text) or a
    ``parsedExamples`` list (HTML, needs stripping).  Both live inside each
    definition dict under an entry.  This helper aggregates them across all
    entries and definitions and returns them in the ``{source, target}`` shape
    used by ContextProvider.
    """
    seen: set[str] = set()
    results: list[dict[str, str]] = []
    for entry in entries:
        for d in entry.get("definitions", []):
            # ``examples`` is plain text; ``parsedExamples`` has HTML wrappers.
            raw_examples: list[str] = d.get("examples", []) or [
                _strip_html(pe.get("example", ""))
                for pe in d.get("parsedExamples", [])
            ]
            for ex in raw_examples:
                text = _strip_html(ex).strip()
                if text and text not in seen:
                    seen.add(text)
                    results.append({"source": text, "target": ""})
                    if len(results) >= _MAX_EXAMPLES:
                        return results
    return results


class WiktionaryProvider(Provider, DefinitionProvider, ContextProvider):
    """
    Provider backed by the Wiktionary REST API.

    Supports two capabilities:
    - DEFINITION: monolingual structured definitions.
    - CONTEXT: monolingual example sentences extracted from the same API
      response.  When a definition is fetched, context examples are also
      stored in the cache under ``target_lang=""`` (language-agnostic
      marker) so a subsequent context request can skip the network call.
    """

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)

    @property
    def code(self) -> str:
        return "WIKT"

    @property
    def name(self) -> str:
        return "Wiktionary"

    @property
    def abbrev(self) -> str:
        return "Wikt"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.DEFINITION, ProviderCapability.CONTEXT})

    @property
    def enabled(self) -> bool:
        return get_settings().wiktionary_enabled

    async def _fetch_raw(self, word: str, lang: str) -> list[dict]:
        """Fetch raw Wiktionary entry list for *word* in *lang*."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_WIKTIONARY_URL}/{word}", headers=_HEADERS)
            if resp.status_code in (404, 403):
                return []
            resp.raise_for_status()
            data = resp.json()
        return data.get(lang.lower()) or data.get(lang.split("-")[0].lower(), [])

    # ------------------------------------------------------------------
    # DefinitionProvider
    # ------------------------------------------------------------------

    async def can_define(self, lang: str) -> bool:
        # Wiktionary covers a wide range of languages; accept any 2-char code.
        return True

    async def get_definition(self, word: str, lang: str) -> dict[str, Any] | None:
        from app.services.cache import ContextKey, DefinitionKey
        from app.utils import normalize_text

        cache_word = normalize_text(word).lower()
        key = DefinitionKey(
            word=cache_word, lang=lang, provider_code=self.code
        ) if self._cache else None

        if self._cache and key is not None:
            cached = await self._cache.get_definition(key)
            if cached is not None:
                return cached.value

        try:
            entries = await self._fetch_raw(cache_word, lang)
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_definition(key, None, failed=True)
            raise

        if not entries:
            if self._cache and key is not None:
                await self._cache.store_definition(key, None)  # valid not-found
            return None

        meanings = []
        for entry in entries[:4]:
            defs = [
                {
                    "definition": _strip_html(d.get("definition", "")),
                    "example": _strip_html((d.get("examples") or [""])[0]) or None,
                    "synonyms": [],
                    "antonyms": [],
                }
                for d in entry.get("definitions", [])[:3]
            ]
            meanings.append({
                "part_of_speech": entry.get("partOfSpeech"),
                "definitions": defs,
                "synonyms": [],
            })

        definition = {
            "word": cache_word,
            "phonetics": [],
            "meanings": meanings,
            "source": "wiktionary",
        }

        if self._cache and key is not None:
            await self._cache.store_definition(key, definition)
            # Pre-cache context examples from the same API response so a
            # subsequent context request can skip the network round-trip.
            examples = _extract_examples(entries)
            if examples:
                ctx_key = ContextKey(
                    source_lang=lang,
                    target_lang="",  # monolingual marker — target-lang-agnostic
                    source_text=cache_word,
                    provider_code=self.code,
                )
                await self._cache.store_context(ctx_key, examples)

        return definition

    # ------------------------------------------------------------------
    # ContextProvider
    # ------------------------------------------------------------------

    async def can_provide_context_examples(self, source_lang: str, target_lang: str) -> bool:
        # Wiktionary provides monolingual (source-language) examples regardless
        # of the target language; accept any combination.
        return True

    async def get_context_examples(
        self, text: str, source_lang: str, target_lang: str
    ) -> list[dict[str, str]]:
        from app.services.cache import ContextKey
        from app.utils import normalize_text

        cache_text = normalize_text(text).lower()
        key = ContextKey(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=cache_text,
            provider_code=self.code,
        ) if self._cache else None

        if self._cache and key is not None:
            # Check exact target_lang match first.
            cached = await self._cache.get_context(key)
            if cached is not None:
                return cached.value if cached.value is not None else []
            # Fall back to the language-agnostic pre-cached entry (target_lang="")
            # written by get_definition when it fetched the same word.
            if target_lang != "":
                mono_cached = await self._cache.get_context(
                    ContextKey(
                        source_lang=source_lang,
                        target_lang="",
                        source_text=cache_text,
                        provider_code=self.code,
                    )
                )
                if mono_cached is not None:
                    return mono_cached.value if mono_cached.value is not None else []

        try:
            entries = await self._fetch_raw(cache_text, source_lang)
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_context(key, None, failed=True)
            raise

        examples = _extract_examples(entries)

        if self._cache and key is not None:
            await self._cache.store_context(key, examples)

        return examples

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.context import ContextProvider
from app.providers.types.lexical import LexicalProvider

if TYPE_CHECKING:
    from app.services.cache import CacheService

_MAX_LEXICAL_MATCHES = 10
_MAX_CONTEXT_EXAMPLES = 5
_EXECUTOR_TIMEOUT = 10  # seconds; prevents indefinite "Loading" on slow/hung Reverso responses

# Reverso Context supported language pairs (ISO 639-1 codes).
# Derived from the combinations available on context.reverso.net.
# Both (src, tgt) and (tgt, src) are listed explicitly.
_SUPPORTED_PAIRS: frozenset[tuple[str, str]] = frozenset({
    # English with all others
    ("en", "ar"), ("ar", "en"),
    ("en", "de"), ("de", "en"),
    ("en", "es"), ("es", "en"),
    ("en", "fr"), ("fr", "en"),
    ("en", "he"), ("he", "en"),
    ("en", "it"), ("it", "en"),
    ("en", "ja"), ("ja", "en"),
    ("en", "nl"), ("nl", "en"),
    ("en", "pl"), ("pl", "en"),
    ("en", "pt"), ("pt", "en"),
    ("en", "ro"), ("ro", "en"),
    ("en", "ru"), ("ru", "en"),
    ("en", "tr"), ("tr", "en"),
    ("en", "uk"), ("uk", "en"),
    ("en", "zh"), ("zh", "en"),
    # French cross-pairs
    ("fr", "ar"), ("ar", "fr"),
    ("fr", "de"), ("de", "fr"),
    ("fr", "es"), ("es", "fr"),
    ("fr", "it"), ("it", "fr"),
    ("fr", "nl"), ("nl", "fr"),
    ("fr", "pt"), ("pt", "fr"),
    # Other cross-pairs
    ("de", "es"), ("es", "de"),
    ("de", "nl"), ("nl", "de"),
    ("es", "pt"), ("pt", "es"),
    ("ru", "de"), ("de", "ru"),
    ("ru", "fr"), ("fr", "ru"),
    ("ru", "es"), ("es", "ru"),
})


class ReversoProvider(Provider, LexicalProvider, ContextProvider):
    """
    Provider backed by the Reverso Context API.

    Supports two capabilities:
    - LEXICAL: corpus-frequency-ranked target-language word equivalents
      via Client.get_translations().
    - CONTEXT: bilingual sentence-pair examples
      via Client.get_translation_samples().
    """

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)

    @property
    def code(self) -> str:
        return "REVERSO"

    @property
    def name(self) -> str:
        return "Reverso Context"

    @property
    def abbrev(self) -> str:
        return "Reverso"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.LEXICAL, ProviderCapability.CONTEXT})

    @property
    def enabled(self) -> bool:
        return get_settings().reverso_enabled

    # ------------------------------------------------------------------
    # ContextProvider
    # ------------------------------------------------------------------

    async def can_provide_context_examples(self, source_lang: str, target_lang: str) -> bool:
        return (source_lang.lower(), target_lang.lower()) in _SUPPORTED_PAIRS

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
            cached = await self._cache.get_context(key)
            if cached is not None:
                if cached.failed:
                    raise RuntimeError("Fetch error, please try again later")
                return cached.value if cached.value is not None else []

        try:
            loop = asyncio.get_running_loop()
            examples = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._fetch_context, text, source_lang, target_lang
                ),
                timeout=_EXECUTOR_TIMEOUT,
            )
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_context(key, None, failed=True)
            raise

        if self._cache and key is not None:
            await self._cache.store_context(key, examples)

        return examples

    @staticmethod
    def _fetch_context(text: str, source_lang: str, target_lang: str) -> list[dict[str, str]]:
        """Fetch context examples synchronously; exceptions propagate to the caller."""
        from reverso_context_api import Client  # type: ignore

        client = Client(source_lang, target_lang)
        examples: list[dict[str, str]] = []
        for src, tgt in client.get_translation_samples(text, cleanup=True):
            examples.append({"source": str(src), "target": str(tgt)})
            if len(examples) >= _MAX_CONTEXT_EXAMPLES:
                break
        return examples

    # ------------------------------------------------------------------
    # LexicalProvider
    # ------------------------------------------------------------------

    async def can_provide_lexical_matches(self, source_lang: str, target_lang: str) -> bool:
        return (source_lang.lower(), target_lang.lower()) in _SUPPORTED_PAIRS

    async def get_lexical_matches(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[str]:
        from app.services.cache import LexicalKey
        from app.utils import normalize_text

        cache_word = normalize_text(word).lower()
        key = LexicalKey(
            source_lang=source_lang,
            target_lang=target_lang,
            word=cache_word,
            provider_code=self.code,
        ) if self._cache else None

        if self._cache and key is not None:
            cached = await self._cache.get_lexical(key)
            if cached is not None:
                if cached.failed:
                    raise RuntimeError("Fetch error, please try again later")
                return cached.value if cached.value is not None else []

        try:
            loop = asyncio.get_running_loop()
            matches = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._fetch_lexical, word, source_lang, target_lang
                ),
                timeout=_EXECUTOR_TIMEOUT,
            )
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_lexical(key, None, failed=True)
            raise

        if self._cache and key is not None:
            await self._cache.store_lexical(key, matches)

        return matches

    @staticmethod
    def _fetch_lexical(word: str, source_lang: str, target_lang: str) -> list[str]:
        """Fetch lexical matches synchronously; exceptions propagate to the caller."""
        from reverso_context_api import Client  # type: ignore

        client = Client(source_lang, target_lang)
        results: list[str] = []
        for match in client.get_translations(word):
            results.append(str(match))
            if len(results) >= _MAX_LEXICAL_MATCHES:
                break
        return results

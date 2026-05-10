"""Yandex Cloud Translation provider.

Uses the Yandex Cloud Translation API v2
(https://translate.api.cloud.yandex.net/translate/v2/translate).

An API key must be obtained from the Yandex Cloud console
(IAM → Service accounts → Create API key for a service account that has the
``translate.translator`` role).  Set the ``YANDEX_TRANSLATE_API_KEY``
environment variable (or ``yandex_translate_api_key`` in .env) to activate
this provider; the provider reports itself unavailable when the key is absent.

Language-pair support: Yandex Cloud Translate handles 100 + languages using
two-letter ISO 639-1 codes, so no mapping is required.  Auto-detection works
by omitting ``sourceLanguageCode`` from the request body.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.translation import TranslationProvider, TranslationResult
from app.providers.cache import TTLCache

if TYPE_CHECKING:
    from app.services.cache import CacheService

_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"
_LANGUAGES_URL = "https://translate.api.cloud.yandex.net/translate/v2/languages"


class YandexTranslateProvider(Provider, TranslationProvider):
    """
    TranslationProvider backed by the Yandex Cloud Translation API v2.

    The provider is inactive (``is_available = False``) when no API key is
    configured, so it degrades gracefully in installations that don't use it.
    """

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)
        self._api_key = get_settings().yandex_translate_api_key
        self._lang_cache: TTLCache[frozenset[str]] = TTLCache(ttl=1800)

    @property
    def code(self) -> str:
        return "YANDEX"

    @property
    def name(self) -> str:
        return "Yandex Translate"

    @property
    def abbrev(self) -> str:
        return "Yandex"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.TRANSLATION})

    @property
    def enabled(self) -> bool:
        return get_settings().yandex_translate_enabled

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    @property
    def unavailable_reason(self) -> str | None:
        if not self._api_key:
            return "YANDEX_TRANSLATE_API_KEY is not set"
        return None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Api-Key {self._api_key}"}

    # ------------------------------------------------------------------
    # TranslationProvider
    # ------------------------------------------------------------------

    async def _get_supported_langs(self) -> frozenset[str]:
        cached = self._lang_cache.get()
        if cached is not None:
            return cached
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(_LANGUAGES_URL, json={}, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        langs = frozenset(
            lang["code"].lower() for lang in data.get("languages", [])
        )
        self._lang_cache.set(langs)
        return langs

    async def can_translate_pair(self, source_lang: str, target_lang: str) -> bool:
        langs = await self._get_supported_langs()
        source_lang = source_lang.lower()
        target_lang = target_lang.lower()
        if source_lang == "auto":
            return target_lang in langs
        return source_lang != target_lang and source_lang in langs and target_lang in langs

    async def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        from app.services.cache import TranslationKey
        from app.utils import normalize_text

        is_auto = source_lang == "auto"
        norm_text = normalize_text(text)
        key = TranslationKey(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=norm_text,
            provider_code=self.code,
        ) if self._cache else None

        if self._cache and key is not None:
            cached = await self._cache.get_translation(key)
            if cached is not None:
                if cached.value is None:
                    raise RuntimeError(
                        "Translation temporarily unavailable (retry window active)"
                    )
                return TranslationResult(
                    translated_text=cached.value["translated_text"],
                    detected_lang=cached.value.get("detected_lang") if is_auto else None,
                )

        try:
            body: dict = {"texts": [text], "targetLanguageCode": target_lang}
            if source_lang and source_lang != "auto":
                body["sourceLanguageCode"] = source_lang

            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    _TRANSLATE_URL, json=body, headers=self._headers()
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_translation(key, None, failed=True)
            raise

        translations = data.get("translations", [])
        if not translations:
            raise ValueError("Yandex Translate returned an empty translations list")

        first = translations[0]
        translated_text: str = first.get("text", "")
        detected: str | None = first.get("detectedLanguageCode") or None
        result = TranslationResult(
            translated_text=translated_text, detected_lang=detected
        )

        if self._cache and key is not None:
            await self._cache.store_translation(key, {
                "translated_text": result.translated_text,
                "detected_lang": result.detected_lang,
            })

        return result

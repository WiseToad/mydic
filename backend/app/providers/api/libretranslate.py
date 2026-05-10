from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from app.config import get_settings
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.translation import TranslationProvider, TranslationResult
from app.providers.cache import TTLCache

if TYPE_CHECKING:
    from app.services.cache import CacheService


class LibreTranslateProvider(Provider, TranslationProvider):
    @property
    def code(self) -> str:
        return "LIBRE"

    @property
    def name(self) -> str:
        return "Libre Translate"

    @property
    def abbrev(self) -> str:
        return "Libre"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.TRANSLATION})

    @property
    def enabled(self) -> bool:
        return get_settings().libre_translate_enabled

    def __init__(self, cache: "CacheService | None" = None) -> None:
        super().__init__(cache=cache)
        settings = get_settings()
        self._base_url = settings.libre_translate_url.rstrip("/")
        self._lang_cache: TTLCache[frozenset[str]] = TTLCache(ttl=1800)

    def _payload(self, extra: dict) -> dict:
        p = dict(extra)
        return p

    async def _get_supported_langs(self) -> frozenset[str]:
        cached = self._lang_cache.get()
        if cached is not None:
            return cached
        params: dict = {}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self._base_url}/languages", params=params)
            resp.raise_for_status()
            data = resp.json()
        langs = frozenset(lang["code"].lower() for lang in data)
        self._lang_cache.set(langs)
        return langs

    # ------------------------------------------------------------------
    # TranslationProvider
    # ------------------------------------------------------------------

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
            payload = self._payload({"q": text, "source": source_lang, "target": target_lang})
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base_url}/translate", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            if self._cache and key is not None:
                await self._cache.store_translation(key, None, failed=True)
            raise

        detected = None
        if dl := data.get("detectedLanguage"):
            detected = dl.get("language")
        result = TranslationResult(
            translated_text=data["translatedText"], detected_lang=detected
        )

        if self._cache and key is not None:
            await self._cache.store_translation(key, {
                "translated_text": result.translated_text,
                "detected_lang": result.detected_lang,
            })

        return result

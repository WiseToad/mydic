"""PostgreSQL-backed implementation of :class:`app.services.cache.CacheService`.

This is a singleton: one instance is created at app startup (using the
global ``async_sessionmaker``) and injected into every provider at
construction time.  Each cache operation opens its own short-lived session
so it is decoupled from the per-request transaction.

Retry-window logic
------------------
A row stored with ``failed=True`` will suppress further API calls
(``get_X`` returns ``Cached(None)``) until ``cache_failure_retry_seconds``
have elapsed since ``fetched_at``.  After the window expires ``get_X``
returns ``None``, signalling the provider to re-attempt the API call.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.models.cache import (
    ContextCache,
    DefinitionCache,
    LexicalCache,
    TranslationCache,
)
from app.services.cache import (
    CacheService,
    Cached,
    ContextKey,
    DefinitionKey,
    LexicalKey,
    TranslationKey,
)


class PostgresCacheService(CacheService):
    """CacheService backed by PostgreSQL via SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session = session_factory
        self._retry_seconds: int = get_settings().api_failure_retry_seconds

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_stale(self, fetched_at: datetime) -> bool:
        """Return True when a failed entry's retry window has expired."""
        return (datetime.now(timezone.utc) - fetched_at).total_seconds() >= self._retry_seconds

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    async def get_translation(
        self, key: TranslationKey
    ) -> Cached[dict[str, Any]] | None:
        async with self._session() as db:
            stmt = select(TranslationCache).where(
                TranslationCache.source_lang == key.source_lang,
                TranslationCache.target_lang == key.target_lang,
                TranslationCache.source_text == key.source_text,
                TranslationCache.provider_code == key.provider_code,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()

        if row is None:
            return None
        if row.failed:
            if not self._is_stale(row.fetched_at):
                return Cached(None)  # within retry window — suppress API call
            return None  # window expired — trigger re-fetch
        return Cached({
            "translated_text": row.translated_text,
            "source_lang": row.source_lang,
            "detected_lang": row.detected_lang,
        })

    async def store_translation(
        self,
        key: TranslationKey,
        data: dict[str, Any] | None,
        *,
        failed: bool = False,
    ) -> None:
        is_auto = key.source_lang == "auto"
        # For auto-detect successes, skip caching when no detected language
        # is known — avoids storing a row we can never usefully retrieve.
        if is_auto and not failed and data and not data.get("detected_lang"):
            return

        async with self._session() as db:
            try:
                stmt = select(TranslationCache).where(
                    TranslationCache.source_lang == key.source_lang,
                    TranslationCache.target_lang == key.target_lang,
                    TranslationCache.source_text == key.source_text,
                    TranslationCache.provider_code == key.provider_code,
                )
                row = (await db.execute(stmt)).scalar_one_or_none()

                translated_text = (data or {}).get("translated_text", "")
                detected_lang = (data or {}).get("detected_lang") if is_auto else None

                if row is not None:
                    row.translated_text = translated_text
                    row.detected_lang = detected_lang
                    row.failed = failed
                    row.fetched_at = datetime.now(timezone.utc)
                else:
                    db.add(TranslationCache(
                        source_lang=key.source_lang,
                        detected_lang=detected_lang,
                        target_lang=key.target_lang,
                        source_text=key.source_text,
                        translated_text=translated_text,
                        provider_code=key.provider_code,
                        failed=failed,
                    ))
                await db.commit()
            except Exception:
                await db.rollback()

    # ------------------------------------------------------------------
    # Definition
    # ------------------------------------------------------------------

    async def get_definition(
        self, key: DefinitionKey
    ) -> Cached[dict[str, Any]] | None:
        async with self._session() as db:
            row = (await db.execute(
                select(DefinitionCache).where(
                    DefinitionCache.word == key.word,
                    DefinitionCache.lang == key.lang,
                    DefinitionCache.provider_code == key.provider_code,
                )
            )).scalar_one_or_none()

        if row is None:
            return None
        if row.failed:
            if not self._is_stale(row.fetched_at):
                return Cached(None)
            return None
        # Treat the not-found sentinel (or legacy empty-dict entries) as a
        # valid "not found" result without re-fetching.
        if not row.definition or row.definition.get("__not_found__"):
            return Cached(None)
        return Cached(row.definition)

    async def store_definition(
        self,
        key: DefinitionKey,
        data: dict[str, Any] | None,
        *,
        failed: bool = False,
    ) -> None:
        async with self._session() as db:
            try:
                row = (await db.execute(
                    select(DefinitionCache).where(
                        DefinitionCache.word == key.word,
                        DefinitionCache.lang == key.lang,
                        DefinitionCache.provider_code == key.provider_code,
                    )
                )).scalar_one_or_none()

                # For valid not-found (data=None, not a failure), store a
                # sentinel so get_definition can return Cached(None) without
                # the caller accidentally treating {} as a real definition.
                stored_def = data if data is not None else (
                    {} if failed else {"__not_found__": True}
                )
                if row is not None:
                    row.definition = stored_def
                    row.failed = failed
                    row.fetched_at = datetime.now(timezone.utc)
                else:
                    db.add(DefinitionCache(
                        word=key.word,
                        lang=key.lang,
                        definition=stored_def,
                        provider_code=key.provider_code,
                        failed=failed,
                    ))
                await db.commit()
            except Exception:
                await db.rollback()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    async def get_context(
        self, key: ContextKey
    ) -> Cached[list[Any]] | None:
        async with self._session() as db:
            row = (await db.execute(
                select(ContextCache).where(
                    ContextCache.source_lang == key.source_lang,
                    ContextCache.target_lang == key.target_lang,
                    ContextCache.source_text == key.source_text,
                    ContextCache.provider_code == key.provider_code,
                )
            )).scalar_one_or_none()

        if row is None:
            return None
        if row.failed:
            if not self._is_stale(row.fetched_at):
                return Cached(None)
            return None
        return Cached(row.examples)

    async def store_context(
        self,
        key: ContextKey,
        data: list[Any] | None,
        *,
        failed: bool = False,
    ) -> None:
        async with self._session() as db:
            try:
                row = (await db.execute(
                    select(ContextCache).where(
                        ContextCache.source_lang == key.source_lang,
                        ContextCache.target_lang == key.target_lang,
                        ContextCache.source_text == key.source_text,
                        ContextCache.provider_code == key.provider_code,
                    )
                )).scalar_one_or_none()

                if row is not None:
                    row.examples = data if data is not None else []
                    row.failed = failed
                    row.fetched_at = datetime.now(timezone.utc)
                else:
                    db.add(ContextCache(
                        source_lang=key.source_lang,
                        target_lang=key.target_lang,
                        source_text=key.source_text,
                        examples=data if data is not None else [],
                        provider_code=key.provider_code,
                        failed=failed,
                    ))
                await db.commit()
            except Exception:
                await db.rollback()

    # ------------------------------------------------------------------
    # Lexical
    # ------------------------------------------------------------------

    async def get_lexical(
        self, key: LexicalKey
    ) -> Cached[list[Any]] | None:
        async with self._session() as db:
            row = (await db.execute(
                select(LexicalCache).where(
                    LexicalCache.source_lang == key.source_lang,
                    LexicalCache.target_lang == key.target_lang,
                    LexicalCache.word == key.word,
                    LexicalCache.provider_code == key.provider_code,
                )
            )).scalar_one_or_none()

        if row is None:
            return None
        if row.failed:
            if not self._is_stale(row.fetched_at):
                return Cached(None)
            return None
        return Cached(row.matches)

    async def store_lexical(
        self,
        key: LexicalKey,
        data: list[Any] | None,
        *,
        failed: bool = False,
    ) -> None:
        async with self._session() as db:
            try:
                row = (await db.execute(
                    select(LexicalCache).where(
                        LexicalCache.source_lang == key.source_lang,
                        LexicalCache.target_lang == key.target_lang,
                        LexicalCache.word == key.word,
                        LexicalCache.provider_code == key.provider_code,
                    )
                )).scalar_one_or_none()

                if row is not None:
                    row.matches = data if data is not None else []
                    row.failed = failed
                    row.fetched_at = datetime.now(timezone.utc)
                else:
                    db.add(LexicalCache(
                        source_lang=key.source_lang,
                        target_lang=key.target_lang,
                        word=key.word,
                        matches=data if data is not None else [],
                        provider_code=key.provider_code,
                        failed=failed,
                    ))
                await db.commit()
            except Exception:
                await db.rollback()

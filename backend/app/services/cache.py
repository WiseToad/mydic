"""Abstract cache service interface for all provider capabilities.

Each ``get_X`` method returns either:
* ``None``          — no cached answer; the caller should make the API call.
* ``Cached(value)`` — use ``value`` without calling the API.  ``value`` may
                      itself be ``None`` (valid empty / not-found result, or a
                      failed entry still within the retry window — both cases
                      suppress the API call).

Each ``store_X`` method persists a result.  Pass ``failed=True`` to record
that the underlying API call failed; the implementation handles retry-window
logic so callers never inspect timestamps or failure flags directly.

Implementations are free to use any backing store.  The ``failed=True``
semantic maps to a column flag + timestamp comparison in the Postgres
implementation, and to a short TTL in a hypothetical Redis implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class Cached(Generic[T]):
    """Wraps a single cached value.

    ``value`` may be ``None`` for a valid 'not found' result or to represent
    a within-retry-window failed entry.  Callers distinguish "use this value"
    from "go fetch" solely by whether this wrapper is returned at all.
    """

    value: T | None


# ---------------------------------------------------------------------------
# Cache-key types (frozen dataclasses for hashability / equality)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranslationKey:
    source_lang: str   # 'auto' for auto-detect requests, explicit lang code otherwise
    target_lang: str
    source_text: str
    provider_code: str


@dataclass(frozen=True)
class DefinitionKey:
    word: str          # normalized (lower-cased, stripped)
    lang: str
    provider_code: str


@dataclass(frozen=True)
class ContextKey:
    source_lang: str
    target_lang: str   # may be "" for monolingual (Wiktionary pre-cache) entries
    source_text: str   # normalized
    provider_code: str


@dataclass(frozen=True)
class LexicalKey:
    source_lang: str
    target_lang: str
    word: str          # normalized
    provider_code: str


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class CacheService(ABC):
    """Backend-agnostic read/write interface for all provider result caches."""

    # -- Translation ---------------------------------------------------------

    @abstractmethod
    async def get_translation(
        self, key: TranslationKey
    ) -> Cached[dict[str, Any]] | None: ...

    @abstractmethod
    async def store_translation(
        self,
        key: TranslationKey,
        data: dict[str, Any] | None,
        *,
        failed: bool = False,
    ) -> None: ...

    # -- Definition ----------------------------------------------------------

    @abstractmethod
    async def get_definition(
        self, key: DefinitionKey
    ) -> Cached[dict[str, Any]] | None: ...

    @abstractmethod
    async def store_definition(
        self,
        key: DefinitionKey,
        data: dict[str, Any] | None,
        *,
        failed: bool = False,
    ) -> None: ...

    # -- Context -------------------------------------------------------------

    @abstractmethod
    async def get_context(
        self, key: ContextKey
    ) -> Cached[list[Any]] | None: ...

    @abstractmethod
    async def store_context(
        self,
        key: ContextKey,
        data: list[Any] | None,
        *,
        failed: bool = False,
    ) -> None: ...

    # -- Lexical -------------------------------------------------------------

    @abstractmethod
    async def get_lexical(
        self, key: LexicalKey
    ) -> Cached[list[Any]] | None: ...

    @abstractmethod
    async def store_lexical(
        self,
        key: LexicalKey,
        data: list[Any] | None,
        *,
        failed: bool = False,
    ) -> None: ...

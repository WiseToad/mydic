from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.cache import CacheService


class ProviderCapability(Enum):
    """Functional capability a provider can advertise."""
    TRANSLATION = "translation"
    DEFINITION = "definition"
    CONTEXT = "context"
    LEXICAL = "lexical"
    TTS = "tts"

class Provider(ABC):
    def __init__(self, cache: CacheService | None = None) -> None:
        self._cache = cache

    @abstractmethod
    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        """Return the set of capabilities this provider supports.

        A provider may support more than one capability.
        """
        ...

    @property
    @abstractmethod
    def code(self) -> str:
        """Short uppercase slug that uniquely identifies this provider (e.g. 'LIBRE', 'REVERSO').

        Used as a stable key wherever a provider must be referenced by identity
        (user preferences, cache attribution) without an integer database ID.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def abbrev(self) -> str:
        """Short display name shown in UI tips."""
        return self.name

    @property
    def is_available(self) -> bool:
        """Whether this provider is ready to use (e.g. binary present, credentials set).

        Checked at instantiation time; providers that require external setup
        (binaries, credentials) should override this and unavailable_reason.
        """
        return True

    @property
    def unavailable_reason(self) -> str | None:
        """Human-readable explanation when is_available is False; None otherwise."""
        return None

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this provider is enabled at the deployment / config level.

        This is an admin-level switch (typically backed by an env / config
        variable) and is independent of :attr:`is_available` (a runtime
        check) and of any per-user preference (stored in the DB).  Disabled
        providers are filtered out by the registry and never appear in any
        user-facing list.
        """
        ...

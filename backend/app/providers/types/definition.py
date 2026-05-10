from abc import ABC, abstractmethod
from typing import Any


class DefinitionProvider(ABC):
    """
    Common interface for providers that return monolingual word definitions.

    Distinct from TranslationProvider (cross-lingual, sentence-level)
    and LexicalProvider (cross-lingual, word-level equivalents).
    """

    async def can_define(self, lang: str) -> bool:
        """Return True if this provider can supply definitions for *lang*.

        Override in providers with language restrictions (e.g. English-only APIs).
        Default: True (accepts any language).
        """
        return True

    @abstractmethod
    async def get_definition(
        self, word: str, lang: str
    ) -> dict[str, Any] | None:
        """Return structured definition data for *word* in *lang*, or None if not found.

        The returned dict must contain at least 'word', 'phonetics', 'meanings',
        and 'source' keys.
        """
        ...

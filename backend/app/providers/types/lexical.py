from abc import ABC, abstractmethod


class LexicalProvider(ABC):
    """
    Common interface for providers that return target-language word-level
    equivalents for a given source-language word (cross-lingual lexical lookup).

    Distinct from TranslationProvider (sentence-level, single best result)
    and DefinitionProvider (monolingual, structured).

    To add a new provider: subclass this, implement get_lexical_matches,
    then register it in providers/lexical_factory.py.
    """

    async def can_provide_lexical_matches(self, source_lang: str, target_lang: str) -> bool:
        """Return True if this provider supports lexical lookup for the given language pair.

        Override to restrict to supported language combinations.
        Default: True (accepts any combination).
        """
        return True

    @abstractmethod
    async def get_lexical_matches(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[str]:
        """Return target-language equivalents for *word* in source_lang.

        Results are ordered by corpus frequency (most common first).
        Returns an empty list when no matches are found.
        """
        ...

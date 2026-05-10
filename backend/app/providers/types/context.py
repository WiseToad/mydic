from abc import ABC, abstractmethod


class ContextProvider(ABC):
    """
    Common interface for providers that return sentence-pair examples for a
    given source word or phrase.

    Providers may return bilingual (source + target) or monolingual (source only)
    examples depending on their corpus.  A monolingual provider should override
    ``can_provide_context_examples`` to return ``True`` whenever ``source_lang``
    is supported, regardless of ``target_lang``.

    Distinct from LexicalProvider (word-level equivalents, no example sentences).
    """

    async def can_provide_context_examples(self, source_lang: str, target_lang: str) -> bool:
        """Return True if this provider can supply context examples for the given pair.

        Monolingual providers should return True based on *source_lang* alone.
        Override to restrict to supported language combinations.
        Default: True (accepts any combination).
        """
        return True

    @abstractmethod
    async def get_context_examples(
        self, text: str, source_lang: str, target_lang: str
    ) -> list[dict[str, str]]:
        """Return sentence pairs illustrating *text* in context.

        Each item is a dict with 'source' and 'target' keys; 'target' may be
        an empty string for monolingual providers.
        Results are ordered by corpus relevance.
        Returns an empty list when no examples are found.
        """
        ...

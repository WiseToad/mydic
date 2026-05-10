from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranslationResult:
    translated_text: str
    detected_lang: str | None = None


class TranslationProvider(ABC):
    """
    Common interface for all translation engines.
    To add a new engine: subclass this, implement the abstract methods,
    then register it in providers/factory.py.
    """

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        """Translate text. Pass source_lang='auto' for auto-detection.

        When ``source_lang='auto'``, providers should populate
        :attr:`TranslationResult.detected_lang` with the language they
        detected.  A standalone ``detect_language`` method is intentionally
        not part of the interface: language detection is a free side-effect
        of every translate call and no caller currently needs it on its own.
        """
        ...

    @abstractmethod
    async def can_translate_pair(self, source_lang: str, target_lang: str) -> bool:
        """Return True if this provider supports translating source_lang → target_lang.

        Implementations should cache the underlying language-list API response
        to avoid redundant network calls on repeated invocations.
        Pass source_lang='auto' to check only the target language.
        """
        ...

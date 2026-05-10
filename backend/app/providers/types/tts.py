from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TtsVoice:
    """Static description of a single voice exposed by a TTS provider.

    ``id`` is the provider-specific voice identifier passed back via the ``voice``
    argument of :meth:`TtsProvider.generate_speech`.
    ``name`` is a short human-readable label for UI display (defaults to id).
    ``languages`` lists the two-letter ISO 639-1 codes the voice can pronounce;
    a multilingual voice exposes several entries here.
    """

    id: str
    name: str
    languages: tuple[str, ...]


class TtsProvider(ABC):
    """
    Common interface for text-to-speech synthesis providers.

    Providers are cache-agnostic: they only produce raw bytes for the
    request parameters given.  Caching and metadata persistence live in
    ``app.services.tts_cache``.
    """

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        lang: str,
        voice: str,
        *,
        speed_ratio: float = 1.0,
    ) -> bytes:
        """Synthesize *text* in *lang* and return raw WAV audio bytes.

        ``voice`` is a provider-specific identifier; when ``None`` the provider
        picks a default for *lang* (see :meth:`resolve_voice`).
        ``speed_ratio`` is a numeric multiplier applied to the natural
        speaking rate (``1.0`` = normal, ``<1.0`` = slower, ``>1.0`` = faster).
        """
        ...

    @abstractmethod
    def list_voices(self) -> list[TtsVoice]:
        """Return the static catalog of voices this provider exposes.

        Used by the settings endpoint to render the per-provider voice list
        and by the audio-button long-press popup.  Implementations must avoid
        loading heavy model files; the call is expected to be cheap and
        idempotent.
        """
        ...

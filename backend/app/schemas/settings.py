from pydantic import BaseModel, Field


class TtsVoiceItem(BaseModel):
    """User-facing entry for a single TTS voice within a provider.

    ``id``: provider-specific voice identifier (passed straight back to
    :meth:`TtsProvider.generate_speech`).
    ``languages``: ISO 639-1 codes the voice can pronounce; rendered next to
    the voice name in the settings UI and used to filter the long-press popup.
    """
    id: str
    name: str = ""
    languages: list[str] = Field(default_factory=list)
    position: int = 0
    enabled: bool = True


class ProviderItem(BaseModel):
    """Unified provider descriptor returned by all provider-listing endpoints.

    For TTS providers, ``voices`` carries the nested per-voice list (ordered
    + enable flags).  Other capabilities leave it empty.
    """
    code: str
    name: str = ""
    abbrev: str = ""
    position: int
    enabled: bool = True
    available: bool = True
    unavailable_reason: str | None = None
    voices: list[TtsVoiceItem] = Field(default_factory=list)


class UserSettingsResponse(BaseModel):
    tts: list[ProviderItem]
    translation: list[ProviderItem]
    definition: list[ProviderItem]
    context: list[ProviderItem]
    lexical: list[ProviderItem]


class UserSettingsUpdate(BaseModel):
    tts: list[ProviderItem]
    translation: list[ProviderItem]
    definition: list[ProviderItem]
    context: list[ProviderItem]
    lexical: list[ProviderItem]

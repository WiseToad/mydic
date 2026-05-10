from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_prefs import UserTtsPref
from app.providers.registry import get_provider_by_code
from app.providers.types.tts import TtsProvider
from app.services.tts_cache import TtsSpeed, get_or_create_tts


async def _resolve_voice_for_user(
    db: AsyncSession,
    user_id: int,
    provider_code: str,
    lang: str,
    provider: TtsProvider,
) -> str | None:
    """Return the user's preferred voice for *provider_code* and *lang*.

    Walks the user's saved voice preferences for the given provider in saved
    order, picking the first enabled voice whose language list includes *lang*
    (or has an empty list, meaning universal).  Returns ``None`` when no
    suitable preference exists so the caller falls back to
    ``provider.resolve_voice``.
    """
    voice_rows = list(
        (
            await db.execute(
                select(UserTtsPref)
                .where(
                    UserTtsPref.user_id == user_id,
                    UserTtsPref.provider_code == provider_code,
                )
                .order_by(UserTtsPref.position)
            )
        )
        .scalars()
        .all()
    )
    catalog = {v.id: v for v in provider.list_voices()}
    for v_row in voice_rows:
        if not v_row.enabled:
            continue
        v = catalog.get(v_row.voice)
        if v is None:
            continue
        if not v.languages or lang in v.languages:
            return v_row.voice
    return None


async def generate_speech(
    db: AsyncSession,
    text: str,
    lang: str,
    speed: TtsSpeed = TtsSpeed.NORMAL,
    *,
    user_id: int | None = None,
    provider_code: str,
    voice: str | None = None,
) -> tuple[bytes, str]:
    """Synthesize (or retrieve from cache) speech for *text* in *lang*.

    *provider_code* is mandatory: the caller must always specify which TTS
    engine to use.  Voice resolution order:
      1. Explicit *voice* argument.
      2. The user's saved voice preferences for *provider_code* and *lang*,
         when *user_id* is supplied.
      3. The provider's own default for *lang* (``provider.resolve_voice``).

    Returns:
        ``(audio_bytes, audio_format)`` where ``audio_format`` is one of
        ``"wav"`` or ``"mp3"`` — the latter when the offline encoder worker
        has already rotated the cached clip to a lossy format.  The router
        converts this into a ``Content-Type`` header.
    """
    candidate = get_provider_by_code(provider_code)
    if candidate is None or not isinstance(candidate, TtsProvider):
        raise ValueError(f"Unknown TTS provider '{provider_code}'")
    if not candidate.is_available:
        raise ValueError(f"TTS provider '{provider_code}' is not available")

    if voice is None and user_id is not None:
        voice = await _resolve_voice_for_user(
            db, user_id, provider_code, lang, candidate
        )
    if voice is None:
        raise ValueError(f"Failed to resolve voice for '{provider_code}' and language '{lang}'")

    return await get_or_create_tts(
        db,
        text=text,
        lang=lang,
        speed=speed,
        provider=candidate,
        voice=voice,
    )

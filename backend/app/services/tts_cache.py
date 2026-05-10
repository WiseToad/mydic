"""Metadata-aware TTS cache.

Owns the mapping between synthesized audio files and their logical identity
(``lang``, ``text``, ``provider_code``, ``voice``, ``speed_ratio``) so
providers remain cache-agnostic.  Public callers continue to talk in tagged
``TtsSpeed`` values (``NORMAL`` / ``SLOW``); this module owns the mapping
from tag to an integer percent of the natural speaking rate that is then
used for cache lookup and storage.

Files live under ``settings.tts_cache_dir`` at the relative path recorded in
the :class:`~app.models.cache.TtsCache` row.  Filenames are UUID-based and
sharded two levels deep to keep every directory well-bounded:

    ``{provider_code_lower}/{voice}/{fid[:2]}/{fid[2:4]}/{fid}.wav``

After the offline encoder worker rotates a wav to mp3, the row's
``filename`` is rewritten to point at ``{...}/{fid}.mp3``.  The container
format is derived from the filename extension at read time so no separate
format field needs to be stored.  Reads return both bytes and format so the
router can pick the right ``Content-Type``.
"""

from __future__ import annotations

import os
import uuid
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.cache import TtsCache
from app.providers.provider import ProviderCapability
from app.providers.registry import get_providers_by_capability
from app.providers.types.tts import TtsProvider
from app.utils import normalize_text

# Cache key is an integer percent of the natural speaking rate; 100 = normal,
# <100 = slower, >100 = faster.  Stored as INTEGER on Postgres so equality
# comparisons in the lookup are exact (no floating-point drift).
_NORMAL_PERCENT: int = 100


class TtsSpeed(str, Enum):
    """Discrete pronunciation speed degree.

    Public-facing tag exchanged by the API and frontend.  The numeric ratio
    used for synthesis and cache lookup is resolved per-call from settings
    by :func:`speed_ratio_for`.
    """

    NORMAL = "NORMAL"
    SLOW = "SLOW"


def speed_ratio_for(speed: TtsSpeed, provider_code: str | None = None) -> int:
    """Return the integer percent of original speed for *speed*.

    ``NORMAL`` is fixed at 100 (full speed).  ``SLOW`` is admin-tunable via
    settings; the value is read fresh on each call so a hot-reloaded config
    takes effect without process restart.  Resolution order for SLOW:

      1. ``<provider_code>_slow_ratio`` (e.g. ``piper_slow_ratio``) when
         *provider_code* is supplied AND the per-engine override is set.
      2. ``tts_slow_ratio`` global default otherwise.

    The float multiplier is rounded to the nearest whole percent for storage
    and cache lookup.  Per-engine values let admins compensate for engines
    whose synthesis quality degrades at the global slowdown rate; the cache
    key already includes ``provider_code`` so concurrent per-engine values
    coexist without collision.
    """
    if speed == TtsSpeed.NORMAL:
        return _NORMAL_PERCENT
    if speed == TtsSpeed.SLOW:
        settings = get_settings()
        raw: float | None = None
        if provider_code:
            raw = getattr(settings, f"{provider_code.lower()}_slow_ratio", None)
        if raw is None:
            raw = settings.tts_slow_ratio
        percent = int(round(float(raw) * 100))
        if percent <= 0:
            raise ValueError(
                f"slow_ratio must be > 0 (got {raw!r} for "
                f"provider {provider_code!r})."
            )
        return percent
    raise ValueError(f"Unsupported TTS speed: {speed!r}")


def _first_tts_provider() -> TtsProvider:
    providers = get_providers_by_capability(ProviderCapability.TTS)
    if not providers:
        raise RuntimeError("No TTS provider is configured.")
    return providers[0]  # type: ignore[return-value]


def _build_relative_filename(provider_code: str, voice: str) -> str:
    """Generate a UUID-based relative path for a new clip."""
    fid = uuid.uuid4().hex
    # Two nested 2-char shards: cap every directory at <= 256 children.
    return os.path.join(
        provider_code.lower(),
        voice,
        fid[:2],
        fid[2:4],
        f"{fid}.wav",
    )


def _format_from_filename(filename: str) -> str:
    """Derive the audio container format from the filename extension.

    Returns the lower-cased extension without the leading dot
    (e.g. ``"wav"``, ``"mp3"``).  Falls back to ``"wav"`` for rows
    with no recognisable extension.
    """
    ext = os.path.splitext(filename)[1]  # includes the dot, or ""
    return ext.lstrip(".").lower() or "wav"


async def _synthesize_and_write(
    provider: TtsProvider,
    *,
    text: str,
    lang: str,
    voice: str,
    speed_percent: int,
    relative_filename: str,
) -> bytes:
    """Call the provider, write the file, return the bytes.

    Providers operate on plain ``float`` ratios (numpy/torch friendly); the
    int-percent→float conversion happens at this boundary so the storage
    layer stays exact while the synthesis layer stays fast.
    """
    audio = await provider.generate_speech(
        text, lang, voice, speed_ratio=speed_percent / 100
    )
    settings = get_settings()
    abs_path = os.path.join(settings.app_home, settings.tts_cache_dir, relative_filename)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(audio)
    return audio


async def get_or_create_tts(
    db: AsyncSession,
    *,
    text: str,
    lang: str,
    speed: TtsSpeed = TtsSpeed.NORMAL,
    provider: TtsProvider,
    voice: str
) -> tuple[bytes, str]:
    """Return cached audio bytes plus its container format for the request.

    Behavior:
        1. Normalize *text* and *lang*.
        2. Resolve provider (first TTS-capable if not supplied) and voice.
        3. Look up ``tts_cache`` by
           ``(lang, text, provider_code, voice, speed_ratio)``.
        4. On hit: read the file from disk.  If the file is missing
           (stale row), re-fetch the row once — it may have been rewritten
           in place by the encoder worker between our SELECT and the open.
           Otherwise regenerate as wav (Piper / Kokoro emit wav) and update
           the existing row in place.
        5. On miss: synthesize, write a new wav at a fresh UUID path, and
           insert a new row pointing at the new ``.wav`` file.

    Returns:
        ``(bytes, audio_format)`` where ``audio_format`` is the file extension
        of the cached clip (e.g. ``"wav"``, ``"mp3"``), derived from the
        ``filename`` column.  Callers map this to a ``Content-Type`` for the
        HTTP response.
    """
    text = normalize_text(text)

    provider_code = getattr(provider, "code", None)
    if not provider_code:
        raise RuntimeError("TTS provider is missing a code.")
    # Per-engine slowdown overrides resolve here so the percent baked into
    # the cache key reflects the engine that actually produced the audio.
    percent = speed_ratio_for(speed, provider_code)

    settings = get_settings()

    stmt = select(TtsCache).where(
        TtsCache.lang == lang,
        TtsCache.text == text,
        TtsCache.provider_code == provider_code,
        TtsCache.voice == voice,
        TtsCache.speed_ratio == percent,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is not None:
        abs_path = os.path.join(settings.app_home, settings.tts_cache_dir, row.filename)
        if os.path.exists(abs_path):
            with open(abs_path, "rb") as f:
                return f.read(), _format_from_filename(row.filename)

        # File missing on disk.  This can happen for two reasons:
        #   (a) the encoder worker rotated wav → mp3 and unlinked the wav
        #       between our SELECT and the open() above; or
        #   (b) someone deleted the cache directory.
        # Try a fresh SELECT to differentiate (a) from (b).  In case (a) the
        # newly committed row points at the .mp3 file which DOES exist.
        await db.refresh(row)
        abs_path = os.path.join(settings.app_home, settings.tts_cache_dir, row.filename)
        if os.path.exists(abs_path):
            with open(abs_path, "rb") as f:
                return f.read(), _format_from_filename(row.filename)

        # Genuinely stale: regenerate as wav in place.  The new filename
        # always carries a .wav extension; needs_encode is re-armed so the
        # encoder worker picks up the fresh clip even if the previous row
        # had already been encoded (needs_encode was False).
        new_filename = _build_relative_filename(provider_code, voice)
        audio = await _synthesize_and_write(
            provider,
            text=text,
            lang=lang,
            voice=voice,
            speed_percent=percent,
            relative_filename=new_filename,
        )
        row.filename = new_filename
        row.needs_encode = True
        await db.commit()
        return audio, "wav"

    # Cache miss: synthesize, then persist both file and metadata.
    new_filename = _build_relative_filename(provider_code, voice)
    audio = await _synthesize_and_write(
        provider,
        text=text,
        lang=lang,
        voice=voice,
        speed_percent=percent,
        relative_filename=new_filename,
    )
    db.add(
        TtsCache(
            lang=lang,
            text=text,
            filename=new_filename,
            provider_code=provider_code,
            voice=voice,
            speed_ratio=percent,
        )
    )
    await db.commit()
    return audio, "wav"

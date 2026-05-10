import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.tts import generate_speech
from app.services.tts_cache import TtsSpeed

router = APIRouter(prefix="/tts", tags=["tts"])

_SAMPLES_PATH = Path(__file__).parent.parent / "data" / "tts-samples.json"


@lru_cache(maxsize=1)
def _load_samples() -> dict[str, str]:
    return json.loads(_SAMPLES_PATH.read_text(encoding="utf-8"))


@router.get("/samples", response_model=dict[str, str])
async def tts_samples() -> dict[str, str]:
    """Return sample sentences keyed by ISO 639-1 language code.

    Covers all languages supported by at least one configured TTS provider.
    No authentication required.
    """
    return _load_samples()


@router.get("")
async def text_to_speech(
    text: str = Query(..., max_length=500),
    lang: str = Query(..., min_length=1, max_length=10),
    speed: TtsSpeed = Query(TtsSpeed.NORMAL),
    provider: str = Query(
        ...,
        max_length=50,
        description="Provider code (required); determines which TTS engine to use.",
    ),
    voice: str | None = Query(
        None,
        max_length=100,
        description="Voice override; when omitted the backend resolves from user prefs.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    try:
        audio_bytes, audio_format = await generate_speech(
            db,
            text.strip(),
            lang,
            speed,
            user_id=current_user.id,
            provider_code=provider,
            voice=voice,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc

    # Map the cache-layer's container tag to a proper IANA media type.
    # Anything unknown falls back to the wav default so the response stays
    # playable even if the worker grows new formats before this map does.
    media_type = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
    }.get(audio_format, "audio/wav")

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )

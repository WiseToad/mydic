from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.languages import ISO639_NAMES
from app.schemas.settings import ProviderItem
from app.schemas.translation import TranslateRequest, TranslateResponse
from app.services import translation as translation_service
from app.services.providers import get_providers_for_pair

router = APIRouter(prefix="/translate", tags=["translation"])


@router.get("/providers", response_model=list[ProviderItem])
async def list_providers_for_pair(
    source_lang: str = Query(..., description="Source language code, or 'auto'"),
    target_lang: str = Query(..., description="Target language code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderItem]:
    """Return the ordered list of translation providers for source→target.

    Includes disabled providers (enabled=False).  Results are cached per
    (user, language pair) for 5 minutes.
    """
    return await get_providers_for_pair(
        user_id=current_user.id,
        source_lang=source_lang,
        target_lang=target_lang,
        db=db,
    )


@router.post("", response_model=TranslateResponse)
async def translate(
    req: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_auto = req.source_lang == "auto"

    # Provider lookup, availability check, cache get/store, and API call are
    # all handled inside the provider (via the injected CacheService singleton).
    try:
        result = await translation_service.translate(
            text=req.source_text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            provider_code=req.provider_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Translation provider error: {exc}"
        ) from exc

    detected_lang = result.detected_lang if is_auto else None
    detected_lang_name = ISO639_NAMES.get(detected_lang) if detected_lang else None

    return TranslateResponse(
        translated_text=result.translated_text,
        detected_lang=detected_lang,
        detected_lang_name=detected_lang_name
    )

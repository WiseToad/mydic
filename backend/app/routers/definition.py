from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.settings import ProviderItem
from app.services.dictionary import get_definition
from app.services.providers import get_definition_providers_for_lang

router = APIRouter(prefix="/definition", tags=["definition"])


@router.get("/providers", response_model=list[ProviderItem])
async def definition_providers(
    lang: str = Query(..., max_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderItem]:
    """Return ordered definition providers for *lang*, including disabled ones."""
    return await get_definition_providers_for_lang(current_user.id, lang, db)


@router.get("")
async def definition(
    word: str = Query(..., max_length=200),
    lang: str = Query(..., max_length=10),
    provider_code: str = Query(..., max_length=50),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await get_definition(
            word.strip(), lang, provider_code=provider_code
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Fetch error, please try again later")
    if result is None:
        raise HTTPException(status_code=404, detail="No definition found")
    return result

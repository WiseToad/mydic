from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.settings import ProviderItem
from app.services.context import get_context_examples
from app.services.providers import get_context_providers_for_pair

router = APIRouter(prefix="/context", tags=["context"])


@router.get("/providers", response_model=list[ProviderItem])
async def context_providers(
    source_lang: str = Query(..., max_length=10),
    target_lang: str = Query(..., max_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderItem]:
    """Return ordered context providers for *source_lang* → *target_lang*,
    including disabled ones.  It is the provider's responsibility to decide
    whether to use *target_lang* (bilingual vs. monolingual).
    """
    return await get_context_providers_for_pair(
        current_user.id,
        source_lang,
        target_lang,
        db,
    )


@router.get("")
async def context_examples(
    text: str = Query(..., max_length=200),
    source_lang: str = Query(..., max_length=10),
    target_lang: str = Query(..., max_length=10),
    provider_code: str = Query(..., max_length=50),
    current_user: User = Depends(get_current_user),
):
    try:
        examples = await get_context_examples(
            text.strip(),
            source_lang,
            target_lang,
            provider_code=provider_code,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Fetch error, please try again later")
    return {"examples": examples}

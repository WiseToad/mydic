from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.settings import ProviderItem
from app.services.context import get_context_examples
from app.services.dictionary import get_definition
from app.services.providers import get_definition_providers_for_lang, get_context_providers_for_pair

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.get("/definition/providers", response_model=list[ProviderItem])
async def definition_providers(
    lang: str = Query(..., max_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderItem]:
    """Return ordered definition providers for *lang*, including disabled ones."""
    return await get_definition_providers_for_lang(current_user.id, lang, db)


@router.get("/context/providers", response_model=list[ProviderItem])
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


@router.get("/definition")
async def definition(
    word: str = Query(..., max_length=200),
    lang: str = Query(..., max_length=10),
    provider_code: str = Query(..., max_length=50),
    current_user: User = Depends(get_current_user),
):
    result = await get_definition(
        word.strip(), lang, provider_code=provider_code
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No definition found")
    return result


@router.get("/context")
async def context_examples(
    text: str = Query(..., max_length=200),
    source_lang: str = Query(..., max_length=10),
    target_lang: str = Query(..., max_length=10),
    provider_code: str = Query(..., max_length=50),
    current_user: User = Depends(get_current_user),
):
    examples = await get_context_examples(
        text.strip(),
        source_lang,
        target_lang,
        provider_code=provider_code,
    )
    return {"examples": examples}

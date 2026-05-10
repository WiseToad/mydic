from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.settings import ProviderItem
from app.services.lexical import get_lexical_matches
from app.services.providers import get_lexical_providers_for_pair

router = APIRouter(prefix="/lexical", tags=["lexical"])


@router.get("/providers", response_model=list[ProviderItem])
async def lexical_providers(
    source_lang: str = Query(..., max_length=10),
    target_lang: str = Query(..., max_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderItem]:
    """Return ordered lexical providers for *source_lang* → *target_lang*,
    including disabled ones.
    """
    return await get_lexical_providers_for_pair(
        current_user.id,
        source_lang,
        target_lang,
        db,
    )


@router.get("")
async def lexical_matches(
    word: str = Query(..., max_length=200),
    source_lang: str = Query(..., max_length=10),
    target_lang: str = Query(..., max_length=10),
    provider_code: str = Query(..., max_length=50),
    current_user: User = Depends(get_current_user),
):
    """Return target-language word-level equivalents for *word* in source_lang.

    Backed by Reverso Context's bilingual word index (corpus-frequency ranked).
    Results are cached in the DB per-provider after the first fetch.
    """
    matches = await get_lexical_matches(
        word.strip(),
        source_lang,
        target_lang,
        provider_code=provider_code,
    )
    return {"matches": matches}

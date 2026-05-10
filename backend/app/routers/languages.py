from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_prefs import UserLanguagePref
from app.schemas.languages import (
    ISO639_NAMES,
    LanguageItem,
    LanguageListResponse,
    LanguageListUpdate,
    get_supported_language_codes,
    get_supported_language_names,
)

router = APIRouter(prefix="/languages", tags=["languages"])


def _build_default_list() -> list[LanguageItem]:
    """Return all supported languages enabled, in config-defined order."""
    names = get_supported_language_names()
    return [
        LanguageItem(code=code, name=names[code], position=i, enabled=True)
        for i, code in enumerate(get_supported_language_codes())
    ]


async def _load_saved_list(user_id: int, db: AsyncSession) -> list[LanguageItem] | None:
    """Load saved language prefs for a user. Returns None if no rows saved yet.

    Languages added to the registry after the user last saved are appended at
    the end with enabled=True, mirroring the provider prefs behaviour.
    """
    rows = list(
        (
            await db.execute(
                select(UserLanguagePref)
                .where(UserLanguagePref.user_id == user_id)
                .order_by(UserLanguagePref.position)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return None

    supported_codes = get_supported_language_codes()
    supported_names = get_supported_language_names()
    saved_codes: set[str] = set()
    items: list[LanguageItem] = []
    for row in rows:
        if row.lang_code not in supported_names:
            continue  # removed from supported list or registry – skip orphaned row
        saved_codes.add(row.lang_code)
        items.append(LanguageItem(
            code=row.lang_code,
            name=supported_names[row.lang_code],
            position=row.position,
            enabled=row.enabled,
        ))

    # Append newly supported languages not yet in saved prefs
    next_position = (max(item.position for item in items) + 1) if items else 0
    for code in supported_codes:
        if code not in saved_codes:
            items.append(LanguageItem(
                code=code,
                name=supported_names[code],
                position=next_position,
                enabled=True,
            ))
            next_position += 1

    if not items:
        return None

    items.sort(key=lambda x: x.position)
    return items


@router.get("", response_model=LanguageListResponse)
async def get_languages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LanguageListResponse:
    saved = await _load_saved_list(current_user.id, db)
    return LanguageListResponse(languages=saved if saved is not None else _build_default_list())


@router.put("", response_model=LanguageListResponse)
async def update_languages(
    payload: LanguageListUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LanguageListResponse:
    await db.execute(
        delete(UserLanguagePref).where(UserLanguagePref.user_id == current_user.id)
    )
    for item in payload.languages:
        if item.code not in ISO639_NAMES:
            continue  # ignore unknown codes sent by the client
        db.add(UserLanguagePref(
            user_id=current_user.id,
            lang_code=item.code,
            position=item.position,
            enabled=item.enabled,
        ))
    await db.commit()
    return await get_languages(current_user=current_user, db=db)

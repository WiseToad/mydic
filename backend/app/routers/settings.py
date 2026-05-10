from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_prefs import UserProviderPref, UserTtsPref
from app.providers.provider import ProviderCapability
from app.providers.registry import get_providers_by_capability
from app.providers.types.tts import TtsProvider, TtsVoice
from app.schemas.settings import (
    ProviderItem,
    TtsVoiceItem,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.providers import invalidate_user_cache

router = APIRouter(prefix="/settings", tags=["settings"])

# Capabilities with no nested voice prefs; used everywhere except 'tts'.
_FLAT_CAPABILITIES: tuple[str, ...] = ("translation", "definition", "context", "lexical")


def _voice_catalog(provider_code: str) -> list[TtsVoice]:
    """Return the static voice catalog for a TTS provider, or [] if unknown."""
    for p in get_providers_by_capability(ProviderCapability.TTS):
        if p.code == provider_code and isinstance(p, TtsProvider):
            return p.list_voices()
    return []


def _voice_items_default(provider_code: str) -> list[TtsVoiceItem]:
    """Default voice list for a TTS provider: catalog order, all enabled."""
    return [
        TtsVoiceItem(
            id=v.id,
            name=v.name,
            languages=list(v.languages),
            position=i,
            enabled=True,
        )
        for i, v in enumerate(_voice_catalog(provider_code))
    ]


def _build_default_list(capability: str) -> list[ProviderItem]:
    """Build a default (unsaved) ordered preference list for a capability.

    Provider order follows the registry order established in registry._build_providers().
    For 'tts', each provider entry is populated with its full default voice list.
    """
    cap_enum = ProviderCapability(capability)
    capable = get_providers_by_capability(cap_enum)

    return [
        ProviderItem(
            code=p.code,
            name=p.name,
            abbrev=p.abbrev,
            position=i,
            enabled=True,
            available=p.is_available,
            unavailable_reason=p.unavailable_reason,
            voices=_voice_items_default(p.code) if capability == "tts" else [],
        )
        for i, p in enumerate(capable)
    ]


async def _load_voice_prefs(
    user_id: int, db: AsyncSession
) -> dict[str, list[UserTtsPref]]:
    """Group saved per-voice prefs by provider_code, ordered by position."""
    rows = list(
        (
            await db.execute(
                select(UserTtsPref)
                .where(UserTtsPref.user_id == user_id)
                .order_by(
                    UserTtsPref.provider_code, UserTtsPref.position
                )
            )
        )
        .scalars()
        .all()
    )
    grouped: dict[str, list[UserTtsPref]] = {}
    for row in rows:
        grouped.setdefault(row.provider_code, []).append(row)
    return grouped


def _merge_voice_list(
    provider_code: str,
    saved: list[UserTtsPref],
) -> list[TtsVoiceItem]:
    """Merge saved voice prefs with the current provider catalog.

    Voices removed from the catalog are dropped.  Voices added since the user
    last saved are appended at the end with ``enabled=True`` so users see
    them automatically without needing to toggle each one on.
    """
    catalog = {v.id: v for v in _voice_catalog(provider_code)}
    items: list[TtsVoiceItem] = []
    seen: set[str] = set()
    for row in saved:
        v = catalog.get(row.voice)
        if v is None:
            continue  # voice removed from catalog; skip orphaned pref
        seen.add(row.voice)
        items.append(TtsVoiceItem(
            id=v.id,
            name=v.name,
            languages=list(v.languages),
            position=row.position,
            enabled=row.enabled,
        ))
    next_position = (max(i.position for i in items) + 1) if items else 0
    for v in catalog.values():
        if v.id not in seen:
            items.append(TtsVoiceItem(
                id=v.id,
                name=v.name,
                languages=list(v.languages),
                position=next_position,
                enabled=True,
            ))
            next_position += 1
    items.sort(key=lambda x: x.position)
    return items


async def _load_saved_list(
    capability: str,
    user_id: int,
    db: AsyncSession,
    voice_prefs: dict[str, list[UserTtsPref]] | None = None,
) -> list[ProviderItem] | None:
    """Load saved preferences for (user, capability). Returns None if no rows exist yet.

    Providers absent from saved prefs (newly registered) are appended in registry order
    after the last saved position.  For 'tts', each provider entry is populated with
    its merged voice list (saved order + new voices appended).
    """
    rows = list(
        (
            await db.execute(
                select(UserProviderPref)
                .where(UserProviderPref.user_id == user_id, UserProviderPref.capability == capability)
                .order_by(UserProviderPref.position)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return None

    cap_enum = ProviderCapability(capability)
    all_registry = get_providers_by_capability(cap_enum)
    registry_by_code = {p.code: p for p in all_registry}

    def voices_for(code: str) -> list[TtsVoiceItem]:
        if capability != "tts":
            return []
        if voice_prefs is None or code not in voice_prefs:
            return _voice_items_default(code)
        return _merge_voice_list(code, voice_prefs[code])

    saved_codes: set[str] = set()
    items: list[ProviderItem] = []
    for row in rows:
        if not row.provider_code or row.provider_code not in registry_by_code:
            continue  # provider no longer registered or code missing; skip orphaned row
        p = registry_by_code[row.provider_code]
        saved_codes.add(row.provider_code)
        items.append(ProviderItem(
            code=row.provider_code,
            name=p.name,
            abbrev=p.abbrev,
            position=row.position,
            enabled=row.enabled,
            available=p.is_available,
            unavailable_reason=p.unavailable_reason,
            voices=voices_for(row.provider_code),
        ))

    # Append newly registered providers not yet in saved prefs, after the last saved position
    next_position = (max(item.position for item in items) + 1) if items else 0
    for p in all_registry:
        if p.code not in saved_codes:
            items.append(ProviderItem(
                code=p.code,
                name=p.name,
                abbrev=p.abbrev,
                position=next_position,
                enabled=True,
                available=p.is_available,
                unavailable_reason=p.unavailable_reason,
                voices=voices_for(p.code),
            ))
            next_position += 1

    if not items:
        return None

    items.sort(key=lambda x: x.position)
    return items


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    voice_prefs = await _load_voice_prefs(current_user.id, db)

    result: dict[str, list[ProviderItem]] = {}
    for cap in ("tts", *_FLAT_CAPABILITIES):
        saved = await _load_saved_list(cap, current_user.id, db, voice_prefs)
        result[cap] = saved if saved is not None else _build_default_list(cap)

    return UserSettingsResponse(**result)


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    # Replace all existing provider prefs for this user
    await db.execute(
        delete(UserProviderPref).where(UserProviderPref.user_id == current_user.id)
    )
    await db.execute(
        delete(UserTtsPref).where(UserTtsPref.user_id == current_user.id)
    )

    for capability, items in (
        ("tts", payload.tts),
        ("translation", payload.translation),
        ("definition", payload.definition),
        ("context", payload.context),
        ("lexical", payload.lexical),
    ):
        for item in items:
            db.add(UserProviderPref(
                user_id=current_user.id,
                capability=capability,
                provider_code=item.code,
                position=item.position,
                enabled=item.enabled,
            ))
            if capability == "tts":
                for voice in item.voices:
                    db.add(UserTtsPref(
                        user_id=current_user.id,
                        provider_code=item.code,
                        voice=voice.id,
                        position=voice.position,
                        enabled=voice.enabled,
                    ))

    await db.commit()

    # Invalidate the providers-for-pair cache so the next translator fetch is fresh
    invalidate_user_cache(current_user.id)

    # Return the freshly saved state (re-use GET logic)
    return await get_settings(current_user=current_user, db=db)

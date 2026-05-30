from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wordbook import WordbookEntry, WordGroup
from app.schemas.wordbook import (
    WordbookEntryCreate,
    WordbookEntryResponse,
    WordbookEntryUpdate,
    WordbookLookupResult,
    WordbookMoveItem,
    WordGroupCreate,
    WordGroupResponse,
    WordGroupUpdate,
)

router = APIRouter(prefix="/wordbook", tags=["wordbook"])


def _entry_query():
    return select(WordbookEntry).options(joinedload(WordbookEntry.group))


@router.get("/lang-pairs", response_model=list[str])
async def list_lang_pairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return distinct lang-pair strings in 'src:tgt' format for the user."""
    rows = (
        await db.execute(
            select(distinct(WordbookEntry.source_lang), WordbookEntry.target_lang)
            .where(WordbookEntry.user_id == current_user.id)
        )
    ).all()
    return [f"{src}:{tgt}" for src, tgt in rows]


@router.get("/lookup", response_model=WordbookLookupResult,
            responses={204: {"description": "Word not in wordbook"}})
async def lookup_entry(
    source_lang: str,
    target_lang: str,
    source_text: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return entry_id/group_id/color for a matching entry, or 204 if not found."""
    from app.utils import normalize_text
    normalized = normalize_text(source_text)
    entry = (
        await db.execute(
            select(WordbookEntry).where(
                WordbookEntry.user_id == current_user.id,
                WordbookEntry.source_lang == source_lang,
                WordbookEntry.target_lang == target_lang,
                WordbookEntry.source_text == normalized,
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        return Response(status_code=204)
    return WordbookLookupResult(
        entry_id=entry.id,
        group_id=entry.group_id,
        color=entry.color,
    )


@router.get("", response_model=list[WordbookEntryResponse])
async def list_entries(
    group_id: int,
    lang_pair: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        _entry_query()
        .where(
            WordbookEntry.user_id == current_user.id,
            WordbookEntry.group_id == group_id,
        )
        .order_by(WordbookEntry.position.asc(), WordbookEntry.created_at.asc())
    )
    if lang_pair:
        pairs = []
        for p in lang_pair:
            parts = p.split(":", 1)
            if len(parts) == 2:
                pairs.append((parts[0], parts[1]))
        if pairs:
            conditions = [
                and_(
                    WordbookEntry.source_lang == src,
                    WordbookEntry.target_lang == tgt,
                )
                for src, tgt in pairs
            ]
            q = q.where(or_(*conditions))
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.post("", response_model=WordbookEntryResponse, status_code=201)
async def create_entry(
    entry: WordbookEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if entry.group_id is None:
        # group_id may be omitted only when the user has no groups yet
        user_group_count = (
            await db.execute(
                select(func.count()).where(WordGroup.user_id == current_user.id)
            )
        ).scalar()
        if user_group_count > 0:
            raise HTTPException(
                status_code=422,
                detail="group_id is required when the user already has groups",
            )
        group = WordGroup(user_id=current_user.id, name="Default", position=0)
        db.add(group)
        await db.flush()
        resolved_group_id = group.id
    else:
        grp = (
            await db.execute(
                select(WordGroup).where(
                    WordGroup.id == entry.group_id,
                    WordGroup.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if grp is None:
            raise HTTPException(status_code=404, detail="Group not found")
        resolved_group_id = entry.group_id

    max_pos = (
        await db.execute(
            select(func.coalesce(func.max(WordbookEntry.position), 0))
            .where(WordbookEntry.user_id == current_user.id)
        )
    ).scalar() or 0

    new_entry = WordbookEntry(
        user_id=current_user.id,
        group_id=resolved_group_id,
        position=max_pos + 1,
        **entry.model_dump(exclude={"group_id"}),
    )
    db.add(new_entry)
    await db.commit()

    row = (
        await db.execute(
            _entry_query().where(WordbookEntry.id == new_entry.id)
        )
    ).scalar_one()
    return row


@router.patch("/{entry_id}", response_model=WordbookEntryResponse)
async def update_entry(
    entry_id: int,
    update: WordbookEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (
        await db.execute(
            _entry_query().where(
                WordbookEntry.id == entry_id,
                WordbookEntry.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    await db.commit()
    row = (
        await db.execute(
            _entry_query().where(WordbookEntry.id == entry_id)
        )
    ).scalar_one()
    return row


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (
        await db.execute(
            select(WordbookEntry).where(
                WordbookEntry.id == entry_id,
                WordbookEntry.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    await db.delete(entry)
    await db.commit()


@router.put("/reorder", status_code=204)
async def reorder_entries(
    body: WordbookMoveItem,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move source_id to the position of target_id within the same group.

    Both entries must belong to the current user and to the same group.
    """
    if body.source_id == body.target_id:
        raise HTTPException(status_code=422, detail="source_id and target_id must differ")

    rows = (
        await db.execute(
            select(WordbookEntry).where(
                WordbookEntry.id.in_([body.source_id, body.target_id]),
                WordbookEntry.user_id == current_user.id,
            )
        )
    ).scalars().all()
    entry_map = {e.id: e for e in rows}

    if body.source_id not in entry_map or body.target_id not in entry_map:
        raise HTTPException(status_code=404, detail="Entry not found")

    source = entry_map[body.source_id]
    target = entry_map[body.target_id]
    if source.group_id != target.group_id:
        raise HTTPException(status_code=422, detail="Entries must belong to the same group")

    all_rows = (
        await db.execute(
            select(WordbookEntry)
            .where(
                WordbookEntry.user_id == current_user.id,
                WordbookEntry.group_id == source.group_id,
            )
            .order_by(WordbookEntry.position.asc(), WordbookEntry.created_at.asc())
        )
    ).scalars().all()

    ids = [e.id for e in all_rows]
    src_idx = ids.index(body.source_id)
    tgt_idx = ids.index(body.target_id)
    moving_forward = src_idx < tgt_idx
    new_ids = [i for i in ids if i != body.source_id]
    insert_at = new_ids.index(body.target_id)
    new_ids.insert(insert_at + 1 if moving_forward else insert_at, body.source_id)

    first = min(src_idx, tgt_idx)
    last = max(src_idx, tgt_idx)
    all_map = {e.id: e for e in all_rows}
    for i, eid in enumerate(new_ids[first:last + 1], start=first):
        all_map[eid].position = (i + 1) * 1000
    await db.commit()


# ---------------------------------------------------------------------------
# Word groups
# ---------------------------------------------------------------------------

@router.get("/groups", response_model=list[WordGroupResponse])
async def list_groups(
    lang_pair: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return groups, optionally filtered to those containing entries matching
    ANY of the supplied 'src:tgt' lang_pair values (OR logic)."""
    q = (
        select(WordGroup)
        .where(WordGroup.user_id == current_user.id)
        .order_by(WordGroup.position, WordGroup.id)
    )
    if lang_pair:
        pairs = []
        for p in lang_pair:
            parts = p.split(":", 1)
            if len(parts) == 2:
                pairs.append((parts[0], parts[1]))
        if pairs:
            conditions = [
                and_(
                    WordbookEntry.source_lang == src,
                    WordbookEntry.target_lang == tgt,
                )
                for src, tgt in pairs
            ]
            q = q.where(
                WordGroup.id.in_(
                    select(WordbookEntry.group_id).where(or_(*conditions))
                )
            )
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.post("/groups", response_model=WordGroupResponse, status_code=201)
async def create_group(
    body: WordGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    max_pos = (
        await db.execute(
            select(func.coalesce(func.max(WordGroup.position), 0))
            .where(WordGroup.user_id == current_user.id)
        )
    ).scalar() or 0

    group = WordGroup(
        user_id=current_user.id,
        name=body.name.strip(),
        position=max_pos + 1000,
    )
    db.add(group)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A group with this name already exists")
    await db.refresh(group)
    return group


@router.patch("/groups/{group_id}", response_model=WordGroupResponse)
async def update_group(
    group_id: int,
    body: WordGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = (
        await db.execute(
            select(WordGroup).where(
                WordGroup.id == group_id,
                WordGroup.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        group.name = data["name"].strip()
    if "position" in data and data["position"] is not None:
        group.position = data["position"]

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A group with this name already exists")
    await db.refresh(group)
    return group


@router.put("/groups/reorder", status_code=204)
async def reorder_groups(
    body: WordbookMoveItem,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move source_id to the position of target_id among the user's groups."""
    if body.source_id == body.target_id:
        raise HTTPException(status_code=422, detail="source_id and target_id must differ")

    all_rows = (
        await db.execute(
            select(WordGroup)
            .where(WordGroup.user_id == current_user.id)
            .order_by(WordGroup.position, WordGroup.id)
        )
    ).scalars().all()
    group_map = {g.id: g for g in all_rows}

    if body.source_id not in group_map or body.target_id not in group_map:
        raise HTTPException(status_code=404, detail="Group not found")

    ids = [g.id for g in all_rows]
    src_idx = ids.index(body.source_id)
    tgt_idx = ids.index(body.target_id)
    moving_forward = src_idx < tgt_idx
    new_ids = [i for i in ids if i != body.source_id]
    insert_at = new_ids.index(body.target_id)
    new_ids.insert(insert_at + 1 if moving_forward else insert_at, body.source_id)

    first = min(src_idx, tgt_idx)
    last = max(src_idx, tgt_idx)
    for i, gid in enumerate(new_ids[first:last + 1], start=first):
        group_map[gid].position = (i + 1) * 1000
    await db.commit()


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = (
        await db.execute(
            select(WordGroup).where(
                WordGroup.id == group_id,
                WordGroup.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.delete(group)
    await db.commit()


@router.put("/{entry_id}/group/{group_id}", status_code=204)
async def set_entry_group(
    entry_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign *entry_id* to *group_id*, replacing any previous group membership."""
    entry = (
        await db.execute(
            select(WordbookEntry).where(
                WordbookEntry.id == entry_id,
                WordbookEntry.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    group = (
        await db.execute(
            select(WordGroup).where(
                WordGroup.id == group_id,
                WordGroup.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    entry.group_id = group_id
    await db.commit()



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wordbook import WordbookEntry, WordGroup
from app.schemas.wordbook import (
    WordbookEntryBatchDelete,
    WordbookEntryCreate,
    WordbookEntryResponse,
    WordbookEntryUpdate,
    WordbookReorder,
    WordGroupCreate,
    WordGroupResponse,
    WordGroupUpdate,
)

router = APIRouter(prefix="/wordbook", tags=["wordbook"])


def _entry_query():
    return select(WordbookEntry).options(joinedload(WordbookEntry.group))


@router.get("", response_model=list[WordbookEntryResponse])
async def list_entries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            _entry_query()
            .where(WordbookEntry.user_id == current_user.id)
            .order_by(WordbookEntry.position.asc(), WordbookEntry.created_at.asc())
        )
    ).scalars().all()
    return rows


@router.post("", response_model=WordbookEntryResponse, status_code=201)
async def create_entry(
    entry: WordbookEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    max_pos = (
        await db.execute(
            select(func.coalesce(func.max(WordbookEntry.position), 0))
            .where(WordbookEntry.user_id == current_user.id)
        )
    ).scalar() or 0

    new_entry = WordbookEntry(
        user_id=current_user.id,
        position=max_pos + 1,
        **entry.model_dump(),
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


@router.post("/batch-delete", status_code=204)
async def batch_delete_entries(
    body: WordbookEntryBatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple entries in a single query, scoped to the current user."""
    if not body.ids:
        return
    await db.execute(
        delete(WordbookEntry).where(
            WordbookEntry.id.in_(body.ids),
            WordbookEntry.user_id == current_user.id,
        )
    )
    await db.commit()


@router.put("/reorder", status_code=204)
async def reorder_entries(
    body: WordbookReorder,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update positions for a contiguous slice of entries in one transaction.

    ``body.ids`` contains entry IDs in display order for the changed slice.
    ``body.offset`` is the 0-based index of ``ids[0]`` in the full list.
    Items outside the slice are not touched.
    """
    rows = (
        await db.execute(
            select(WordbookEntry).where(
                WordbookEntry.id.in_(body.ids),
                WordbookEntry.user_id == current_user.id,
            )
        )
    ).scalars().all()
    entry_map = {e.id: e for e in rows}
    for i, entry_id in enumerate(body.ids):
        if entry_id in entry_map:
            entry_map[entry_id].position = (body.offset + i + 1) * 1000
    await db.commit()


# ---------------------------------------------------------------------------
# Word groups
# ---------------------------------------------------------------------------

@router.get("/groups", response_model=list[WordGroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(WordGroup)
            .where(WordGroup.user_id == current_user.id)
            .order_by(WordGroup.position, WordGroup.id)
        )
    ).scalars().all()
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
    body: WordbookReorder,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update positions for a contiguous slice of groups in one transaction.

    Same offset-based semantics as ``PUT /wordbook/reorder``.
    """
    rows = (
        await db.execute(
            select(WordGroup).where(
                WordGroup.id.in_(body.ids),
                WordGroup.user_id == current_user.id,
            )
        )
    ).scalars().all()
    group_map = {g.id: g for g in rows}
    for i, group_id in enumerate(body.ids):
        if group_id in group_map:
            group_map[group_id].position = (body.offset + i + 1) * 1000
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


@router.delete("/{entry_id}/group", status_code=204)
async def clear_entry_group(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove *entry_id* from its group (sets group to null)."""
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

    entry.group_id = None
    await db.commit()

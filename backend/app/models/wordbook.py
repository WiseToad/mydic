from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, String, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User

class WordbookEntry(Base):
    __tablename__ = "wordbook_entries"
    __table_args__ = (
        UniqueConstraint('user_id', 'source_lang', 'target_lang', 'source_text', name='uq_wordbook_entries_user_word'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_code: Mapped[str | None] = mapped_column(String(25), nullable=True)
    source_lang: Mapped[str] = mapped_column(String(10))
    target_lang: Mapped[str] = mapped_column(String(10))
    source_text: Mapped[str] = mapped_column(Text)
    target_text: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str | None] = mapped_column(String(15), nullable=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("word_groups.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="wordbookEntries")
    group: Mapped["WordGroup"] = relationship(back_populates="entries")

class WordGroup(Base):
    __tablename__ = "word_groups"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_word_groups_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    user: Mapped["User"] = relationship(back_populates="wordbookGroups")
    entries: Mapped[list["WordbookEntry"]] = relationship(back_populates="group")

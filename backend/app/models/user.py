from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.wordbook import WordbookEntry, WordGroup

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))

    wordbookEntries: Mapped[list["WordbookEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    wordbookGroups: Mapped[list["WordGroup"]] = relationship(back_populates="user", cascade="all, delete-orphan")

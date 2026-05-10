from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TranslationCache(Base):
    __tablename__ = "translation_cache"
    __table_args__ = (
        UniqueConstraint("provider_code", "source_lang", "target_lang", "source_text", name="uq_translation_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(25), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(5))
    target_lang: Mapped[str] = mapped_column(String(5))
    detected_lang: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class DefinitionCache(Base):
    __tablename__ = "definition_cache"
    __table_args__ = (
        UniqueConstraint("provider_code", "lang", "word", name="uq_definition_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(25), nullable=False)
    lang: Mapped[str] = mapped_column(String(5))
    word: Mapped[str] = mapped_column(Text)
    definition: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class ContextCache(Base):
    __tablename__ = "context_cache"
    __table_args__ = (
        UniqueConstraint("provider_code", "source_lang", "target_lang", "source_text", name="uq_context_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(25), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(5))
    target_lang: Mapped[str] = mapped_column(String(5))
    source_text: Mapped[str] = mapped_column(Text)
    examples: Mapped[list[Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class LexicalCache(Base):
    __tablename__ = "lexical_cache"
    __table_args__ = (
        UniqueConstraint("provider_code", "source_lang", "target_lang", "word", name="uq_lexical_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(25), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(5))
    target_lang: Mapped[str] = mapped_column(String(5))
    word: Mapped[str] = mapped_column(Text)
    matches: Mapped[list[Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class TtsCache(Base):
    __tablename__ = "tts_cache"
    __table_args__ = (
        UniqueConstraint("provider_code", "voice", "lang", "text", "speed_ratio", name="uq_tts_cache"),
        Index("ix_tts_cache_needs_encode", "id", postgresql_where=text("needs_encode IS TRUE")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(25), nullable=False)
    voice: Mapped[str] = mapped_column(String(100), nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    speed_ratio: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    needs_encode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

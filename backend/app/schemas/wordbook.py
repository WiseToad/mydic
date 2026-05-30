from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator

from app.utils import normalize_text

GROUP_NAME_MAX_LEN = 25


class WordGroupCreate(BaseModel):
    name: str = Field(max_length=GROUP_NAME_MAX_LEN)


class WordGroupUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=GROUP_NAME_MAX_LEN)
    position: int | None = None


class WordGroupResponse(BaseModel):
    id: int
    name: str
    position: int
    model_config = {"from_attributes": True}


class WordbookEntryCreate(BaseModel):
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    notes: str | None = None
    provider_code: str | None = None
    color: str | None = None
    group_id: int | None = None

    @field_validator("source_text", "target_text")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_text(v)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, v: str | None) -> str | None:
        return normalize_text(v) if v else v


class WordbookEntryUpdate(BaseModel):
    source_text: str | None = None
    target_text: str | None = None
    notes: str | None = None
    position: int | None = None
    provider_code: str | None = None
    color: str | None = None

    @field_validator("notes")
    @classmethod
    def empty_notes_to_null(cls, v: str | None) -> str | None:
        return None if v == "" else v


class WordbookMoveItem(BaseModel):
    source_id: int
    target_id: int


class WordbookEntryResponse(BaseModel):
    id: int
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    notes: str | None = None
    position: int
    provider_code: str | None = None
    color: str | None = None
    group: WordGroupResponse
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def provider_abbrev(self) -> str | None:
        if not self.provider_code:
            return None
        from app.providers.registry import get_provider_by_code
        provider = get_provider_by_code(self.provider_code)
        return provider.abbrev if provider else None


class WordbookLookupResult(BaseModel):
    entry_id: int
    group_id: int
    color: str | None = None

from pydantic import BaseModel, field_validator


class TranslateRequest(BaseModel):
    source_text: str
    source_lang: str = "auto"
    target_lang: str
    provider_code: str

    @field_validator("source_text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        from app.utils import normalize_text
        v = normalize_text(v)
        if not v:
            raise ValueError("Text must not be empty")
        if len(v) > 5000:
            raise ValueError("Text too long (max 5000 characters)")
        return v


class TranslateResponse(BaseModel):
    translated_text: str
    detected_lang: str | None = None
    detected_lang_name: str | None = None

import os
from functools import lru_cache
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    app_home: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "mydic"
    postgres_password: str = Field(..., min_length=1)
    postgres_db: str = "mydic"

    @computed_field
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Authentication
    jwt_secret_key: str = Field(..., min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = 60 * 24 * 7  # 7 days

    registration_enabled: bool = False

    # Supported languages (comma-separated ISO 639-1 codes)
    supported_langs: Any = ["en", "es", "pt", "fr", "ru", "de", "it", "zh", "ja"]

    @field_validator("supported_langs", mode="before")
    @classmethod
    def _parse_lang_codes(cls, v: object) -> object:
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v

    # LibreTranslate
    libre_translate_enabled: bool = True
    libre_translate_url: str = "http://localhost:5000"

    # Yandex Cloud Translation API
    yandex_translate_enabled: bool = True
    yandex_translate_api_key: str = ""

    # Reverso Context (lexical + context examples)
    reverso_enabled: bool = True

    # Free Dictionary API (English definitions)
    freedict_enabled: bool = True

    # Wiktionary REST API (definitions + context examples)
    wiktionary_enabled: bool = True

    # Tatoeba sentence corpus (context examples)
    tatoeba_enabled: bool = True

    # Piper TTS
    piper_enabled: bool = True
    piper_voices_dir: str = "../tts/piper/voices"
    piper_slow_ratio: float | None = None
    
    # Kokoro TTS
    kokoro_enabled: bool = True
    kokoro_url: str = "http://localhost:8880"
    kokoro_slow_ratio: float | None = None

    # TTS common
    tts_cache_dir: str = "../tts/cache"
    tts_slow_ratio: float = 0.75

    # How long to wait before retrying a failed API call
    api_failure_retry_seconds: int = 600  # 10 minutes

@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file='.env')

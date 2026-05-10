import json
from pathlib import Path

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Full ISO 639-1 reference — loaded from the data file, never hard-coded here.
# ---------------------------------------------------------------------------
_ISO639_DATA: list[dict] = json.loads(
    (Path(__file__).parent.parent / "data" / "iso639-1.json").read_text(encoding="utf-8")
)

# code → English name  (e.g. "de" → "German")
ISO639_NAMES: dict[str, str] = {entry["code"]: entry["name"] for entry in _ISO639_DATA}

# code → ISO 639-2/T alpha-3  (e.g. "de" → "deu")  — used by the Tatoeba provider.
ISO639_ALPHA3: dict[str, str] = {entry["code"]: entry["alpha3"] for entry in _ISO639_DATA}


# ---------------------------------------------------------------------------
# Helpers — filtered by the deployment's supported_langs config.
# Called at request time (not module load) so they pick up the live settings.
# ---------------------------------------------------------------------------

def get_supported_language_codes() -> list[str]:
    """Return the ordered list of app-supported ISO 639-1 codes from config."""
    from app.config import get_settings
    return [c for c in get_settings().supported_langs if c in ISO639_NAMES]


def get_supported_language_names() -> dict[str, str]:
    """Return code→name mapping restricted to app-supported languages."""
    return {c: ISO639_NAMES[c] for c in get_supported_language_codes()}


class LanguageItem(BaseModel):
    code: str
    name: str
    position: int
    enabled: bool = True


class LanguageListResponse(BaseModel):
    languages: list[LanguageItem]


class LanguageListUpdate(BaseModel):
    languages: list[LanguageItem]

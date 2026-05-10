# Import all models so Alembic autogenerate can detect them
from app.models.user import User
from app.models.user_prefs import UserLanguagePref, UserProviderPref, UserTtsPref
from app.models.cache import TranslationCache, ContextCache, DefinitionCache, LexicalCache, TtsCache
from app.models.wordbook import WordbookEntry, WordGroup

__all__ = [
    "User",
    "UserLanguagePref",
    "UserProviderPref",
    "UserTtsPref",
    "TranslationCache",
    "LexicalCache",
    "DefinitionCache",
    "ContextCache",
    "TtsCache",
    "WordbookEntry",
    "WordGroup"
]

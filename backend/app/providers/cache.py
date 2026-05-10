"""Shared in-memory TTL cache for provider implementations."""
import time


class TTLCache[T]:
    """In-memory TTL cache for a single value of any type.

    Providers that fetch data from a remote API (e.g. supported languages,
    available voices) use this to avoid redundant network calls.

    Usage::

        class MyProvider:
            def __init__(self) -> None:
                self._lang_cache: TTLCache[frozenset[str]] = TTLCache(ttl=1800)

            async def _get_supported_langs(self) -> frozenset[str]:
                cached = self._lang_cache.get()
                if cached is not None:
                    return cached
                langs = frozenset(...)   # fetch from API
                self._lang_cache.set(langs)
                return langs
    """

    def __init__(self, ttl: float = 1800.0) -> None:
        self._ttl = ttl
        self._value: T | None = None
        self._cached_at: float = 0.0

    def get(self) -> T | None:
        """Return the cached value if it is still fresh, otherwise ``None``."""
        if self._value is not None and time.monotonic() - self._cached_at < self._ttl:
            return self._value
        return None

    def set(self, value: T) -> None:
        """Store *value* and record the current monotonic timestamp."""
        self._value = value
        self._cached_at = time.monotonic()

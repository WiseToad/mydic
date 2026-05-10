"""TtsProvider backed by a containerized Kokoro-FastAPI sidecar.

Kokoro-82M (https://github.com/hexgrad/kokoro) is an 82M-parameter StyleTTS2-
based open-weight TTS model.  Rather than loading the model in-process (which
would pull ~1.3 GB of ``torch`` wheels into the backend image and require the
``espeak-ng`` system dependency for non-English G2P), this provider talks to a
Kokoro-FastAPI server (https://github.com/remsky/Kokoro-FastAPI) running as a
separate container.  The server exposes an OpenAI-compatible
``/v1/audio/speech`` endpoint and ships with the model weights baked in.

Operational benefits over the in-process approach:
  - Backend image stays small; the heavy torch / kokoro / espeak-ng stack is
    isolated in the sidecar.
  - Kokoro can be GPU-accelerated independently (``kokoro-fastapi-gpu``) while
    the backend remains CPU-only.
  - Crashes / OOMs in the TTS engine no longer take the API process down.
  - The sidecar is multi-arch (amd64 + arm64), removing the implicit amd64
    lock the in-process build had through ``torch``.

Configuration (see :mod:`app.config`):
    ``kokoro_url``     base URL of the Kokoro-FastAPI server
                       (default ``http://localhost:8880``).
    ``kokoro_enabled`` hard off-switch evaluated by the provider registry.

Voice discovery is dynamic: ``list_voices()`` queries the sidecar's
``GET /v1/audio/voices`` endpoint (cached for ``_VOICES_TTL_SECONDS``) so any
fork or future addition is surfaced automatically.  When the sidecar is
unreachable, the call falls back to the static catalog in
``voices/kokoro.json`` so the UI never goes empty.  Voice ids match the
upstream Kokoro naming convention and are accepted as-is by the sidecar; the
language map is still resolved locally from ``voices/kokoro.json``.
"""

from __future__ import annotations

import time
import httpx

from app.providers.cache import TTLCache
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.tts import TtsProvider, TtsVoice

_KOKORO_LANG_MAP: dict[str, str] = {
    "en": "a",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "ja": "j",
    "pt": "p",
    "zh": "z"
}

_LANG_REGION_MAP: dict[str, str] = {
    "a": "en_US", "b": "en_GB"
}

# Voice-name prefix → ISO 639-1 lang code.  Used to map ids returned by the
# sidecar's ``GET /v1/audio/voices`` (which gives just names) onto the
# language a voice can pronounce.  Mirrors the upstream Kokoro convention
# captured in the static catalog.
_VOICE_PREFIX_LANG: dict[str, str] = {
    "af": "en", "am": "en",   # American English
    "bf": "en", "bm": "en",   # British English
    "ef": "es", "em": "es",   # Spanish
    "ff": "fr", "fm": "fr",   # French
    "hf": "hi", "hm": "hi",   # Hindi
    "if": "it", "im": "it",   # Italian
    "jf": "ja", "jm": "ja",   # Japanese
    "pf": "pt", "pm": "pt",   # Portuguese
    "zf": "zh", "zm": "zh",   # Chinese
}

# Health probe TTL: avoid hammering the sidecar's /health endpoint on every
# request while still picking up a recovery within a reasonable window.
_HEALTH_TTL_SECONDS = 30.0

# Voices-list TTL: refreshed less often than /health since the upstream
# catalog is stable across sidecar lifetimes.  A miss falls back to the
# static catalog so the UI never goes empty.
_VOICES_TTL_SECONDS = 300.0

# Synthesis HTTP timeout.  Kokoro is fast (~real-time on CPU, much faster on
# GPU) but cold model load on the sidecar's first request can take several
# seconds, hence the generous default.
_SYNTH_TIMEOUT_SECONDS = 60.0


class KokoroTtsProvider(Provider, TtsProvider):
    """TtsProvider backed by a Kokoro-FastAPI HTTP sidecar.

    Synthesis is delegated to the OpenAI-compatible ``/v1/audio/speech``
    endpoint exposed by the sidecar; this class just maps the MyDic
    request shape onto the upstream payload and surfaces transport errors
    in a way the router can map cleanly to HTTP status codes.
    """

    @property
    def code(self) -> str:
        return "KOKORO"

    @property
    def name(self) -> str:
        return "Kokoro TTS"

    @property
    def abbrev(self) -> str:
        return "Kokoro"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.TTS})

    @property
    def enabled(self) -> bool:
        from app.config import get_settings

        return get_settings().kokoro_enabled

    def __init__(self) -> None:
        super().__init__()
        from app.config import get_settings

        self._base_url: str = get_settings().kokoro_url.rstrip("/")
        # Cached health state; populated lazily so importing this module is
        # cheap and the sidecar isn't probed during tests.
        self._healthy: bool = False
        self._health_checked_at: float = 0.0
        self._unavailable_reason: str | None = (
            f"Kokoro-FastAPI not yet probed at {self._base_url}"
        )

        self._voices_cache: TTLCache[list[TtsVoice]] = TTLCache(ttl=300)

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _probe_health(self) -> None:
        """Refresh the cached health state by hitting the sidecar's /health."""
        now = time.monotonic()
        if self._healthy and (now - self._health_checked_at) < _HEALTH_TTL_SECONDS:
            return
        try:
            resp = httpx.get(f"{self._base_url}/health", timeout=2.0)
            resp.raise_for_status()
            self._healthy = True
            self._unavailable_reason = None
        except httpx.HTTPError as exc:
            self._healthy = False
            self._unavailable_reason = (
                f"Kokoro-FastAPI unreachable at {self._base_url}: {exc}"
            )
        finally:
            self._health_checked_at = now

    @property
    def is_available(self) -> bool:
        self._probe_health()
        return self._healthy

    @property
    def unavailable_reason(self) -> str | None:
        self._probe_health()
        return self._unavailable_reason

    # ------------------------------------------------------------------
    # TtsProvider
    # ------------------------------------------------------------------

    def _fetch_voices_from_api(self) -> list[TtsVoice]:
        """Refresh the cached voices list from ``GET /v1/audio/voices``.

        Returns:
            The freshly fetched list (also stored in ``self._voices_cache``)
            on success, or ``None`` when the sidecar is unreachable / the
            response is malformed.  Errors are silenced so the caller can
            seamlessly fall back to the static catalog.
        """
        try:
            resp = httpx.get(
                f"{self._base_url}/v1/audio/voices", timeout=2.0
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError):
            return []

        raw = payload.get("voices") if isinstance(payload, dict) else None
        if not isinstance(raw, list):
            return []

        voices: list[TtsVoice] = []
        for item in raw:
            # Sidecar returns ``["af_heart", ...]``.  Some forks may return
            # objects of shape ``{"id": "af_heart", ...}``; tolerate both.
            if isinstance(item, str):
                voice_id = item
            elif isinstance(item, dict) and isinstance(item.get("id"), str):
                voice_id = item["id"]
            else:
                continue
            
            prefix = voice_id[:2].lower()
            lang = _VOICE_PREFIX_LANG.get(prefix)
            languages: tuple[str, ...] = (lang,) if lang else ()

            prefix = voice_id[:1].lower()
            region = _LANG_REGION_MAP.get(prefix)

            name = voice_id[3:].lower()
            if region:
                name = f"{region} {name}"

            voices.append(TtsVoice(id=voice_id, name=name, languages=languages))

        return voices

    def list_voices(self) -> list[TtsVoice]:
        """Return the live Kokoro voice catalog when reachable.

        Behaviour:
          1. If the sidecar's ``GET /v1/audio/voices`` was hit successfully
             within ``_VOICES_TTL_SECONDS``, return the cached result.
          2. Otherwise re-probe the endpoint; on success cache and return
             the live list.
          3. On any failure, fall back to the static catalog shipped in
             ``voices/kokoro.json`` so the UI never sees an empty selector.

        Each entry is single-language (Kokoro derives the synthesis pipeline
        from the voice-name prefix).  Voices with an unknown prefix expose an
        empty ``languages`` tuple so the long-press popup still surfaces them
        and the user can pick explicitly.
        """
        cached = self._voices_cache.get()
        if cached is not None:
            return cached

        voices = self._fetch_voices_from_api()
        self._voices_cache.set(voices)
        return voices

    async def generate_speech(
        self,
        text: str,
        lang: str,
        voice: str,
        *,
        speed_ratio: float = 1.0,
    ) -> bytes:
        from app.utils import normalize_text

        if speed_ratio <= 0:
            raise ValueError("speed_ratio must be > 0")

        text = normalize_text(text)

        lang_code = _KOKORO_LANG_MAP.get(lang.lower())
        if lang_code is None:
            raise FileNotFoundError(
                f"Kokoro does not support language '{lang}'. "
                f"Supported: {', '.join(sorted(_KOKORO_LANG_MAP))}."
            )

        # OpenAI-compatible payload accepted by Kokoro-FastAPI.
        # ``response_format=wav`` keeps parity with the previous in-process
        # implementation so callers receive the same audio container.
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
            "speed": speed_ratio,
            "lang_code": lang_code,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=_SYNTH_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/audio/speech", json=payload
                )
        except httpx.HTTPError as exc:
            # Network-layer failures invalidate the cached health so the next
            # availability check re-probes immediately.
            self._healthy = False
            self._unavailable_reason = (
                f"Kokoro-FastAPI request failed at {self._base_url}: {exc}"
            )
            raise RuntimeError(self._unavailable_reason) from exc

        if resp.status_code == 400:
            # Kokoro-FastAPI returns 400 for invalid voice / unsupported
            # language; surface as ValueError → HTTP 422 in the router.
            raise ValueError(
                f"Kokoro synthesis rejected inputs: {resp.text[:200]}"
            )
        if resp.status_code >= 500:
            raise RuntimeError(
                f"Kokoro-FastAPI returned {resp.status_code}: "
                f"{resp.text[:200]}"
            )
        resp.raise_for_status()

        audio = resp.content
        if not audio:
            raise RuntimeError("Kokoro-FastAPI returned an empty audio body.")
        return audio

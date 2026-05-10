import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.providers.cache import TTLCache
from app.providers.provider import Provider, ProviderCapability
from app.providers.types.tts import TtsProvider, TtsVoice
from app.config import get_settings

class PiperTtsProvider(Provider, TtsProvider):
    """
    TtsProvider backed by the Piper local TTS binary.
    Synthesizes speech offline using pre-downloaded ONNX voice models.
    The piper binary must be available in PATH.
    """

    @property
    def code(self) -> str:
        return "PIPER"

    @property
    def name(self) -> str:
        return "Piper TTS"

    @property
    def abbrev(self) -> str:
        return "Piper"

    def supported_capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.TTS})

    @property
    def enabled(self) -> bool:
        return get_settings().piper_enabled

    def __init__(self) -> None:
        super().__init__()
        self._piper_in_path: bool = shutil.which("piper") is not None
        self._voices_cache: TTLCache[list[TtsVoice]] = TTLCache(ttl=300)

    @property
    def is_available(self) -> bool:
        return self._piper_in_path

    @property
    def unavailable_reason(self) -> str | None:
        if not self._piper_in_path:
            return "Piper binary not found in PATH"
        return None

    def list_voices(self) -> list[TtsVoice]:
        """Enumerate Piper voices found on disk."""
        cached = self._voices_cache.get()
        if cached is not None:
            return cached

        settings = get_settings()
        voices_dir = Path(settings.app_home) / settings.piper_voices_dir
        if not voices_dir.is_dir():
            return []

        voices: list[TtsVoice] = []
        for onnx_path in sorted(voices_dir.rglob("*.onnx")):
            rel = onnx_path.relative_to(voices_dir)
            voice_id = str(rel.with_suffix(""))  # strip .onnx

            # Defaults parsed from the filename stem (key format: region-speaker-quality)
            key = onnx_path.stem  # e.g. "en_US-lessac-medium"
            key_parts = key.split("-")
            region = key_parts[0] if key_parts else key
            quality = key_parts[-1] if len(key_parts) > 1 else ""
            speaker = "-".join(key_parts[1:-1]) if len(key_parts) > 2 else ""
            lang = ""

            # All name parts and language family from the collateral .onnx.json
            meta_path = onnx_path.parent / (onnx_path.name + ".json")
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    lang_info = meta.get("language", {})
                    region = lang_info.get("code") or region
                    speaker = meta.get("dataset") or speaker
                    quality = meta.get("audio", {}).get("quality") or quality
                    lang = lang_info.get("family")
                except Exception:
                    pass

            lang = lang or region.split("_")[0]
            langs: tuple[str, ...] = (lang.lower(),) if lang and len(lang) == 2 else ()

            name = f"{region} {speaker} ({quality})" if speaker else key

            voices.append(TtsVoice(id=voice_id, name=name, languages=langs))

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

        settings = get_settings()
        voice_path = os.path.join(settings.app_home, settings.piper_voices_dir, f"{voice}.onnx")
        if not os.path.exists(voice_path):
            raise FileNotFoundError(f"Piper voice '{voice}' not found.")

        length_scale = 1.0 / speed_ratio

        return await asyncio.get_running_loop().run_in_executor(
            None, self._synthesize, text, voice_path, length_scale
        )

    @staticmethod
    def _synthesize(text: str, voice_path: str, length_scale: float = 1.0) -> bytes:
        """Call the piper binary synchronously; meant to run in a thread pool."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            cmd = ["piper", "--model", voice_path, "--output_file", tmp_path]
            if length_scale != 1.0:
                cmd += ["--length_scale", f"{length_scale:.4f}"]
            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Piper exited with code {result.returncode}: "
                    f"{result.stderr.decode(errors='replace')}"
                )
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

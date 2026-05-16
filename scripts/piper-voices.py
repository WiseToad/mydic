#!/usr/bin/env python3

"""
Manage Piper TTS voice models.

Usage:
    piper-voices.py list
        Print the voice catalog grouped by language.

    piper-voices.py list --langs LANG ...
        Print the voice catalog filtered by one or more language codes.

    piper-voices.py list --update
        Fetch voices.json from Hugging Face and rebuild piper.json
        (high and medium quality voices only; lang codes auto-derived).

    piper-voices.py download --langs LANG ... [--type {all,medium,high}]
        Download voice models for one or more language codes.
        Without --type the first voice (medium-first order) per language
        is downloaded.

    piper-voices.py download --voices KEY ...
        Download explicitly specified voice keys.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
HF_VOICES_JSON = f"{HF_BASE}/voices.json"

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "piper-voices.toml"

config = {}
if CONFIG_FILE.exists():
    with CONFIG_FILE.open("rb") as f:
        config = tomllib.load(f)

DATA_DIR = (
    SCRIPT_DIR / config["PIPER_DATA_DIR"]
    if "PIPER_DATA_DIR" in config
    else SCRIPT_DIR.parent / "data" / "tts" / "piper"
)
VOICES_DIR = DATA_DIR / "voices"
CATALOG_FILE = DATA_DIR / "voices.json"

# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

def load_catalog() -> list[dict]:
    """Return voices parsed from the curated JSON."""
    if not CATALOG_FILE.exists():
        sys.exit(
            f"[fatal] Catalog not found at {CATALOG_FILE}.  "
            "Run 'list --update' first."
        )
    with CATALOG_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    voices = data.get("voices") or []
    if not voices:
        sys.exit(
            f"[fatal] No voices found in {CATALOG_FILE}.  "
            "Run 'list --update' to regenerate it."
        )
    return voices


def index_by_lang(voices: list[dict]) -> dict[str, list[dict]]:
    """Group voices by ISO 639-1 family; within each language sort
    medium-first, then alphabetically by key."""
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for v in voices:
        by_lang[v["lang"]].append(v)
    quality_rank = {"medium": 0, "high": 1}
    for lang in by_lang:
        by_lang[lang].sort(
            key=lambda v: (quality_rank.get(v["quality"], 99), v["key"])
        )
    return by_lang


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest*, skipping if the file already exists."""
    if dest.exists():
        print(f"  [skip] {dest} already exists")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  [ok]   {dest}")
    except Exception as e:
        print(f"  [fail] {dest}: {e}")
        dest.unlink(missing_ok=True)


def try_download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest*, silently skipping 404 (file is optional)."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  [ok]   {dest}")
    except urllib.error.HTTPError as e:
        dest.unlink(missing_ok=True)
        if e.code != 404:
            print(f"  [warn] {dest.name}: HTTP {e.code}")
    except Exception as e:
        dest.unlink(missing_ok=True)
        print(f"  [warn] {dest.name}: {e}")


def download_voice(voice: dict) -> None:
    """Fetch .onnx, .onnx.json, and MODEL_CARD (if present) for one voice.

    Files are written into a hierarchy mirroring the source repository::

        VOICES_DIR / en / en_US / lessac / medium / en_US-lessac-medium.onnx
    """
    path = voice["path"]  # e.g. "en/en_US/lessac/medium/en_US-lessac-medium"
    encoded_path = urllib.parse.quote(path, safe="/")  # handle non-ASCII names
    voice_subdir = Path(path).parent   # e.g. "en/en_US/lessac/medium"
    encoded_subdir = urllib.parse.quote(str(voice_subdir), safe="/")

    for ext in (".onnx", ".onnx.json"):
        download_file(
            f"{HF_BASE}/{encoded_path}{ext}", 
            VOICES_DIR / f"{path}{ext}"
        )

    try_download_file(
        f"{HF_BASE}/{encoded_subdir}/MODEL_CARD",
        VOICES_DIR / voice_subdir / "MODEL_CARD",
    )


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def do_update_list() -> None:
    """Fetch voices.json from HF and rebuild piper.json (high/medium only)."""
    print(f"Fetching {HF_VOICES_JSON} ...")
    try:
        with urllib.request.urlopen(HF_VOICES_JSON) as resp:
            raw: dict = json.load(resp)
    except Exception as e:
        sys.exit(f"[fatal] Failed to fetch voices.json: {e}")

    voices = []
    for key, info in sorted(raw.items()):
        quality = info.get("quality", "")
        if quality not in ("medium", "high"):
            continue
        lang_info = info.get("language", {})
        lang = lang_info.get("family", "")
        region = lang_info.get("code", "")
        speaker = info.get("name", "")
        # Derive path stem from the files dict (strip .onnx suffix)
        files = info.get("files", {})
        onnx_key = next((k for k in files if k.endswith(".onnx")), None)
        if onnx_key is None:
            continue
        path = onnx_key.removesuffix(".onnx")
        voices.append({
            "key": key,
            "lang": lang,
            "region": region,
            "speaker": speaker,
            "quality": quality,
            "path": path,
        })

    data = {
        "voices": voices,
    }
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Saved {len(voices)} voices to {CATALOG_FILE}.")


def cmd_list(args: argparse.Namespace) -> None:
    """Update catalog (--update) or print entries grouped by language."""
    if args.update:
        do_update_list()
        return
    voices = load_catalog()
    by_lang = index_by_lang(voices)
    langs = args.langs if args.langs else sorted(by_lang.keys())
    for lang in langs:
        entries = by_lang.get(lang)
        if not entries:
            print(f"[warn] No voices for lang '{lang}'")
            continue
        print(f"{lang}:")
        for v in entries:
            print(f"  {v['key']:<40} ({v['quality']})")


def cmd_download(args: argparse.Namespace) -> None:
    """Download voices by language or by explicit voice keys."""
    voices = load_catalog()

    if args.voices:
        # Explicit voice keys — --type is not applicable.
        by_key = {v["key"]: v for v in voices}
        print(f"Downloading voices to: {VOICES_DIR.resolve()}\n")
        for key in args.voices:
            v = by_key.get(key)
            if v is None:
                print(f"[warn] Unknown voice key '{key}', skipping")
                continue
            print(f"Downloading voice: {key}")
            download_voice(v)
            print()
    else:
        # Language-based download.
        by_lang = index_by_lang(voices)
        voice_type: str | None = args.type
        print(f"Downloading voices to: {VOICES_DIR.resolve()}\n")
        for lang in args.langs:
            entries = by_lang.get(lang)
            if not entries:
                print(f"[warn] No voices in catalog for lang '{lang}', skipping")
                continue
            if voice_type is None:
                to_download = [entries[0]]  # first (medium-first, then alphabetical)
            elif voice_type == "all":
                to_download = entries
            else:
                to_download = [v for v in entries if v["quality"] == voice_type]
                if not to_download:
                    print(f"[warn] No {voice_type} voices for lang '{lang}', skipping")
                    continue
            for v in to_download:
                print(f"Downloading voice: {v['key']}")
                download_voice(v)
                print()

    print("Done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_list = sub.add_parser(
        "list",
        help="Print the voice catalog grouped by language",
    )
    list_sel = p_list.add_mutually_exclusive_group()
    list_sel.add_argument(
        "--update",
        action="store_true",
        help="Fetch voices.json from Hugging Face and rebuild piper.json (no listing)",
    )
    list_sel.add_argument(
        "--langs",
        nargs="+",
        metavar="LANG",
        help="Restrict listing to the given ISO 639-1 language codes",
    )

    p_download = sub.add_parser(
        "download",
        help="Download voice model files",
    )
    sel = p_download.add_mutually_exclusive_group(required=True)
    sel.add_argument(
        "--langs",
        nargs="+",
        metavar="LANG",
        help="Language codes to download",
    )
    sel.add_argument(
        "--voices",
        nargs="+",
        metavar="KEY",
        help="Explicit voice keys to download (e.g. en_US-lessac-medium)",
    )
    p_download.add_argument(
        "--type",
        choices=["all", "medium", "high"],
        default=None,
        help=(
            "Quality filter: 'medium', 'high', or 'all' (only with --langs).  "
            "Omit to download the first voice per language."
        ),
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "download" and args.voices and args.type is not None:
        p_download.error("--type is not allowed with --voices")

    {
        "list": cmd_list,
        "download": cmd_download,
    }[args.command](args)


if __name__ == "__main__":
    main()

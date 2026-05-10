#!/usr/bin/env python3

"""Encode cached TTS clips from wav to mp3 to reclaim disk space.

Usage:
    encode-tts.py             # one batch (default 50)
    encode-tts.py --batch 200 # bigger batch
    encode-tts.py --all       # drain in batches
    encode-tts.py --dry-run   # show plan, do nothing
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.cache import TtsCache

DEFAULT_BATCH = 50
DEFAULT_BITRATE_QSCALE = "4"  # libmp3lame VBR ~ 165 kbps mono speech

def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _encode_wav_to_mp3(src: Path, dst: Path, qscale: str) -> None:
    """Run ffmpeg synchronously and raise on non-zero exit."""
    cmd = [
        "ffmpeg",
        "-y", # to overwrite a stale ``dst`` left over from a previous interrupted run
        "-loglevel", "error",
        "-i", str(src),
        "-codec:a", "libmp3lame",
        "-qscale:a", qscale,
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg exited with code {result.returncode}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )

async def _process_batch(
    session: AsyncSession,
    *,
    cache_root: Path,
    batch: int,
    qscale: str,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Process up to ``batch`` rows; return (encoded, skipped, failed)."""
    stmt = (
        select(TtsCache)
        .where(TtsCache.needs_encode.is_(True))
        .order_by(TtsCache.id)
        .limit(batch)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    encoded = skipped = failed = 0

    for row in rows:
        if not row.filename.endswith(".wav"):
            print(f"[skip] not a wav, clearing flag: {row.filename}", flush=True)
            if not dry_run:
                await session.execute(
                    update(TtsCache)
                    .where(TtsCache.id == row.id)
                    .values(needs_encode=False)
                )
                await session.commit()
            skipped += 1
            continue

        wav_path = cache_root / row.filename
        if not wav_path.exists():
            print(f"[skip] wav missing, clearing flag: {row.filename}", flush=True)
            if not dry_run:
                await session.execute(
                    update(TtsCache)
                    .where(TtsCache.id == row.id)
                    .values(needs_encode=False)
                )
                await session.commit()
            skipped += 1
            continue

        mp3_rel = row.filename[:-len(".wav")] + ".mp3"
        mp3_path = cache_root / mp3_rel

        if dry_run:
            print(f"[plan] {row.filename} -> {mp3_rel}", flush=True)
            encoded += 1
            continue

        try:
            _encode_wav_to_mp3(wav_path, mp3_path, qscale)
        except Exception as exc:
            print(f"[fail] {row.filename}: {exc}", flush=True)
            # Best-effort cleanup of a partial mp3.
            try:
                mp3_path.unlink(missing_ok=True)
            except OSError:
                pass
            failed += 1
            continue

        await session.execute(
            update(TtsCache)
            .where(TtsCache.id == row.id)
            .values(filename=mp3_rel, needs_encode=False)
        )
        await session.commit()
        try:
            wav_path.unlink()
        except OSError as exc:
            print(f"[warn] could not unlink {row.filename}: {exc}", flush=True)
        encoded += 1
        print(f"[ok]   {row.filename} -> {mp3_rel}", flush=True)

    return encoded, skipped, failed


async def _amain(args: argparse.Namespace) -> int:
    if not _have_ffmpeg() and not args.dry_run:
        print("[fatal] ffmpeg not found in PATH", file=sys.stderr)
        return 2

    settings = get_settings()
    cache_root = Path(os.path.abspath(settings.tts_cache_dir))
    if not cache_root.is_dir():
        print(f"[fatal] tts_cache_dir does not exist: {cache_root}", file=sys.stderr)
        return 2

    total_encoded = total_skipped = total_failed = 0

    while True:
        async with AsyncSessionLocal() as session:
            encoded, skipped, failed = await _process_batch(
                session,
                cache_root=cache_root,
                batch=args.batch,
                qscale=args.qscale,
                dry_run=args.dry_run,
            )
        total_encoded += encoded
        total_skipped += skipped
        total_failed += failed
        if not args.all or (encoded + skipped + failed) == 0 or args.dry_run:
            break

    print(
        f"\nSummary: encoded={total_encoded}, skipped={total_skipped}, "
        f"failed={total_failed}",
        flush=True,
    )
    return 0 if total_failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--batch",
        type=int,
        default=DEFAULT_BATCH,
        help=f"Max rows per batch (default: {DEFAULT_BATCH})",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Drain the queue: keep running batches until nothing remains",
    )
    parser.add_argument(
        "--qscale",
        default=DEFAULT_BITRATE_QSCALE,
        help=(
            "libmp3lame VBR quality (lower = higher bitrate; default 4 \u2248 "
            "165 kbps for mono speech)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be encoded without touching files or the DB",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()

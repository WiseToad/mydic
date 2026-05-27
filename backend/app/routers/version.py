import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["meta"])

# Dev: VERSION.txt is three directories above this file (project root).
# Prod: override via VERSION_FILE env var (file is mounted into the container).
_DEFAULT = Path(__file__).resolve().parents[3] / "VERSION.txt"


def _read_version() -> str:
    path = Path(os.environ.get("VERSION_FILE", str(_DEFAULT)))
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="VERSION.txt not found")


@router.get("/version")
async def get_version() -> dict[str, str]:
    return {"version": _read_version()}

#!/usr/bin/env python3

"""Manage app users: add, delete, rename, set-password, list.

Usage:
    users.py list
    users.py add     <username>
    users.py add     <username> --password <pass>
    users.py delete  <username>
    users.py rename  <username> <new_username>
    users.py set-password <username>
    users.py set-password <username> --password <pass>

When `--password` is omitted for `add` and `password`, the
password is read interactively from the terminal (no echo).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.jwt import hash_password
from app.database import AsyncSessionLocal
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt_password(prompt: str = "Password: ") -> str:
    """Read a password interactively, confirming it once."""
    while True:
        pw = getpass.getpass(prompt)
        if not pw:
            print("[error] password must not be empty", file=sys.stderr)
            continue
        confirm = getpass.getpass("Confirm password: ")
        if pw != confirm:
            print("[error] passwords do not match, try again", file=sys.stderr)
            continue
        return pw


async def _get_user(session, username: str) -> User | None:
    return (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_list(_args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        users = list(
            (await session.execute(select(User).order_by(User.username))).scalars()
        )
    if not users:
        print("(no users)")
    else:
        print(f"{'id':>6}  username")
        print(f"{'------':>6}  --------")
        for u in users:
            print(f"{u.id:>6}  {u.username}")
    return 0


async def cmd_add(args: argparse.Namespace) -> int:
    password = args.password or _prompt_password()
    async with AsyncSessionLocal() as session:
        if await _get_user(session, args.username):
            print(f"[error] user '{args.username}' already exists", file=sys.stderr)
            return 1
        session.add(User(username=args.username, password_hash=hash_password(password)))
        try:
            await session.commit()
        except IntegrityError:
            print(f"[error] user '{args.username}' already exists", file=sys.stderr)
            return 1
    print(f"[ok] user '{args.username}' created")
    return 0


async def cmd_delete(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        user = await _get_user(session, args.username)
        if not user:
            print(f"[error] user '{args.username}' not found", file=sys.stderr)
            return 1
        await session.delete(user)
        await session.commit()
    print(f"[ok] user '{args.username}' deleted")
    return 0


async def cmd_rename(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        user = await _get_user(session, args.username)
        if not user:
            print(f"[error] user '{args.username}' not found", file=sys.stderr)
            return 1
        if await _get_user(session, args.new_username):
            print(f"[error] username '{args.new_username}' is already taken", file=sys.stderr)
            return 1
        user.username = args.new_username
        try:
            await session.commit()
        except IntegrityError:
            print(f"[error] username '{args.new_username}' is already taken", file=sys.stderr)
            return 1
    print(f"[ok] '{args.username}' renamed to '{args.new_username}'")
    return 0


async def cmd_password(args: argparse.Namespace) -> int:
    password = args.password or _prompt_password("New password: ")
    async with AsyncSessionLocal() as session:
        user = await _get_user(session, args.username)
        if not user:
            print(f"[error] user '{args.username}' not found", file=sys.stderr)
            return 1
        user.password_hash = hash_password(password)
        await session.commit()
    print(f"[ok] password updated for '{args.username}'")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_COMMANDS = {
    "list": cmd_list,
    "add": cmd_add,
    "delete": cmd_delete,
    "rename": cmd_rename,
    "password": cmd_password,
}


async def _amain(args: argparse.Namespace) -> int:
    return await _COMMANDS[args.command](args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage app users.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    sub.add_parser("list", help="List all users")

    p_add = sub.add_parser("add", help="Create a new user")
    p_add.add_argument("username")
    p_add.add_argument("--password", default=None, help="Password (prompted if omitted)")

    p_del = sub.add_parser("delete", help="Delete a user and all their data")
    p_del.add_argument("username")

    p_ren = sub.add_parser("rename", help="Change a user's username")
    p_ren.add_argument("username", help="Current username")
    p_ren.add_argument("new_username", help="New username")

    p_sp = sub.add_parser("password", help="Change a user's password")
    p_sp.add_argument("username")
    p_sp.add_argument("--password", default=None, help="New password (prompted if omitted)")

    args = parser.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()

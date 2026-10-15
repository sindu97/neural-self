"""Operational commands.

Usage:
    python -m neuralshelf.cli promote-admin someone@example.com
    python -m neuralshelf.cli demote-admin someone@example.com
"""

import argparse
import sys

from neuralshelf.db import model_registry  # noqa: F401  (registers all models)
from neuralshelf.db.session import SessionLocal
from neuralshelf.features.users.repository import UserRepository


def set_admin(email: str, *, is_admin: bool) -> int:
    with SessionLocal() as db:
        repository = UserRepository(db)
        user = repository.get_by_email(email.strip().lower())
        if user is None:
            print(f"No user with email {email!r}.", file=sys.stderr)
            return 1
        repository.set_admin(user, is_admin=is_admin)
        db.commit()
    print(f"{email} is {'now' if is_admin else 'no longer'} an administrator.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m neuralshelf.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("promote-admin", "grant administrator access"),
        ("demote-admin", "revoke administrator access"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("email")

    args = parser.parse_args(argv)
    return set_admin(args.email, is_admin=args.command == "promote-admin")


if __name__ == "__main__":
    raise SystemExit(main())

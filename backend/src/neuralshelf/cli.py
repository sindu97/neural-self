"""NeuralShelf management commands (run from the backend/ directory).

    python -m neuralshelf.cli migrate                    apply all pending migrations
    python -m neuralshelf.cli migrate:status             show current and pending migrations
    python -m neuralshelf.cli migrate:rollback [--steps N]
    python -m neuralshelf.cli migrate:fresh [--seed] [--yes]
                                                         DROP EVERYTHING, re-run all migrations
    python -m neuralshelf.cli make:migration "add x to y"
                                                         autogenerate a migration from model changes
    python -m neuralshelf.cli db:seed [--only users|documents]
    python -m neuralshelf.cli promote-admin EMAIL
    python -m neuralshelf.cli demote-admin EMAIL

Destructive commands (migrate:fresh, db:seed) refuse to run when APP_ENV=production.
"""

import argparse
import shutil
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from neuralshelf.core.config import get_settings
from neuralshelf.db import model_registry  # noqa: F401  (registers all models)
from neuralshelf.db.session import SessionLocal, engine
from neuralshelf.features.users.repository import UserRepository

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class CommandError(Exception):
    """A command could not run; the message is shown to the user."""


def alembic_config() -> Config:
    """Load alembic.ini from the working directory, falling back to the backend root."""
    # Prefer ./alembic.ini (the backend dir, or /app in the Docker image).
    for candidate in (Path.cwd() / "alembic.ini", _BACKEND_ROOT / "alembic.ini"):
        if candidate.exists():
            return Config(str(candidate))
    raise CommandError("alembic.ini not found; run this from the backend/ directory.")


def refuse_in_production(action: str) -> None:
    """Raise CommandError when APP_ENV is production; guards destructive commands."""
    if get_settings().app_env == "production":
        raise CommandError(f"Refusing to {action} with APP_ENV=production.")


def confirm(prompt: str, *, assume_yes: bool) -> None:
    """Require the user to type 'yes', unless ``assume_yes``. Refuses without a terminal."""
    if assume_yes:
        return
    if not sys.stdin.isatty():
        raise CommandError("Confirmation required; re-run with --yes.")
    if input(f"{prompt} Type 'yes' to continue: ").strip().lower() != "yes":
        raise CommandError("Aborted.")


# ---- migrations -------------------------------------------------------------

def migrate(_: argparse.Namespace) -> None:
    """``migrate``: apply all pending migrations."""
    command.upgrade(alembic_config(), "head")
    print("Database is up to date.")


def migrate_status(_: argparse.Namespace) -> None:
    """``migrate:status``: list every migration as applied or pending."""
    script = ScriptDirectory.from_config(alembic_config())
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()

    applied = (
        {revision.revision for revision in script.iterate_revisions(current, "base")}
        if current
        else set()
    )
    print(f"Current revision: {current or '(none: empty database)'}\n")
    for revision in reversed(list(script.walk_revisions())):  # oldest first
        state = "applied" if revision.revision in applied else "PENDING"
        print(f"  [{state:>7}] {revision.revision}  {revision.doc}")


def migrate_rollback(args: argparse.Namespace) -> None:
    """``migrate:rollback``: undo the latest ``--steps`` migrations."""
    refuse_in_production("roll back migrations")
    command.downgrade(alembic_config(), f"-{args.steps}")
    print(f"Rolled back {args.steps} migration(s).")


def migrate_fresh(args: argparse.Namespace) -> None:
    """Drop every table (and uploaded files), then rebuild from migrations."""
    refuse_in_production("drop the database")
    settings = get_settings()
    confirm(
        f"This deletes ALL data in '{engine.url.database}' and all uploaded files.",
        assume_yes=args.yes,
    )

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()  # pooled connections may cache the dropped objects
    print("Dropped all tables.")

    upload_dir = settings.upload_dir.resolve()
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
        print(f"Deleted uploaded files in {upload_dir}.")

    migrate(args)
    if args.seed:
        db_seed(argparse.Namespace(only=None))


def make_migration(args: argparse.Namespace) -> None:
    """``make:migration``: autogenerate a migration from model changes."""
    command.revision(alembic_config(), message=args.message, autogenerate=True)
    print("Review the generated file before applying it: autogenerate can't detect everything.")


# ---- seeding and users ------------------------------------------------------

def db_seed(args: argparse.Namespace) -> None:
    """``db:seed``: run every seeder, or only the one named by ``--only``."""
    refuse_in_production("seed demo accounts")
    from neuralshelf.db.seeders import SEEDERS, seed_all

    print("Seeding:")
    with SessionLocal() as db:
        if args.only:
            SEEDERS[args.only](db)
        else:
            seed_all(db)
    print("Done.")


def set_admin(args: argparse.Namespace) -> None:
    """``promote-admin`` / ``demote-admin``: set a user's administrator flag."""
    is_admin = args.command == "promote-admin"
    with SessionLocal() as db:
        repository = UserRepository(db)
        user = repository.get_by_email(args.email.strip().lower())
        if user is None:
            raise CommandError(f"No user with email {args.email!r}.")
        repository.set_admin(user, is_admin=is_admin)
        db.commit()
    print(f"{args.email} is {'now' if is_admin else 'no longer'} an administrator.")


# ---- entry point ------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser, with one subcommand per management command."""
    parser = argparse.ArgumentParser(
        prog="python -m neuralshelf.cli",
        description="NeuralShelf management commands.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    commands.add_parser("migrate", help="apply all pending migrations").set_defaults(
        handler=migrate
    )
    commands.add_parser("migrate:status", help="show applied and pending migrations").set_defaults(
        handler=migrate_status
    )

    rollback = commands.add_parser("migrate:rollback", help="undo the latest migration(s)")
    rollback.add_argument("--steps", type=int, default=1)
    rollback.set_defaults(handler=migrate_rollback)

    fresh = commands.add_parser("migrate:fresh", help="drop everything and re-run all migrations")
    fresh.add_argument("--seed", action="store_true", help="run the seeders afterwards")
    fresh.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    fresh.set_defaults(handler=migrate_fresh)

    make = commands.add_parser("make:migration", help="autogenerate a migration from the models")
    make.add_argument("message")
    make.set_defaults(handler=make_migration)

    seed = commands.add_parser("db:seed", help="insert development seed data")
    seed.add_argument("--only", choices=["users", "documents"])
    seed.set_defaults(handler=db_seed)

    for name, help_text in (
        ("promote-admin", "grant administrator access"),
        ("demote-admin", "revoke administrator access"),
    ):
        admin = commands.add_parser(name, help=help_text)
        admin.add_argument("email")
        admin.set_defaults(handler=set_admin)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one command and return the exit code: 0 on success, 1 on a CommandError."""
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except CommandError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

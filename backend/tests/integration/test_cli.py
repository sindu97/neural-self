"""Management commands: migrate, status, rollback, fresh, seed.

Each test gets its own empty database (neuralshelf_cli_test), because these
commands create and drop the whole schema.
"""

from collections.abc import Generator

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, func, make_url, select, text
from sqlalchemy.orm import sessionmaker

from neuralshelf import cli
from neuralshelf.core.config import get_settings
from neuralshelf.db import seeders
from neuralshelf.features.documents.models import Document, IngestionJob
from neuralshelf.features.documents.storage import LocalFileStorage
from neuralshelf.features.users.models import User

pytestmark = pytest.mark.integration

CLI_DATABASE = "neuralshelf_cli_test"


@pytest.fixture
def cli_engine(engine, monkeypatch, tmp_path) -> Generator[Engine, None, None]:
    """Point the CLI, Alembic and the seeders at a brand-new empty database."""
    settings = get_settings()
    base_url = make_url(settings.database_url.get_secret_value())
    admin = create_engine(
        base_url.set(drivername="postgresql+psycopg"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{CLI_DATABASE}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{CLI_DATABASE}"'))

    url = base_url.set(database=CLI_DATABASE)
    test_engine = create_engine(url.set(drivername="postgresql+psycopg"))
    monkeypatch.setattr(
        settings, "database_url", SecretStr(url.render_as_string(hide_password=False))
    )
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(cli, "engine", test_engine)
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(
        seeders, "get_file_storage", lambda: LocalFileStorage(tmp_path / "uploads")
    )

    yield test_engine

    test_engine.dispose()
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{CLI_DATABASE}" WITH (FORCE)'))
    admin.dispose()


def run(*args: str) -> int:
    return cli.main(list(args))


def count(engine: Engine, model) -> int:
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(model))


def test_migrate_builds_an_empty_database(cli_engine, capsys) -> None:
    assert run("migrate:status") == 0
    assert "(none: empty database)" in capsys.readouterr().out

    assert run("migrate") == 0
    assert run("migrate:status") == 0
    status = capsys.readouterr().out
    assert "PENDING" not in status
    assert status.count("[applied]") >= 8


def test_rollback_then_migrate_again(cli_engine, capsys) -> None:
    run("migrate")

    assert run("migrate:rollback", "--steps", "2") == 0
    run("migrate:status")
    assert capsys.readouterr().out.count("[PENDING]") == 2

    assert run("migrate") == 0
    run("migrate:status")
    assert "PENDING" not in capsys.readouterr().out


def test_seed_is_idempotent(cli_engine) -> None:
    run("migrate")

    assert run("db:seed") == 0
    assert run("db:seed") == 0

    assert count(cli_engine, User) == 2
    assert count(cli_engine, Document) == 1
    assert count(cli_engine, IngestionJob) == 1
    with cli_engine.connect() as connection:
        admin = connection.scalar(select(User.is_admin).where(User.email == seeders.ADMIN.email))
    assert admin is True


def test_fresh_drops_everything_and_reseeds(cli_engine, tmp_path) -> None:
    run("migrate")
    run("db:seed")
    with cli_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, name, email, password_hash) "
                 "VALUES (gen_random_uuid(), 'Extra', 'extra@example.com', 'x')")
        )
    stray_file = tmp_path / "uploads" / "stray.pdf"
    stray_file.write_bytes(b"%PDF-")

    assert run("migrate:fresh", "--yes", "--seed") == 0

    with cli_engine.connect() as connection:
        emails = set(connection.scalars(select(User.email)))
    assert emails == {seeders.ADMIN.email, seeders.DEMO.email}
    assert not stray_file.exists()
    assert count(cli_engine, Document) == 1


def test_fresh_requires_confirmation(cli_engine, monkeypatch, capsys) -> None:
    run("migrate")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert run("migrate:fresh") == 1
    assert "--yes" in capsys.readouterr().err


@pytest.mark.parametrize(
    "command", [("migrate:fresh", "--yes"), ("db:seed",), ("migrate:rollback",)]
)
def test_destructive_commands_refuse_in_production(
    cli_engine, monkeypatch, capsys, command
) -> None:
    run("migrate")
    monkeypatch.setattr(get_settings(), "app_env", "production")

    assert run(*command) == 1
    assert "APP_ENV=production" in capsys.readouterr().err
    assert count(cli_engine, User) == 0  # nothing was seeded or dropped

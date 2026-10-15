
"""Alembic migration environment for NeuralShelf."""

import logging
import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Import all models so they register on Base.metadata for autogenerate.
import neuralshelf.db.model_registry  # noqa: F401
from neuralshelf.core.config import get_settings
from neuralshelf.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
database_url = settings.database_url.get_secret_value()

# Explicitly use the psycopg 3 driver already installed by NeuralShelf.
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)

target_metadata = Base.metadata

# Arbitrary constant identifying the "migrations running" advisory lock.
MIGRATION_LOCK_KEY = 4_242_001
MIGRATION_LOCK_POLL_SECONDS = 1.0
MIGRATION_LOCK_TIMEOUT_SECONDS = 600.0

logger = logging.getLogger("alembic.env")


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def acquire_migration_lock(connection) -> None:
    """Serialize migration runs across processes (e.g. two deploys at once).

    The losers wait, then find nothing left to do. Waiting uses
    pg_try_advisory_lock with no transaction left open between attempts: a
    transaction blocked in pg_advisory_lock would deadlock with the winner's
    CREATE INDEX CONCURRENTLY, which waits for all open transactions.
    """
    waited = 0.0
    while True:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY}
        ).scalar_one()
        connection.commit()
        if acquired:
            return
        if waited >= MIGRATION_LOCK_TIMEOUT_SECONDS:
            raise RuntimeError("Timed out waiting for another migration run to finish.")
        if waited == 0:
            logger.info("Another migration run is in progress; waiting for it to finish.")
        time.sleep(MIGRATION_LOCK_POLL_SECONDS)
        waited += MIGRATION_LOCK_POLL_SECONDS


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        acquire_migration_lock(connection)
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY}
            )
            connection.commit()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

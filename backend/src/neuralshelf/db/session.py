
"""Database engine, session factory, and connectivity checks."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

database_url = make_url(settings.database_url.get_secret_value())

# Use the psycopg 3 driver already installed in the project.
if database_url.drivername == "postgresql":
    database_url = database_url.set(drivername="postgresql+psycopg")

engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session to a request."""
    with SessionLocal() as session:
        yield session


def get_session_factory() -> sessionmaker[Session]:
    """Provide the session factory, for work that outlives the request's session.

    For example, saving a streamed answer after its last token.
    """
    return SessionLocal


def check_database_connection() -> bool:
    """Return True if PostgreSQL accepts a simple query."""
    try:
        with engine.connect() as connection:
            return connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    except Exception:
        logger.exception("Database connectivity check failed.")
        return False

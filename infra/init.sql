-- Runs once when the Docker database volume is first created.
-- The schema itself is managed by Alembic migrations (alembic upgrade head);
-- only the extension is created here because it needs superuser rights.
CREATE EXTENSION IF NOT EXISTS vector;

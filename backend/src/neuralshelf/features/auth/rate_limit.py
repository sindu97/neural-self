"""Fixed-window rate limiting backed by PostgreSQL.

Each hit is one atomic upsert (``INSERT ... ON CONFLICT DO UPDATE ...
RETURNING count``), so concurrent requests across processes are counted
exactly. Good for low-volume, high-value endpoints like login; use a
dedicated store (e.g. Redis) for limiting high-traffic endpoints.
"""

import math
import random
import time
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from neuralshelf.core.config import get_settings
from neuralshelf.core.exceptions import RateLimitExceededError
from neuralshelf.features.auth.models import RateLimitBucket

# Roughly 1 in 100 hits also deletes stale windows, so the table stays small
# without a separate cleanup job.
CLEANUP_PROBABILITY = 0.01
RETENTION = timedelta(days=1)


def client_ip(request: Request) -> str:
    """Client address as seen by the server.

    Behind a reverse proxy, run uvicorn with --proxy-headers and
    --forwarded-allow-ips set to the proxy's address so this is the real
    client IP rather than the proxy's.
    """
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def hit(self, key: str, *, limit: int) -> None:
        """Count one request for ``key``; raise 429 once ``limit`` is exceeded.

        Commits immediately so the attempt counts even if the request fails.
        """
        if not self.settings.rate_limit_enabled:
            return

        window = self.settings.rate_limit_window_seconds
        now = time.time()
        window_start_epoch = math.floor(now / window) * window
        window_start = datetime.fromtimestamp(window_start_epoch, UTC)

        statement = (
            insert(RateLimitBucket)
            .values(key=key[:255], window_start=window_start, count=1)
            .on_conflict_do_update(
                index_elements=[RateLimitBucket.key, RateLimitBucket.window_start],
                set_={"count": RateLimitBucket.count + 1},
            )
            .returning(RateLimitBucket.count)
        )
        count = self.db.execute(statement).scalar_one()

        if random.random() < CLEANUP_PROBABILITY:
            self.db.execute(
                delete(RateLimitBucket).where(
                    RateLimitBucket.window_start < datetime.now(UTC) - RETENTION
                )
            )
        self.db.commit()

        if count > limit:
            retry_after = max(1, math.ceil(window_start_epoch + window - now))
            raise RateLimitExceededError(retry_after)

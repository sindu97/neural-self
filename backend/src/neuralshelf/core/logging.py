"""Centralized logging configuration.

Every log record carries a ``request_id``: the HTTP request's ID in the API
(see ``RequestContextMiddleware``) or ``job:<id>`` in the worker, so all lines
belonging to one request or job can be found together. ``LOG_FORMAT=json``
emits one JSON object per line for log aggregators.
"""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

from neuralshelf.core.config import get_settings
from neuralshelf.core.constants import DEFAULT_LOG_FORMAT

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Attributes every LogRecord has; anything else was passed via ``extra=``.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    """Attach the current request (or worker job) ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Set ``record.request_id``; never drops a record."""
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per log line, including any ``extra`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialise ``record`` as a JSON string."""
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        entry.update(
            {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        )
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    """Configure consistent application logging."""
    settings = get_settings()

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
    # httpx logs every Ollama call at INFO; keep it for warnings only.
    logging.getLogger("httpx").setLevel(logging.WARNING)

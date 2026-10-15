"""Stable application-wide constants."""

API_V1_PREFIX = "/api/v1"

HEALTH_LIVE_PATH = "/health/live"
HEALTH_READY_PATH = "/health/ready"

DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
)

REQUEST_ID_HEADER = "X-Request-ID"

# Must match the output size of the configured embedding model
# (nomic-embed-text produces 768-dimensional vectors). Changing it requires
# a migration of chunks.embedding and re-ingesting every document.
EMBEDDING_DIMENSIONS = 768

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

RETRIEVAL_DEFAULT_TOP_K = 5
RETRIEVAL_MAX_TOP_K = 20
RETRIEVAL_MAX_DOCUMENT_FILTERS = 50

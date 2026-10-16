"""Stable application-wide constants."""

API_V1_PREFIX = "/api/v1"

HEALTH_LIVE_PATH = "/health/live"
HEALTH_READY_PATH = "/health/ready"

DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
)

REQUEST_ID_HEADER = "X-Request-ID"

# Browsers send the refresh-token cookie automatically, so cookie-based
# refresh/revoke requests must also carry this custom header. Other sites
# can't add it to a cross-site request (CORS blocks it), which stops CSRF.
CSRF_HEADER = "X-NeuralShelf-CSRF"
# Native clients send "X-Auth-Mode: token" to receive the refresh token in
# the response body (for OS secure storage) instead of a cookie.
AUTH_MODE_HEADER = "X-Auth-Mode"

# Must match the output size of the configured embedding model
# (nomic-embed-text produces 768-dimensional vectors). Changing it requires
# a migration of chunks.embedding and re-ingesting every document.
EMBEDDING_DIMENSIONS = 768

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

RETRIEVAL_DEFAULT_TOP_K = 5
RETRIEVAL_MAX_TOP_K = 20
RETRIEVAL_MAX_DOCUMENT_FILTERS = 50

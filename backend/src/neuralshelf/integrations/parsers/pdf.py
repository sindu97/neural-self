"""PDF validation and text extraction with pypdf."""

import io
import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"


class PdfValidationError(Exception):
    """Raised when bytes are not a readable, unencrypted PDF with pages."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_pdf_bytes(data: bytes) -> int:
    """Check that ``data`` is a readable PDF and return its page count.

    ``reason`` on the raised error is one of: not_pdf, unreadable, encrypted, no_pages.
    """
    if not data.startswith(PDF_MAGIC):
        raise PdfValidationError("not_pdf")

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfValidationError("encrypted")
        page_count = len(reader.pages)
    except PdfValidationError:
        raise
    except (PdfReadError, ValueError, OSError) as exc:
        raise PdfValidationError("unreadable") from exc
    except Exception as exc:  # pypdf raises assorted errors on malformed input
        logger.warning("Unexpected PDF validation failure: %s", type(exc).__name__)
        raise PdfValidationError("unreadable") from exc

    if page_count == 0:
        raise PdfValidationError("no_pages")
    return page_count


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    """Return ``(page_number, text)`` for each page, numbered from 1."""
    reader = PdfReader(path)
    pages: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # one bad page should not fail the whole document
            logger.warning("Text extraction failed for page %d of %s.", page_number, path.name)
            text = ""
        pages.append((page_number, text))
    return pages

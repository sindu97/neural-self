import pytest

from neuralshelf.features.documents.exceptions import FileTooLargeError, InvalidFileError
from neuralshelf.features.documents.service import sanitize_filename, validate_upload
from neuralshelf.integrations.parsers.pdf import extract_pdf_pages
from tests.pdf_factory import make_pdf


def test_sanitize_filename_strips_paths_and_control_characters() -> None:
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("C:\\Users\\me\\report.pdf") == "report.pdf"
    assert sanitize_filename("bad\x00name\n.pdf") == "badname.pdf"
    assert sanitize_filename(None) == "document.pdf"


def test_sanitize_filename_truncates_but_keeps_extension() -> None:
    name = sanitize_filename("a" * 400 + ".pdf")

    assert len(name) == 255
    assert name.endswith(".pdf")


def test_validate_upload_accepts_real_pdf() -> None:
    validate_upload(filename="ok.pdf", content_type="application/pdf", data=make_pdf(["hi"]))


@pytest.mark.parametrize(
    ("filename", "content_type", "data"),
    [
        ("notes.txt", "text/plain", make_pdf(["hi"])),
        ("fake.pdf", "application/pdf", b"just some text"),
        ("broken.pdf", "application/pdf", b"%PDF-1.4\nthis is not a real pdf"),
        ("ok.pdf", "image/png", make_pdf(["hi"])),
        ("empty.pdf", "application/pdf", b""),
    ],
)
def test_validate_upload_rejects_invalid_files(
    filename: str, content_type: str, data: bytes
) -> None:
    with pytest.raises(InvalidFileError):
        validate_upload(filename=filename, content_type=content_type, data=data)


def test_validate_upload_rejects_oversized_files(monkeypatch: pytest.MonkeyPatch) -> None:
    from neuralshelf.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)

    with pytest.raises(FileTooLargeError):
        validate_upload(
            filename="big.pdf", content_type="application/pdf", data=b"%PDF-" + b"0" * 2**20
        )


def test_extract_pdf_pages_returns_numbered_page_text(tmp_path) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(["First page text", "Second page text"]))

    pages = extract_pdf_pages(path)

    assert [number for number, _ in pages] == [1, 2]
    assert "First page text" in pages[0][1]
    assert "Second page text" in pages[1][1]

"""Tests for PDF/DOCX export."""
from app.services.export import to_docx, to_pdf

SAMPLE = "Jane Doe\nBackend Engineer\n\nSUMMARY\nExperienced engineer.\n\nSKILLS\nPython, FastAPI"


def test_to_pdf_returns_valid_pdf_bytes():
    data = to_pdf(SAMPLE, title="Resume")
    assert isinstance(data, (bytes, bytearray))
    assert data[:4] == b"%PDF"  # PDF magic header
    assert len(data) > 500


def test_to_docx_returns_valid_docx_bytes():
    data = to_docx(SAMPLE, title="Resume")
    assert isinstance(data, bytes)
    # DOCX is a zip archive -> starts with the PK zip signature.
    assert data[:2] == b"PK"
    assert len(data) > 500


def test_export_handles_non_latin1_characters():
    # Should not raise even with characters outside latin-1 (e.g. em dash, emoji).
    tricky = "Résumé — leadership – delivered 5× results \U0001f680"
    assert to_pdf(tricky)[:4] == b"%PDF"
    assert to_docx(tricky)[:2] == b"PK"


def test_export_handles_empty_text():
    assert to_pdf("")[:4] == b"%PDF"
    assert to_docx("")[:2] == b"PK"

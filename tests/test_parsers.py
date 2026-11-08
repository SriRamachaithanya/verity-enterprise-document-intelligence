from pathlib import Path

import pymupdf
import pytest
from docx import Document

from src.parsers import get_parser_for_file
from src.parsers.base import DocumentParseError
from src.parsers.docx_parser import DOCXParser
from src.parsers.pdf_parser import PDFParser
from src.parsers.txt_parser import TXTParser


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a valid synthetic PDF document."""
    pdf_path = tmp_path / "synthetic_policy.pdf"
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Section 1.0: Enterprise Access Control Policy\n\n"
        "All engineers must use hardware FIDO2 tokens for multi-factor authentication.\n"
        "Passwords must be at least 16 characters in length and rotated yearly.",
    )
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "Section 2.0: Data Retention and Archival Standards\n\n"
        "Financial transaction records must be retained in immutable storage for 7 years.",
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """Generate a valid synthetic DOCX document."""
    docx_path = tmp_path / "synthetic_procedure.docx"
    doc = Document()
    doc.add_heading("Section 4.0: Cryptographic Key Management", level=1)
    doc.add_paragraph(
        "Production keys must be stored in Hardware Security Modules (HSM) or AWS KMS. "
        "Keys must be automatically rotated every 90 days."
    )
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Control ID"
    table.rows[0].cells[1].text = "Implementation"
    table.rows[1].cells[0].text = "KM-01"
    table.rows[1].cells[1].text = "AES-256 GCM Envelope Encryption"
    doc.save(str(docx_path))
    return docx_path


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    """Generate a valid synthetic plain text document."""
    txt_path = tmp_path / "synthetic_guidelines.txt"
    txt_path.write_text(
        "# Section 5.0: Incident Response Timelines\n\n"
        "Severity-1 security incidents must be escalated to the CISO within 15 minutes.\n"
        "Initial containment must be initiated within 1 hour.",
        encoding="utf-8",
    )
    return txt_path


def test_pdf_extraction(sample_pdf: Path):
    parser = PDFParser()
    extracted = parser.parse(sample_pdf)

    assert extracted.metadata.filename == "synthetic_policy.pdf"
    assert extracted.metadata.mime_type == "application/pdf"
    assert extracted.metadata.page_count == 2
    assert len(extracted.elements) >= 2
    assert "FIDO2" in extracted.full_text
    assert extracted.elements[0].page_number == 1
    assert "Section 1.0" in extracted.elements[0].section_heading


def test_docx_extraction(sample_docx: Path):
    parser = DOCXParser()
    extracted = parser.parse(sample_docx)

    assert extracted.metadata.filename == "synthetic_procedure.docx"
    assert extracted.metadata.page_count is None  # Page numbers not invented
    assert "AES-256 GCM" in extracted.full_text
    # Verify paragraph locator preservation
    locators = [e.locator for e in extracted.elements]
    assert any("Section" in loc and "Para" in loc for loc in locators)
    assert any("Table" in loc for loc in locators)


def test_txt_extraction(sample_txt: Path):
    parser = TXTParser()
    extracted = parser.parse(sample_txt)

    assert extracted.metadata.filename == "synthetic_guidelines.txt"
    assert "Severity-1" in extracted.full_text
    assert extracted.elements[0].section_heading == "Section 5.0: Incident Response Timelines"


def test_parser_factory_dispatch(sample_pdf: Path, sample_docx: Path, sample_txt: Path):
    assert isinstance(get_parser_for_file(sample_pdf), PDFParser)
    assert isinstance(get_parser_for_file(sample_docx), DOCXParser)
    assert isinstance(get_parser_for_file(sample_txt), TXTParser)

    with pytest.raises(DocumentParseError, match="Unsupported file format"):
        get_parser_for_file("malicious.exe")


def test_invalid_magic_bytes_rejection(tmp_path: Path):
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"This is not a real PDF file header")
    parser = PDFParser()

    with pytest.raises(DocumentParseError, match="Invalid PDF magic header"):
        parser.parse(fake_pdf)


def test_binary_in_txt_rejection(tmp_path: Path):
    fake_txt = tmp_path / "fake.txt"
    fake_txt.write_bytes(b"Hello world\x00\x01\x02binary bytes")
    parser = TXTParser()

    with pytest.raises(DocumentParseError, match="Binary content detected"):
        parser.parse(fake_txt)


def test_file_size_limit_rejection(tmp_path: Path, monkeypatch):
    large_txt = tmp_path / "large.txt"
    large_txt.write_text("dummy payload exceeding limit", encoding="utf-8")

    # Lower MAX_FILE_SIZE_BYTES artificially for unit testing
    from src.parsers import base

    monkeypatch.setattr(base, "MAX_FILE_SIZE_BYTES", 10)

    parser = TXTParser()
    with pytest.raises(DocumentParseError, match="exceeds limit"):
        parser.parse(large_txt)

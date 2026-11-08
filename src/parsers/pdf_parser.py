import logging
from pathlib import Path
from typing import ClassVar

import pymupdf

from src.parsers.base import BaseDocumentParser, DocumentParseError
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement

logger = logging.getLogger(__name__)

# Security page limit to prevent memory exhaustion from oversized PDF generation
MAX_PDF_PAGES = 1000


class PDFParser(BaseDocumentParser):
    """Passive PDF text extractor using PyMuPDF."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".pdf"}
    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = {"application/pdf"}

    def _validate_magic_bytes(self, path: Path) -> None:
        with open(path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                raise DocumentParseError(f"Invalid PDF magic header: {header!r}. Expected b'%PDF-'")

    def parse(self, file_path: Path | str) -> ExtractedDocument:
        path = self.validate_file(file_path)
        sha256 = self.calculate_sha256(path)
        file_size = path.stat().st_size

        elements: list[ParsedElement] = []
        full_text_parts: list[str] = []

        try:
            doc = pymupdf.open(str(path))
        except Exception as e:
            raise DocumentParseError(f"Failed to open PDF with PyMuPDF: {e}") from e

        try:
            page_count = len(doc)
            if page_count > MAX_PDF_PAGES:
                raise DocumentParseError(
                    f"PDF page count ({page_count}) exceeds maximum allowed limit of {MAX_PDF_PAGES} pages."
                )
            current_heading = "General"

            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                # Extract blocks to preserve layout structure
                # Each block: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type == 0 is text
                blocks = page.get_text("blocks")
                para_counter = 1

                for b in blocks:
                    if b[6] != 0:  # Skip image blocks
                        continue
                    text = b[4].strip()
                    if not text:
                        continue

                    # Heuristic for section headings (short line, capital letters, or numbering like 'Section 1.0')
                    lines = text.split("\n")
                    first_line = lines[0].strip()
                    if len(first_line) < 80 and (
                        first_line.startswith(("Section ", "Chapter ", "Article ", "Policy "))
                        or (first_line.isupper() and len(first_line) < 40)
                        or any(first_line.startswith(f"{i}.") for i in range(1, 20))
                    ):
                        current_heading = first_line

                    locator = f"Page {page_num}, Block {b[5]}"
                    elements.append(
                        ParsedElement(
                            text=text,
                            page_number=page_num,
                            section_heading=current_heading,
                            paragraph_index=para_counter,
                            locator=locator,
                        )
                    )
                    full_text_parts.append(text)
                    para_counter += 1

            metadata = DocumentMetadata(
                filename=path.name,
                file_hash=sha256,
                mime_type="application/pdf",
                file_size_bytes=file_size,
                page_count=page_count,
                extra={
                    "pdf_title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                },
            )

            return ExtractedDocument(
                metadata=metadata,
                elements=elements,
                full_text="\n\n".join(full_text_parts),
            )
        finally:
            doc.close()

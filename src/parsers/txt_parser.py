import logging
from pathlib import Path
from typing import ClassVar

from src.parsers.base import BaseDocumentParser, DocumentParseError
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement

logger = logging.getLogger(__name__)


class TXTParser(BaseDocumentParser):
    """Passive plain text and Markdown extractor."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".txt", ".md"}
    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = {"text/plain", "text/markdown"}

    def _validate_magic_bytes(self, path: Path) -> None:
        # Check first 512 bytes for null-bytes to reject binary files renamed as .txt
        with open(path, "rb") as f:
            chunk = f.read(512)
            if b"\x00" in chunk:
                raise DocumentParseError(
                    f"Binary content detected in text file: {path}. Null bytes present."
                )

    def parse(self, file_path: Path | str) -> ExtractedDocument:
        path = self.validate_file(file_path)
        sha256 = self.calculate_sha256(path)
        file_size = path.stat().st_size

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                raise DocumentParseError(f"Could not decode text file {path}: {e}") from e

        elements: list[ParsedElement] = []
        full_text_parts: list[str] = []
        current_heading = "General"

        # Split by double newline to preserve paragraph semantics
        raw_paras = content.split("\n\n")
        para_idx = 1

        for raw_p in raw_paras:
            text = raw_p.strip()
            if not text:
                continue

            # Check for Markdown heading or section marker
            first_line = text.split("\n")[0].strip()
            if first_line.startswith(("# ", "## ", "### ")):
                current_heading = first_line.lstrip("#").strip()
            elif first_line.isupper() and len(first_line) < 50:
                current_heading = first_line

            locator = f"Section '{current_heading}', Para {para_idx}"
            elements.append(
                ParsedElement(
                    text=text,
                    page_number=None,
                    section_heading=current_heading,
                    paragraph_index=para_idx,
                    locator=locator,
                )
            )
            full_text_parts.append(text)
            para_idx += 1

        metadata = DocumentMetadata(
            filename=path.name,
            file_hash=sha256,
            mime_type="text/plain",
            file_size_bytes=file_size,
            page_count=None,
            extra={"total_paragraphs": len(elements)},
        )

        return ExtractedDocument(
            metadata=metadata,
            elements=elements,
            full_text="\n\n".join(full_text_parts),
        )

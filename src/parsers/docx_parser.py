import logging
import zipfile
from pathlib import Path
from typing import ClassVar

from docx import Document

from src.parsers.base import BaseDocumentParser, DocumentParseError
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement

logger = logging.getLogger(__name__)

# Security boundaries to defend against ZIP bomb and resource exhaustion attacks
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_COMPRESSION_RATIO = 100.0  # Uncompressed to compressed size ratio threshold
MAX_ZIP_ENTRIES = 2000


class DOCXParser(BaseDocumentParser):
    """Passive DOCX text extractor using python-docx with structural paragraph locators."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".docx"}
    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    def _validate_magic_bytes(self, path: Path) -> None:
        with open(path, "rb") as f:
            header = f.read(4)
            if header != b"PK\x03\x04":
                raise DocumentParseError(
                    f"Invalid DOCX magic header: {header!r}. Expected zip header b'PK\\x03\\x04'"
                )

        # Inspect ZIP container for decompression bomb attributes
        try:
            with zipfile.ZipFile(path, "r") as zf:
                infos = zf.infolist()
                if len(infos) > MAX_ZIP_ENTRIES:
                    raise DocumentParseError(
                        f"DOCX archive contains excessive entries ({len(infos)} > {MAX_ZIP_ENTRIES}). Rejected as potential ZIP bomb."
                    )
                total_uncompressed = sum(info.file_size for info in infos)
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    raise DocumentParseError(
                        f"DOCX uncompressed size ({total_uncompressed} bytes) exceeds {MAX_UNCOMPRESSED_BYTES // (1024*1024)} MB limit."
                    )
                file_size = path.stat().st_size
                if file_size > 0:
                    ratio = total_uncompressed / file_size
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise DocumentParseError(
                            f"DOCX compression ratio {ratio:.1f}x exceeds safe limit of {MAX_COMPRESSION_RATIO}x. Rejected as potential ZIP bomb."
                        )
        except zipfile.BadZipFile as bz:
            raise DocumentParseError(f"Corrupted or invalid DOCX archive: {bz}") from bz

    def parse(self, file_path: Path | str) -> ExtractedDocument:
        path = self.validate_file(file_path)
        sha256 = self.calculate_sha256(path)
        file_size = path.stat().st_size

        try:
            doc = Document(str(path))
        except Exception as e:
            raise DocumentParseError(f"Failed to open DOCX document: {e}") from e

        elements: list[ParsedElement] = []
        full_text_parts: list[str] = []
        current_heading = "General"
        para_index = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading" in style_name or "title" in style_name:
                current_heading = text

            locator = f"Section '{current_heading}', Para {para_index}"
            elements.append(
                ParsedElement(
                    text=text,
                    page_number=None,  # Do not invent page numbers for DOCX
                    section_heading=current_heading,
                    paragraph_index=para_index,
                    locator=locator,
                )
            )
            full_text_parts.append(text)
            para_index += 1

        # Also extract structured table rows
        table_index = 1
        for table in doc.tables:
            for row_idx, row in enumerate(table.rows):
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if not row_cells:
                    continue
                # Remove duplicate adjacent cells from merged cells
                deduped = []
                for c in row_cells:
                    if not deduped or deduped[-1] != c:
                        deduped.append(c)
                row_text = " | ".join(deduped)
                locator = f"Table {table_index}, Row {row_idx + 1}"
                elements.append(
                    ParsedElement(
                        text=row_text,
                        page_number=None,
                        section_heading=current_heading,
                        paragraph_index=para_index,
                        locator=locator,
                    )
                )
                full_text_parts.append(row_text)
                para_index += 1
            table_index += 1

        metadata = DocumentMetadata(
            filename=path.name,
            file_hash=sha256,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size_bytes=file_size,
            page_count=None,  # Not applicable to reflowable DOCX
            extra={"total_paragraphs": para_index - 1, "total_tables": table_index - 1},
        )

        return ExtractedDocument(
            metadata=metadata,
            elements=elements,
            full_text="\n\n".join(full_text_parts),
        )

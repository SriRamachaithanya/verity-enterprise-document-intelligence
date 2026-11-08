from pathlib import Path

from src.parsers.base import BaseDocumentParser, DocumentParseError
from src.parsers.docx_parser import DOCXParser
from src.parsers.pdf_parser import PDFParser
from src.parsers.txt_parser import TXTParser


def get_parser_for_file(file_path: Path | str) -> BaseDocumentParser:
    """Return the appropriate parser instance based on file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return PDFParser()
    elif ext == ".docx":
        return DOCXParser()
    elif ext in {".txt", ".md"}:
        return TXTParser()
    else:
        raise DocumentParseError(
            f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt, .md"
        )


__all__ = [
    "BaseDocumentParser",
    "DOCXParser",
    "DocumentParseError",
    "PDFParser",
    "TXTParser",
    "get_parser_for_file",
]

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from src.schemas.document import ExtractedDocument

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class DocumentParseError(Exception):
    """Raised when document extraction fails or validation fails."""


class BaseDocumentParser(ABC):
    """Abstract base class for passive document extractors with strict validation."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = set()
    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = set()

    def validate_file(self, file_path: Path | str) -> Path:
        """Validate file existence, size, extension and magic bytes."""
        path = Path(file_path)
        if not path.is_file():
            raise DocumentParseError(f"File not found or is not a regular file: {path}")

        file_size = path.stat().st_size
        if file_size == 0:
            raise DocumentParseError(f"File is empty: {path}")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise DocumentParseError(
                f"File size {file_size / (1024 * 1024):.2f} MB exceeds limit of 25 MB: {path}"
            )

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise DocumentParseError(
                f"Unsupported extension '{ext}'. Expected one of {self.SUPPORTED_EXTENSIONS}"
            )

        self._validate_magic_bytes(path)
        return path

    @abstractmethod
    def _validate_magic_bytes(self, path: Path) -> None:
        """Verify binary header magic bytes."""

    @abstractmethod
    def parse(self, file_path: Path | str) -> ExtractedDocument:
        """Extract structured text elements, sections, and metadata."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Compute SHA-256 cryptographic digest using chunked reading."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

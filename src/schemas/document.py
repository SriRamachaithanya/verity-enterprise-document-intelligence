from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class DocumentMetadata:
    filename: str
    file_hash: str  # SHA-256
    mime_type: str
    file_size_bytes: int
    page_count: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedElement:
    text: str
    page_number: int | None = None
    section_heading: str = "General"
    paragraph_index: int | None = None
    locator: str = ""  # e.g., "Page 3" or "Section 4.1, Para 2"


@dataclass
class ExtractedDocument:
    metadata: DocumentMetadata
    elements: list[ParsedElement]
    full_text: str = ""


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None = None
    section_heading: str = "General"
    locator: str = ""
    faiss_index_id: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    section_heading: str
    locator: str
    content: str
    rrf_score: float
    dense_rank: int | None = None
    lexical_rank: int | None = None

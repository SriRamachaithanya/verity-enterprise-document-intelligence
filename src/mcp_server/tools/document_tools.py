import json
import logging
from typing import Any

from src.mcp_server.dependencies import get_db, get_hybrid_search
from src.schemas.mcp import (
    DocumentMetadataResponse,
    DocumentSummaryItem,
    ListDocumentsResponse,
    SearchDocumentsResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


def list_documents(limit: int = 20, offset: int = 0) -> ListDocumentsResponse:
    """
    List all ingested documents in the repository with pagination.

    Args:
        limit: Maximum number of documents to return (1-100). Default is 20.
        offset: Number of documents to skip for pagination (>= 0). Default is 0.

    Returns:
        ListDocumentsResponse with total_count and list of document summaries.
    """
    if limit < 1 or limit > 100:
        raise ValueError("Argument 'limit' must be between 1 and 100.")
    if offset < 0:
        raise ValueError("Argument 'offset' must be non-negative.")

    db = get_db()
    total_count = db.count_documents()
    docs = db.list_documents(limit=limit, offset=offset)

    items = [
        DocumentSummaryItem(
            id=d["id"],
            filename=d["filename"],
            file_hash=d["file_hash"],
            mime_type=d["mime_type"],
            file_size_bytes=d["file_size_bytes"],
            page_count=d.get("page_count"),
            created_at=str(d["created_at"]),
        )
        for d in docs
    ]
    return ListDocumentsResponse(total_count=total_count, documents=items)


def search_documents(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> SearchDocumentsResponse:
    """
    Execute hybrid search (FAISS dense + SQLite FTS5 BM25 with Reciprocal Rank Fusion).

    Args:
        query: Search query text (minimum 2 characters).
        top_k: Maximum number of results to return (1-50). Default is 5.
        document_id: Optional document ID to restrict search scope.

    Returns:
        SearchDocumentsResponse containing ranked chunks, scores, and exact verbatim text.
    """
    cleaned_query = query.strip()
    if len(cleaned_query) < 2:
        raise ValueError("Search query must contain at least 2 non-whitespace characters.")
    if top_k < 1 or top_k > 50:
        raise ValueError("Argument 'top_k' must be between 1 and 50.")

    db = get_db()
    if document_id:
        doc = db.get_document_by_id(document_id)
        if not doc:
            raise ValueError(f"Document ID '{document_id}' not found.")

    hybrid_engine = get_hybrid_search()
    raw_results = hybrid_engine.search(
        query=cleaned_query,
        top_k=top_k,
        document_id=document_id,
    )

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_name=r.document_name,
            page_number=r.page_number,
            section_heading=r.section_heading,
            locator=r.locator,
            content=r.content,
            rrf_score=r.rrf_score,
            dense_rank=r.dense_rank,
            lexical_rank=r.lexical_rank,
        )
        for r in raw_results
    ]

    return SearchDocumentsResponse(
        query=cleaned_query,
        total_results=len(items),
        results=items,
    )


def get_document_metadata(document_id: str) -> DocumentMetadataResponse:
    """
    Retrieve structural, cryptographic, and categorical metadata for a specific document.

    Args:
        document_id: Unique document identifier.

    Returns:
        DocumentMetadataResponse with SHA-256 hash, section breakdown, and total chunks.
    """
    clean_id = document_id.strip()
    if not clean_id:
        raise ValueError("Argument 'document_id' cannot be empty.")

    db = get_db()
    doc = db.get_document_by_id(clean_id)
    if not doc:
        raise ValueError(f"Document ID '{clean_id}' not found.")

    chunks = db.get_chunks_for_document(clean_id)
    seen_sections: set[str] = set()
    sections: list[str] = []
    for c in chunks:
        sec = c.get("section_heading", "General")
        if sec and sec not in seen_sections:
            seen_sections.add(sec)
            sections.append(sec)

    metadata_dict: dict[str, Any] = {}
    if doc.get("metadata_json"):
        try:
            metadata_dict = json.loads(doc["metadata_json"])
        except Exception:  # noqa: BLE001
            metadata_dict = {}

    return DocumentMetadataResponse(
        id=doc["id"],
        filename=doc["filename"],
        file_hash=doc["file_hash"],
        mime_type=doc["mime_type"],
        file_size_bytes=doc["file_size_bytes"],
        page_count=doc.get("page_count"),
        total_chunks=len(chunks),
        sections=sections,
        created_at=str(doc["created_at"]),
        metadata_json=metadata_dict,
    )


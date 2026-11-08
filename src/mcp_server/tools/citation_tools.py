import logging
from typing import Any

from src.mcp_server.dependencies import get_db
from src.schemas.mcp import CitationResponse

logger = logging.getLogger(__name__)


def get_citation(
    chunk_id: str,
    include_surrounding_context: bool = False,
) -> CitationResponse:
    """
    Retrieve exact verbatim citation, document locator, and cryptographic integrity proof for a chunk.

    Args:
        chunk_id: Unique chunk identifier.
        include_surrounding_context: Whether to return preceding and succeeding chunk text.

    Returns:
        CitationResponse containing verbatim chunk text, section heading, locator, and SHA-256 verification.
    """
    clean_id = chunk_id.strip()
    if not clean_id:
        raise ValueError("Argument 'chunk_id' cannot be empty.")

    db = get_db()
    chunk = db.get_chunk_by_id(clean_id)
    if not chunk:
        raise ValueError(f"Chunk ID '{clean_id}' not found.")

    prev_chunk: dict[str, Any] | None = None
    next_chunk: dict[str, Any] | None = None

    if include_surrounding_context:
        all_chunks = db.get_chunks_for_document(chunk["document_id"])
        target_index = chunk["chunk_index"]
        for c in all_chunks:
            if c["chunk_index"] == target_index - 1:
                prev_chunk = c
            elif c["chunk_index"] == target_index + 1:
                next_chunk = c

    return CitationResponse.from_chunk(
        chunk=chunk,
        prev_chunk=prev_chunk,
        next_chunk=next_chunk,
    )


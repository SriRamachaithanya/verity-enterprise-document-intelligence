import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from src.api.dependencies import get_db, get_ingestion_pipeline
from src.api.schemas.documents import (
    DocumentDetailResponse,
    DocumentItemResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from src.api.security.auth import AuthenticatedUser, require_admin, require_user
from src.api.security.file_security import run_malware_scan, validate_uploaded_file
from src.indexing.ingestion_pipeline import IngestionPipeline
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Document Intelligence"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Ingest Document",
    description=(
        "Securely upload, validate, parse, chunk, embed, and index enterprise documents. "
        "Enforces strict MIME validation, magic byte checks, malware inspection, and SHA-256 deduplication."
    ),
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document binary file (PDF, DOCX, TXT)")],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    ingestion: Annotated[IngestionPipeline, Depends(get_ingestion_pipeline)],
) -> DocumentUploadResponse:
    # 1. Validate file extension, size, and magic bytes
    sanitized_filename, content_bytes = await validate_uploaded_file(file)

    # 2. Stage into a secure isolated temporary file for inspection and parsing
    suffix = Path(sanitized_filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content_bytes)
        temp_path = Path(temp_file.name)

    try:
        # 3. Malware inspection and quarantine analysis
        scan_result = run_malware_scan(temp_path, content_sample=content_bytes)

        # 4. Ingest through the verified pipeline (extracts, chunks, embeds, indexes)
        ingest_result = ingestion.ingest_document(
            source_path=temp_path,
            custom_metadata={"uploaded_by": current_user.user_id},
            original_filename=sanitized_filename,
        )

        doc_record = ingest_result["document"]
        return DocumentUploadResponse(
            document_id=doc_record["id"],
            filename=doc_record["filename"],
            file_hash=doc_record["file_hash"],
            file_size_bytes=doc_record["file_size_bytes"],
            mime_type=doc_record["mime_type"],
            chunks_count=ingest_result["chunks_count"],
            status=ingest_result["status"],
            message=ingest_result["message"],
            malware_scan=scan_result,
        )

    finally:
        # Ensure temporary file is safely unlinked
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not delete temporary staging file %s: %s", temp_path, e)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Ingested Documents",
    description="Retrieve paginated list of ingested documents in the repository.",
)
def list_documents(
    limit: Annotated[int, Query(ge=1, le=100, description="Max documents to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)] = None,
    db: Annotated[DatabaseManager, Depends(get_db)] = None,
) -> DocumentListResponse:
    docs = db.list_documents(limit=limit, offset=offset)
    total_count = db.count_documents()

    items = [
        DocumentItemResponse(
            id=d["id"],
            filename=d["filename"],
            file_hash=d["file_hash"],
            mime_type=d["mime_type"],
            file_size_bytes=d["file_size_bytes"],
            page_count=d.get("page_count"),
            created_at=d["created_at"],
        )
        for d in docs
    ]

    return DocumentListResponse(
        total_count=total_count,
        documents=items,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get Document Details",
    description="Retrieve detailed metadata and section hierarchy for a specific document.",
)
def get_document_by_id(
    document_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[DatabaseManager, Depends(get_db)],
) -> DocumentDetailResponse:
    clean_id = document_id.strip()
    doc = db.get_document_by_id(clean_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{clean_id}' not found.",
        )

    chunks = db.get_chunks_for_document(clean_id)
    sections = sorted(
        {c["section_heading"] for c in chunks if c.get("section_heading")}
    )

    return DocumentDetailResponse(
        id=doc["id"],
        filename=doc["filename"],
        file_hash=doc["file_hash"],
        mime_type=doc["mime_type"],
        file_size_bytes=doc["file_size_bytes"],
        page_count=doc.get("page_count"),
        total_chunks=len(chunks),
        sections=sections,
        created_at=doc["created_at"],
        metadata_json=doc.get("metadata", {}),
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Delete a document, cascade-delete its chunks and FTS entries, and re-index the FAISS vector space.",
)
def delete_document_by_id(
    document_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    ingestion: Annotated[IngestionPipeline, Depends(get_ingestion_pipeline)],
) -> dict[str, str]:
    clean_id = document_id.strip()
    success = ingestion.delete_document(clean_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{clean_id}' not found.",
        )

    return {
        "status": "deleted",
        "document_id": clean_id,
        "message": "Document, chunks, and vector index entries successfully removed.",
    }

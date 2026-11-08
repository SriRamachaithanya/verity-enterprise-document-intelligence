from typing import Any

from pydantic import BaseModel, Field


class MalwareScanResult(BaseModel):
    scanned: bool = Field(description="Whether a malware engine scan was executed")
    engine: str = Field(description="Scanner identifier (e.g. 'Windows Defender', 'ClamAV', or 'Static Signature Engine')")
    is_clean: bool = Field(description="True if no malicious signatures were detected")
    details: str = Field(description="Diagnostic details or offline disclaimer")


class DocumentUploadResponse(BaseModel):
    document_id: str = Field(description="Unique document identifier")
    filename: str = Field(description="Original sanitized filename")
    file_hash: str = Field(description="Cryptographic SHA-256 digest")
    file_size_bytes: int = Field(description="File size in bytes")
    mime_type: str = Field(description="Detected MIME media type")
    chunks_count: int = Field(description="Number of chunks extracted and indexed")
    status: str = Field(description="Ingestion status ('ingested' or 'already_exists')")
    message: str = Field(description="Informational status message")
    malware_scan: MalwareScanResult = Field(description="Malware inspection results")


class DocumentItemResponse(BaseModel):
    id: str = Field(description="Document ID")
    filename: str = Field(description="Sanitized filename")
    file_hash: str = Field(description="SHA-256 hash")
    mime_type: str = Field(description="MIME type")
    file_size_bytes: int = Field(description="Size in bytes")
    page_count: int | None = Field(default=None, description="Page count if known")
    created_at: str = Field(description="Ingestion timestamp")


class DocumentListResponse(BaseModel):
    total_count: int = Field(description="Total document count")
    documents: list[DocumentItemResponse] = Field(description="List of document records")
    limit: int = Field(description="Pagination limit applied")
    offset: int = Field(description="Pagination offset applied")


class DocumentDetailResponse(BaseModel):
    id: str = Field(description="Document ID")
    filename: str = Field(description="Sanitized filename")
    file_hash: str = Field(description="SHA-256 hash")
    mime_type: str = Field(description="MIME type")
    file_size_bytes: int = Field(description="Size in bytes")
    page_count: int | None = Field(default=None, description="Page count")
    total_chunks: int = Field(description="Total chunks indexed for this document")
    sections: list[str] = Field(description="Distinct section headings identified")
    created_at: str = Field(description="Ingestion timestamp")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")

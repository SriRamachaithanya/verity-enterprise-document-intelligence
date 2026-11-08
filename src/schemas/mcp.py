import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Tool 1: list_documents
# -----------------------------------------------------------------------------

class DocumentSummaryItem(BaseModel):
    id: str = Field(description="Unique document ID")
    filename: str = Field(description="Original filename")
    file_hash: str = Field(description="Cryptographic SHA-256 hash of the document")
    mime_type: str = Field(description="MIME media type")
    file_size_bytes: int = Field(description="File size in bytes")
    page_count: int | None = Field(default=None, description="Page count if known")
    created_at: str = Field(description="Ingestion timestamp")


class ListDocumentsResponse(BaseModel):
    total_count: int = Field(description="Total count of documents matching pagination")
    documents: list[DocumentSummaryItem] = Field(description="List of document records")


# -----------------------------------------------------------------------------
# Tool 2: search_documents
# -----------------------------------------------------------------------------

class SearchResultItem(BaseModel):
    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document identifier")
    document_name: str = Field(description="Original parent document filename")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    section_heading: str = Field(default="General", description="Section heading context")
    locator: str = Field(default="", description="Structural paragraph/section locator")
    content: str = Field(description="Verbatim text content of the chunk")
    rrf_score: float = Field(description="Normalized Reciprocal Rank Fusion score")
    dense_rank: int | None = Field(default=None, description="Dense FAISS ranking")
    lexical_rank: int | None = Field(default=None, description="Lexical FTS5 BM25 ranking")


class SearchDocumentsResponse(BaseModel):
    query: str = Field(description="Executed search query")
    total_results: int = Field(description="Total chunks returned")
    results: list[SearchResultItem] = Field(description="Ranked candidate chunks")


# -----------------------------------------------------------------------------
# Tool 3: get_document_metadata
# -----------------------------------------------------------------------------

class DocumentMetadataResponse(BaseModel):
    id: str = Field(description="Unique document ID")
    filename: str = Field(description="Original filename")
    file_hash: str = Field(description="Cryptographic SHA-256 hash")
    mime_type: str = Field(description="MIME type")
    file_size_bytes: int = Field(description="File size in bytes")
    page_count: int | None = Field(default=None, description="Page count")
    total_chunks: int = Field(description="Total indexed chunks for this document")
    sections: list[str] = Field(description="Distinct section headings identified in document")
    created_at: str = Field(description="Ingestion timestamp")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Parsed extra metadata")


# -----------------------------------------------------------------------------
# Tool 4: get_citation
# -----------------------------------------------------------------------------

class CitationResponse(BaseModel):
    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document ID")
    document_name: str = Field(description="Parent document filename")
    page_number: int | None = Field(default=None, description="Page number if known")
    section_heading: str = Field(default="General", description="Section heading context")
    locator: str = Field(default="", description="Structural locator (e.g. 'Page 3', '¶4')")
    exact_text: str = Field(description="Verbatim chunk text, un-paraphrased")
    sha256_verification: str = Field(description="SHA-256 hash verifying text integrity")
    previous_context: str | None = Field(default=None, description="Preceding chunk text")
    next_context: str | None = Field(default=None, description="Subsequent chunk text")

    @classmethod
    def from_chunk(
        cls,
        chunk: dict[str, Any],
        prev_chunk: dict[str, Any] | None = None,
        next_chunk: dict[str, Any] | None = None,
    ) -> "CitationResponse":
        text = chunk["content"]
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(
            chunk_id=chunk["id"],
            document_id=chunk["document_id"],
            document_name=chunk.get("document_name", "Unknown"),
            page_number=chunk.get("page_number"),
            section_heading=chunk.get("section_heading", "General"),
            locator=chunk.get("locator", ""),
            exact_text=text,
            sha256_verification=text_hash,
            previous_context=prev_chunk["content"] if prev_chunk else None,
            next_context=next_chunk["content"] if next_chunk else None,
        )


# -----------------------------------------------------------------------------
# Tool 5: evaluate_compliance
# -----------------------------------------------------------------------------

class ComplianceEvidence(BaseModel):
    chunk_id: str = Field(description="Evidence chunk ID")
    document_id: str = Field(description="Evidence document ID")
    document_name: str = Field(description="Evidence document filename")
    page_number: int | None = Field(default=None, description="Page number")
    section_heading: str = Field(default="General", description="Section heading")
    locator: str = Field(default="", description="Locator coordinate")
    quote: str = Field(description="Verbatim excerpt from evidence chunk")


class ComplianceFinding(BaseModel):
    requirement_code: str = Field(description="Requirement identifier (e.g. 'CC6.1')")
    title: str = Field(description="Requirement title")
    category: str = Field(description="Domain category")
    status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"] = Field(
        description="Assessed coverage status"
    )
    confidence_score: float = Field(description="Confidence rating (0.0 to 1.0)")
    evidence: ComplianceEvidence | None = Field(
        default=None, description="Supporting evidence chunk"
    )
    gap: str | None = Field(default=None, description="Identified compliance deficiency")
    recommendation: str | None = Field(default=None, description="Remediation guidance")
    human_review_required: bool = Field(
        default=False, description="Flag indicating human auditor review is required"
    )
    assurance_level: str = Field(
        default="Operating Evidence",
        description="Assurance tier: 'Policy Documentation', 'Implementation Evidence', or 'Operating Evidence'",
    )


class CoverageSummary(BaseModel):
    covered: int = Field(description="Count of fully covered requirements")
    partially_covered: int = Field(description="Count of partially covered requirements")
    missing: int = Field(description="Count of missing requirements")
    total: int = Field(description="Total assessed requirements")
    compliance_percentage: float = Field(description="Percentage covered (0-100%)")


class ComplianceEvaluationResponse(BaseModel):
    framework_id: str = Field(description="Evaluated framework ID")
    framework_name: str = Field(description="Evaluated framework name")
    total_requirements: int = Field(description="Total requirements in scope")
    coverage_summary: CoverageSummary = Field(description="Aggregate coverage numbers")
    findings: list[ComplianceFinding] = Field(description="Individual requirement findings")


# -----------------------------------------------------------------------------
# Tool 6: gap_analysis
# -----------------------------------------------------------------------------

class GapItem(BaseModel):
    priority_rank: int = Field(description="Remediation priority rank (1 = highest)")
    requirement_code: str = Field(description="Requirement code")
    title: str = Field(description="Requirement title")
    category: str = Field(description="Domain category")
    current_status: Literal["PARTIALLY_COVERED", "MISSING"] = Field(
        description="Current non-compliant or partially compliant status"
    )
    severity: str = Field(description="Severity tier: 'Critical', 'High', 'Medium', 'Low'")
    identified_gap: str = Field(description="Detailed explanation of the deficiency")
    remediation_recommendation: str = Field(description="Specific actionable remediation guidance")
    human_review_required: bool = Field(description="Whether human auditor review is mandated")
    estimated_effort_days: int = Field(description="Estimated remediation effort in engineering days")


class GapAnalysisResponse(BaseModel):
    framework_id: str = Field(description="Framework ID")
    framework_name: str = Field(description="Framework name")
    total_gaps: int = Field(description="Total identified gaps (PARTIALLY_COVERED + MISSING)")
    covered_count: int = Field(description="Covered requirements count")
    partially_covered_count: int = Field(description="Partially covered requirements count")
    missing_count: int = Field(description="Missing requirements count")
    human_review_count: int = Field(description="Count of requirements flagged for human review")
    remediation_roadmap: list[GapItem] = Field(description="Prioritized gap remediation entries")


# -----------------------------------------------------------------------------
# Tool 7: get_related_knowledge
# -----------------------------------------------------------------------------

class KnowledgeNodeItem(BaseModel):
    id: str = Field(description="Node ID")
    slug: str = Field(description="URL-friendly note slug")
    title: str = Field(description="Note title")
    node_type: str = Field(description="Type: 'document', 'requirement', 'control', 'evidence'")
    content_markdown: str = Field(description="Verbatim Markdown body")


class KnowledgeLinkItem(BaseModel):
    target_slug: str = Field(description="Target node slug")
    target_title: str | None = Field(default=None, description="Target node title if resolved")
    link_text: str | None = Field(default=None, description="Visual display link text")
    context_snippet: str | None = Field(default=None, description="Surrounding sentence context")


class BacklinkItem(BaseModel):
    source_slug: str = Field(description="Source node slug linking to target")
    source_title: str = Field(description="Source node title")
    source_type: str = Field(description="Source node type")
    context_snippet: str | None = Field(default=None, description="Context where link occurred")


class RelatedKnowledgeResponse(BaseModel):
    root_node: KnowledgeNodeItem = Field(description="The requested core knowledge note")
    outgoing_links: list[KnowledgeLinkItem] = Field(description="Forward wiki links from this note")
    backlinks: list[BacklinkItem] = Field(description="Inbound links citing this note")
    related_requirements: list[str] = Field(
        description="Extracted requirement codes referenced in note"
    )
    depth: int = Field(description="Graph traversal depth used")

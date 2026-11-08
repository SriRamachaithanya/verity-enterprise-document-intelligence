from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class UserIntent(str, Enum):
    DOCUMENT_DISCOVERY = "document_discovery"
    DOCUMENT_SEARCH = "document_search"
    CITATION_VERIFICATION = "citation_verification"
    COMPLIANCE_EVALUATION = "compliance_evaluation"
    COMPLIANCE_GAP_ANALYSIS = "compliance_gap_analysis"
    KNOWLEDGE_EXPLORATION = "knowledge_exploration"
    DOCUMENT_QA = "document_qa"


class IntentResult(BaseModel):
    intent: UserIntent = Field(description="Classified user task intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence score")
    extracted_entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted parameters (framework, req_code, doc_id, etc.)"
    )
    reasoning: str = Field(description="Explanation for classification")


class ToolCallPlan(BaseModel):
    tool_name: str = Field(description="Name of approved MCP tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Validated arguments dictionary")
    rationale: str = Field(description="Why this tool call is needed")
    priority: int = Field(default=1, description="Execution priority (1 = highest)")


class ExecutionPlan(BaseModel):
    intent: UserIntent = Field(description="Intent governing this plan")
    tool_calls: list[ToolCallPlan] = Field(default_factory=list, description="Planned tool calls")
    max_iterations: int = Field(default=2, description="Maximum planning refinement rounds")
    current_iteration: int = Field(default=1, description="Current iteration number")
    is_complete: bool = Field(default=False, description="Whether plan execution has concluded")


class ToolExecutionResult(BaseModel):
    tool_name: str = Field(description="Executed tool name")
    arguments: dict[str, Any] = Field(description="Arguments sent to tool")
    raw_text: str = Field(description="Raw text content returned from MCP tool")
    parsed_data: dict[str, Any] | list[Any] | None = Field(
        default=None, description="Parsed JSON payload"
    )
    is_error: bool = Field(default=False, description="Whether execution resulted in an error")
    error_message: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int = Field(default=0, description="Latency in milliseconds")


class ValidatedCitation(BaseModel):
    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document identifier")
    document_name: str = Field(description="Original document filename")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    locator: str = Field(default="", description="Structural coordinate (e.g. Page 1, ¶3)")
    section_heading: str = Field(default="General", description="Section heading")
    exact_text: str = Field(description="Verbatim excerpt")
    sha256_hash: str = Field(description="SHA-256 integrity hash")
    is_valid: bool = Field(default=True, description="Whether cryptographic check passed")
    validation_notes: str = Field(default="Verified against ground truth store")

    @property
    def verified(self) -> bool:
        """Cross-layer property alias matching CitationItem.verified and frontend expectations."""
        return self.is_valid

    @property
    def exact_quote(self) -> str:
        """Cross-layer property alias matching CitationItem.exact_quote and frontend expectations."""
        return self.exact_text


class AgentResponse(BaseModel):
    session_id: str = Field(description="Unique session identifier")
    user_query: str = Field(description="Original user query")
    intent: UserIntent = Field(description="Resolved user intent")
    answer: str = Field(description="Grounded synthesized response in Markdown")
    citations: list[ValidatedCitation] = Field(
        default_factory=list, description="Verified citations supporting the answer"
    )
    compliance_status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING", "NOT_APPLICABLE"] | None = Field(
        default=None, description="Aggregate compliance outcome if query was an audit"
    )
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence rating")
    human_review_required: bool = Field(
        default=False, description="Flag indicating human compliance reviewer sign-off needed"
    )
    tools_executed: list[str] = Field(
        default_factory=list, description="Chronological list of MCP tools executed"
    )
    execution_time_ms: int = Field(default=0, description="End-to-end turn latency in ms")
    fallback_mode_used: bool = Field(
        default=False, description="True if answer was synthesized deterministically without LLM"
    )

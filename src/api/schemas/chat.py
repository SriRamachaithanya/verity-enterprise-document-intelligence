from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000, description="User question or audit command")
    session_id: str | None = Field(default=None, description="Optional existing session tracking ID")


class CitationItem(BaseModel):
    chunk_id: str = Field(description="Referenced chunk identifier")
    document_name: str = Field(description="Parent document filename")
    page_number: int | None = Field(default=None, description="Page number if known")
    section_heading: str = Field(default="General", description="Section context")
    locator: str = Field(default="", description="Structural paragraph locator")
    exact_quote: str = Field(description="Verbatim text quote from source chunk")
    verified: bool = Field(default=True, description="True if verified against database content")


class ChatResponse(BaseModel):
    session_id: str = Field(description="Interaction session ID")
    query: str = Field(description="Input user query")
    intent: str = Field(description="Classified user intent")
    answer: str = Field(description="Synthesized, evidence-grounded answer")
    citations: list[CitationItem] = Field(description="Verifiable source citations")
    compliance_status: str | None = Field(default=None, description="Compliance status if applicable")
    confidence_score: float = Field(description="Heuristic confidence rating (0.0 to 1.0)")
    human_review_required: bool = Field(default=False, description="Whether human review is mandated")
    execution_time_ms: int = Field(description="End-to-end turn execution latency in ms")
    tools_executed: list[str] = Field(default_factory=list, description="List of MCP tools executed")


class StreamEvent(BaseModel):
    event: str = Field(description="SSE event type ('status', 'token', 'citation', 'done', 'error')")
    data: dict[str, Any] = Field(description="Event data payload")

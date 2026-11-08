from pydantic import BaseModel, Field


class ComplianceEvaluateRequest(BaseModel):
    framework_id: str = Field(min_length=1, description="Framework ID or name (e.g. 'SOC2', 'ISO27001')")
    requirement_id: str | None = Field(default=None, description="Optional specific requirement ID/code")
    evidence_document_ids: list[str] | None = Field(
        default=None, description="Optional list of document IDs to restrict evidence search"
    )


class GapAnalysisRequest(BaseModel):
    framework_id: str = Field(min_length=1, description="Framework identifier")
    severity_filter: str = Field(
        default="All",
        description="Filter by severity ('All', 'Critical', 'High', 'Medium', 'Low')",
    )
    document_ids: list[str] | None = Field(default=None, description="Optional document ID filters")


class HistoricalDiffItem(BaseModel):
    requirement_id: str
    requirement_code: str
    current_status: str
    previous_status: str | None
    status_changed: bool
    current_confidence: float
    previous_confidence: float | None
    new_evidence_found: bool
    summary: str


class HistoricalDiffResponse(BaseModel):
    framework_id: str
    total_requirements: int
    diffs: list[HistoricalDiffItem]

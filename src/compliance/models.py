from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceCategory(str, Enum):
    POLICY_DOCUMENTATION = "POLICY_DOCUMENTATION"
    IMPLEMENTATION_EVIDENCE = "IMPLEMENTATION_EVIDENCE"
    OPERATING_EVIDENCE = "OPERATING_EVIDENCE"
    UNCLASSIFIED = "UNCLASSIFIED"
    NONE = "NONE"


class ComplianceStatus(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"


class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvidenceItem(BaseModel):
    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document identifier")
    document_name: str = Field(description="Parent document filename")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    section_heading: str = Field(default="General", description="Section heading context")
    locator: str = Field(default="", description="Structural paragraph/section locator")
    quote: str = Field(description="Verbatim text quote from the evidence chunk")
    category: EvidenceCategory = Field(
        default=EvidenceCategory.UNCLASSIFIED,
        description="Assurance tier classification",
    )
    relevance_score: float = Field(
        default=0.0,
        description="Qualitative relevance heuristic based on hybrid search density",
    )
    quality_score: float = Field(
        default=0.0,
        description="Heuristic quality score based on structure, keywords, and assurance",
    )
    is_adversarial_suspect: bool = Field(
        default=False,
        description="Flag indicating suspicious prompt injection or override language",
    )


class ComplianceAssessmentResult(BaseModel):
    requirement_id: str = Field(description="Requirement database ID")
    requirement_code: str = Field(description="Requirement identifier (e.g. 'CC6.1')")
    framework_id: str = Field(description="Regulatory framework ID")
    title: str = Field(description="Requirement title")
    category: str = Field(description="Domain category")
    status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"] = Field(
        description="Assessed coverage status"
    )
    confidence_score: float = Field(
        description="Qualitative heuristic indicator (not a calibrated probability)"
    )
    assurance_level: str = Field(
        default="Operating Evidence",
        description="Assurance tier: 'Policy Documentation', 'Implementation Evidence', or 'Operating Evidence'",
    )
    evidence_category: EvidenceCategory = Field(
        default=EvidenceCategory.NONE,
        description="Normalized category enum",
    )
    evidence: EvidenceItem | None = Field(
        default=None,
        description="Primary supporting evidence chunk",
    )
    additional_evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Secondary supporting evidence items",
    )
    gap: str | None = Field(
        default=None,
        description="Identified compliance deficiency",
    )
    recommendation: str | None = Field(
        default=None,
        description="Specific actionable remediation guidance",
    )
    human_review_required: bool = Field(
        default=False,
        description="Mandatory flag indicating human auditor review is required",
    )
    control_objective: str = Field(
        default="",
        description="Deconstructed control objective assessed",
    )
    assessment_rationale: str = Field(
        default="",
        description="Transparent chain-of-thought rationale for status decision",
    )
    previous_status: str | None = Field(
        default=None,
        description="Status from prior historical evaluation if available",
    )
    status_changed: bool = Field(
        default=False,
        description="Whether this evaluation status changed compared to prior historical record",
    )


class HistoricalAssessmentDiff(BaseModel):
    requirement_id: str = Field(description="Requirement ID")
    requirement_code: str = Field(description="Requirement code")
    current_status: str = Field(description="Current assessed status")
    previous_status: str | None = Field(default=None, description="Previous assessed status")
    status_changed: bool = Field(description="True if status shifted")
    current_confidence: float = Field(description="Current heuristic confidence")
    previous_confidence: float | None = Field(default=None, description="Previous heuristic confidence")
    new_evidence_found: bool = Field(default=False, description="True if evidence chunk changed")
    summary: str = Field(description="Human-readable delta description")


class RemediationTask(BaseModel):
    priority_rank: int = Field(description="Remediation priority rank (1 = highest)")
    requirement_code: str = Field(description="Requirement code")
    title: str = Field(description="Requirement title")
    category: str = Field(description="Domain category")
    current_status: Literal["PARTIALLY_COVERED", "MISSING"] = Field(
        description="Current non-compliant status"
    )
    severity: str = Field(description="Severity tier: 'Critical', 'High', 'Medium', 'Low'")
    identified_gap: str = Field(description="Detailed explanation of the deficiency")
    remediation_recommendation: str = Field(description="Specific actionable remediation guidance")
    human_review_required: bool = Field(description="Whether human auditor review is mandated")
    estimated_effort_days: int = Field(
        description="Engineering planning estimate in days (not a factual guarantee)"
    )
    effort_rationale: str = Field(
        default="Engineering planning estimate based on standard implementation scope.",
        description="Disclaimer and basis for effort estimation",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Prerequisite control or requirement dependencies",
    )


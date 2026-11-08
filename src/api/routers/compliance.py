import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_compliance_engine, get_db
from src.api.schemas.compliance import (
    ComplianceEvaluateRequest,
    GapAnalysisRequest,
    HistoricalDiffItem,
    HistoricalDiffResponse,
)
from src.api.security.auth import AuthenticatedUser, require_auditor
from src.compliance.engine import ComplianceIntelligenceEngine
from src.schemas.mcp import (
    ComplianceEvaluationResponse,
    ComplianceEvidence,
    ComplianceFinding,
    CoverageSummary,
    GapAnalysisResponse,
    GapItem,
)
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance Intelligence"])


@router.post(
    "/evaluate",
    response_model=ComplianceEvaluationResponse,
    summary="Evaluate Compliance Framework",
    description="Audit requirements against repository evidence using zero-trust assurance tiers.",
)
def evaluate_compliance_endpoint(
    req: ComplianceEvaluateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_auditor)],
    engine: Annotated[ComplianceIntelligenceEngine, Depends(get_compliance_engine)],
    db: Annotated[DatabaseManager, Depends(get_db)],
) -> ComplianceEvaluationResponse:
    clean_fw = req.framework_id.strip()
    framework = db.get_framework(clean_fw)
    if not framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework '{clean_fw}' not found.",
        )

    assessments = engine.evaluate_framework(
        framework_id=clean_fw,
        requirement_id=req.requirement_id,
        evidence_document_ids=req.evidence_document_ids,
        persist=True,
    )

    findings: list[ComplianceFinding] = []
    for a in assessments:
        evidence_obj = None
        if a.evidence:
            evidence_obj = ComplianceEvidence(
                chunk_id=a.evidence.chunk_id,
                document_id=a.evidence.document_id,
                document_name=a.evidence.document_name,
                page_number=a.evidence.page_number,
                section_heading=a.evidence.section_heading,
                locator=a.evidence.locator,
                quote=a.evidence.quote,
            )

        findings.append(
            ComplianceFinding(
                requirement_code=a.requirement_code,
                title=a.title,
                category=a.category,
                status=a.status,
                confidence_score=a.confidence_score,
                evidence=evidence_obj,
                gap=a.gap,
                recommendation=a.recommendation,
                human_review_required=a.human_review_required,
                assurance_level=a.assurance_level,
            )
        )

    covered_cnt = sum(1 for f in findings if f.status == "COVERED")
    partial_cnt = sum(1 for f in findings if f.status == "PARTIALLY_COVERED")
    missing_cnt = sum(1 for f in findings if f.status == "MISSING")
    total_cnt = len(findings)
    pct = round((covered_cnt / total_cnt * 100.0) if total_cnt > 0 else 0.0, 1)

    summary = CoverageSummary(
        covered=covered_cnt,
        partially_covered=partial_cnt,
        missing=missing_cnt,
        total=total_cnt,
        compliance_percentage=pct,
    )

    return ComplianceEvaluationResponse(
        framework_id=framework["id"],
        framework_name=framework["name"],
        total_requirements=total_cnt,
        coverage_summary=summary,
        findings=findings,
    )


@router.post(
    "/gap-analysis",
    response_model=GapAnalysisResponse,
    summary="Run Compliance Gap Analysis",
    description="Deep deficiency analysis on PARTIALLY_COVERED and MISSING controls with prioritized remediation roadmaps.",
)
def gap_analysis_endpoint(
    req: GapAnalysisRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_auditor)],
    engine: Annotated[ComplianceIntelligenceEngine, Depends(get_compliance_engine)],
    db: Annotated[DatabaseManager, Depends(get_db)],
) -> GapAnalysisResponse:
    clean_fw = req.framework_id.strip()
    framework = db.get_framework(clean_fw)
    if not framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework '{clean_fw}' not found.",
        )

    gap_summary, roadmap = engine.analyze_framework_gaps(clean_fw)

    # Filter by severity if requested
    clean_filter = req.severity_filter.strip().title()
    if clean_filter != "All":
        roadmap = [t for t in roadmap if t.severity.lower() == clean_filter.lower()]

    gap_items = [
        GapItem(
            priority_rank=t.priority_rank,
            requirement_code=t.requirement_code,
            title=t.title,
            category=t.category,
            current_status=t.current_status,
            severity=t.severity,
            identified_gap=t.identified_gap,
            remediation_recommendation=t.remediation_recommendation,
            human_review_required=t.human_review_required,
            estimated_effort_days=t.estimated_effort_days,
        )
        for t in roadmap
    ]

    return GapAnalysisResponse(
        framework_id=framework["id"],
        framework_name=framework["name"],
        total_gaps=len(gap_items),
        covered_count=gap_summary["covered_count"],
        partially_covered_count=gap_summary["partially_covered_count"],
        missing_count=gap_summary["missing_count"],
        human_review_count=gap_summary["human_review_count"],
        remediation_roadmap=gap_items,
    )


@router.get(
    "/history",
    response_model=HistoricalDiffResponse,
    summary="Compliance History & Deltas",
    description="Compare latest requirement assessments against immediately prior evaluations to detect coverage drift.",
)
def compliance_history_endpoint(
    current_user: Annotated[AuthenticatedUser, Depends(require_auditor)],
    engine: Annotated[ComplianceIntelligenceEngine, Depends(get_compliance_engine)],
    db: Annotated[DatabaseManager, Depends(get_db)],
    framework_id: Annotated[str, Query(min_length=1, description="Framework ID or name")] = "SOC2",
) -> HistoricalDiffResponse:
    clean_fw = framework_id.strip()
    framework = db.get_framework(clean_fw)
    if not framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework '{clean_fw}' not found.",
        )

    diffs = engine.compare_historical_assessments(clean_fw)
    diff_items = [
        HistoricalDiffItem(
            requirement_id=d.requirement_id,
            requirement_code=d.requirement_code,
            current_status=d.current_status,
            previous_status=d.previous_status,
            status_changed=d.status_changed,
            current_confidence=round(d.current_confidence, 2),
            previous_confidence=round(d.previous_confidence, 2) if d.previous_confidence is not None else None,
            new_evidence_found=d.new_evidence_found,
            summary=d.summary,
        )
        for d in diffs
    ]

    return HistoricalDiffResponse(
        framework_id=framework["id"],
        total_requirements=len(diff_items),
        diffs=diff_items,
    )

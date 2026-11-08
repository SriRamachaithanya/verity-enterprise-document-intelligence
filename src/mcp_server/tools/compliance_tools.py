import logging

from src.compliance.evidence_classifier import EvidenceClassifier
from src.mcp_server.dependencies import get_compliance_engine, get_db
from src.schemas.mcp import (
    ComplianceEvaluationResponse,
    ComplianceEvidence,
    ComplianceFinding,
    CoverageSummary,
    GapAnalysisResponse,
    GapItem,
)

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
}

ESTIMATED_EFFORT_DAYS = {
    "Critical": 10,
    "High": 5,
    "Medium": 3,
    "Low": 1,
}

_classifier = EvidenceClassifier()


def _detect_assurance_tier(text: str) -> tuple[str, bool]:
    """
    Classify evidence text into assurance tiers (backward-compatible helper):
    - Operating Evidence: logs, tickets, review cycles, audit proofs
    - Implementation Evidence: technical configurations, algorithms, hardware tokens
    - Policy Documentation: policy directives, statements of intent
    Returns: (assurance_level, is_robust)
    """
    category, display_name = _classifier.classify_assurance_tier(text)
    is_robust = category.value in ("OPERATING_EVIDENCE", "IMPLEMENTATION_EVIDENCE")
    return display_name, is_robust


def evaluate_compliance(
    framework_id: str,
    requirement_id: str | None = None,
    evidence_document_ids: list[str] | None = None,
) -> ComplianceEvaluationResponse:
    """
    Audit compliance requirements against the document repository with verifiable chunk evidence.

    Args:
        framework_id: Framework ID or name (e.g. 'SOC2', 'ISO27001').
        requirement_id: Optional specific requirement ID or code (e.g. 'CC6.1').
        evidence_document_ids: Optional list of document IDs to restrict evidence search.

    Returns:
        ComplianceEvaluationResponse with findings, coverage statistics, and exact evidence quotes.
    """
    clean_fw = framework_id.strip()
    if not clean_fw:
        raise ValueError("Argument 'framework_id' cannot be empty.")

    db = get_db()
    framework = db.get_framework(clean_fw)
    if not framework:
        raise ValueError(f"Compliance framework '{clean_fw}' not found.")

    engine = get_compliance_engine()
    assessments = engine.evaluate_framework(
        framework_id=clean_fw,
        requirement_id=requirement_id,
        evidence_document_ids=evidence_document_ids,
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


def gap_analysis(
    framework_id: str,
    document_ids: list[str] | None = None,
    severity_filter: str = "All",
) -> GapAnalysisResponse:
    """
    Perform deep gap analysis on PARTIALLY_COVERED and MISSING compliance requirements.

    Args:
        framework_id: Target framework identifier or name.
        document_ids: Optional document filters.
        severity_filter: Optional filter ('All', 'Critical', 'High', 'Medium', 'Low'). Default is 'All'.

    Returns:
        GapAnalysisResponse with prioritized remediation roadmap and human review requirements.
    """
    clean_filter = severity_filter.strip().title()
    allowed_filters = {"All", "Critical", "High", "Medium", "Low"}
    if clean_filter not in allowed_filters:
        raise ValueError(
            f"Invalid severity_filter '{severity_filter}'. Allowed: {sorted(allowed_filters)}"
        )

    eval_result = evaluate_compliance(
        framework_id=framework_id,
        evidence_document_ids=document_ids,
    )

    db = get_db()
    reqs = {
        r["req_code"]: r
        for r in db.get_requirements_by_framework(eval_result.framework_id)
    }

    gap_items: list[GapItem] = []
    human_review_count = 0

    for finding in eval_result.findings:
        if finding.human_review_required:
            human_review_count += 1

        if finding.status not in ("PARTIALLY_COVERED", "MISSING"):
            continue

        raw_req = reqs.get(finding.requirement_code, {})
        sev_level = raw_req.get("severity_level", 2)
        severity = SEVERITY_MAP.get(sev_level, "High")

        if clean_filter != "All" and severity != clean_filter:
            continue

        effort_days = ESTIMATED_EFFORT_DAYS.get(severity, 3)
        if finding.status == "MISSING":
            effort_days += 2

        gap_items.append(
            GapItem(
                priority_rank=0,  # assigned after sorting
                requirement_code=finding.requirement_code,
                title=finding.title,
                category=finding.category,
                current_status=finding.status,
                severity=severity,
                identified_gap=finding.gap or "Unspecified gap",
                remediation_recommendation=finding.recommendation or "Implement missing controls",
                human_review_required=finding.human_review_required,
                estimated_effort_days=effort_days,
            )
        )

    # Sort gaps by severity (Critical first) then status (MISSING first)
    sev_order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}
    gap_items.sort(
        key=lambda g: (
            sev_order.get(g.severity, 99),
            0 if g.current_status == "MISSING" else 1,
            g.requirement_code,
        )
    )

    for idx, item in enumerate(gap_items):
        item.priority_rank = idx + 1

    return GapAnalysisResponse(
        framework_id=eval_result.framework_id,
        framework_name=eval_result.framework_name,
        total_gaps=len(gap_items),
        covered_count=eval_result.coverage_summary.covered,
        partially_covered_count=eval_result.coverage_summary.partially_covered,
        missing_count=eval_result.coverage_summary.missing,
        human_review_count=human_review_count,
        remediation_roadmap=gap_items,
    )

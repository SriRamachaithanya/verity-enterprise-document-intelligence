import logging
from typing import Any

from src.compliance.models import ComplianceAssessmentResult

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}


class GapAnalyzer:
    """
    Analyzes compliance assessment results to identify, prioritize, and structure
    compliance gaps and deficiencies.
    """

    def analyze_gaps(
        self,
        assessments: list[ComplianceAssessmentResult],
        framework_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Produce a structured gap analysis breakdown from a set of assessment results.
        """
        covered = [a for a in assessments if a.status == "COVERED"]
        partially_covered = [a for a in assessments if a.status == "PARTIALLY_COVERED"]
        missing = [a for a in assessments if a.status == "MISSING"]
        gaps = partially_covered + missing
        human_review = [a for a in assessments if a.human_review_required]

        total = len(assessments)
        compliance_pct = round((len(covered) / total * 100), 1) if total > 0 else 0.0

        gap_details = []
        for a in gaps:
            # Determine severity based on category and status
            cat_lower = a.category.lower()
            if any(term in cat_lower for term in ("access", "encryption", "crypto", "auth", "privilege")):
                severity = "Critical" if a.status == "MISSING" else "High"
            elif any(term in cat_lower for term in ("network", "incident", "vulnerability", "monitoring")):
                severity = "High" if a.status == "MISSING" else "Medium"
            else:
                severity = "Medium" if a.status == "MISSING" else "Low"

            gap_details.append({
                "requirement_code": a.requirement_code,
                "title": a.title,
                "category": a.category,
                "current_status": a.status,
                "severity": severity,
                "identified_gap": a.gap or "Deficiency not formally specified.",
                "recommendation": a.recommendation or "Establish formal control implementation.",
                "human_review_required": a.human_review_required,
                "assurance_level": a.assurance_level,
                "assessment_rationale": a.assessment_rationale,
            })

        # Sort gaps by priority: severity descending, then MISSING before PARTIALLY_COVERED
        gap_details.sort(
            key=lambda g: (
                SEVERITY_WEIGHTS.get(g["severity"], 1),
                1 if g["current_status"] == "MISSING" else 0,
            ),
            reverse=True,
        )

        return {
            "total_assessed": total,
            "covered_count": len(covered),
            "partially_covered_count": len(partially_covered),
            "missing_count": len(missing),
            "total_gaps": len(gaps),
            "human_review_count": len(human_review),
            "compliance_percentage": compliance_pct,
            "gaps": gap_details,
        }


import logging
from typing import Any, Literal

from src.compliance.models import (
    ComplianceAssessmentResult,
    EvidenceCategory,
    EvidenceItem,
)

logger = logging.getLogger(__name__)


class ComplianceAssessmentEngine:
    """
    Evaluates candidate evidence against regulatory requirements and assigns
    coverage status adhering strictly to assurance tier rules.
    """

    def evaluate_requirement(
        self,
        req: dict[str, Any],
        candidate_evidence: list[EvidenceItem],
        control_objectives: list[str] | None = None,
        previous_evaluation: dict[str, Any] | None = None,
    ) -> ComplianceAssessmentResult:
        """
        Evaluate a single requirement against mapped evidence.

        CRITICAL ASSURANCE RULE:
        Never classify a requirement as COVERED on policy evidence alone.
        Statements of intent or policy mandates without implementation or operational proof
        must be classified as PARTIALLY_COVERED with human_review_required=True.
        """
        req_id = req["id"]
        req_code = req.get("req_code", "")
        framework_id = req.get("framework_id", "")
        title = req.get("title", "")
        category = req.get("category", "General")
        obj_text = "; ".join(control_objectives) if control_objectives else f"Baseline control for {req_code}"

        # If no evidence or top candidate fails relevance threshold
        if not candidate_evidence or candidate_evidence[0].relevance_score < 0.015:
            status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING"] = "MISSING"
            confidence = 0.85
            evidence_item = None
            additional = []
            assurance_level = "None"
            ev_category = EvidenceCategory.NONE
            gap = f"No documentation or technical evidence found addressing {req_code} ({title})."
            recommendation = (
                f"Formulate formal policy, configure technical controls, and maintain audit logs for {req_code}."
            )
            human_review = False
            rationale = (
                f"Hybrid search returned no relevant chunks with RRF >= 0.015 for query '{req_code} {title}'. "
                "Marked MISSING."
            )
        else:
            primary_ev = candidate_evidence[0]
            evidence_item = primary_ev
            additional = candidate_evidence[1:]
            ev_category = primary_ev.category

            # Check for adversarial attempt
            if primary_ev.is_adversarial_suspect:
                status = "PARTIALLY_COVERED"
                confidence = 0.40
                assurance_level = "Unclassified (Adversarial Suspect)"
                gap = (
                    f"Evidence text for {req_code} contains suspicious override language attempting to bypass audit rules."
                )
                recommendation = "Subject document to forensic administrative review before relying on its content."
                human_review = True
                rationale = "Adversarial override directive detected in chunk content. Demoted to PARTIALLY_COVERED."

            # RULE: Policy Documentation alone CANNOT produce COVERED
            elif ev_category == EvidenceCategory.POLICY_DOCUMENTATION:
                status = "PARTIALLY_COVERED"
                assurance_level = "Policy Documentation"
                confidence = round(min(0.75, 0.40 + primary_ev.relevance_score * 10), 2)
                gap = (
                    f"Policy documentation exists for {req_code}, but technical enforcement "
                    "or operational audit logs are not verified in evidence."
                )
                recommendation = (
                    f"Provide configuration exports, architecture diagrams, or operational audit logs "
                    f"demonstrating active enforcement of {req_code}."
                )
                human_review = True
                rationale = (
                    f"Found policy documentation in '{primary_ev.document_name}'. Under zero-trust assurance rules, "
                    "policy alone does not constitute complete compliance without implementation or operational proof."
                )

            # High/medium assurance (Implementation or Operating evidence)
            elif ev_category in (EvidenceCategory.IMPLEMENTATION_EVIDENCE, EvidenceCategory.OPERATING_EVIDENCE):
                # Check whether retrieval density is high enough for full coverage
                if primary_ev.relevance_score < 0.020:
                    status = "PARTIALLY_COVERED"
                    assurance_level = (
                        "Operating Evidence"
                        if ev_category == EvidenceCategory.OPERATING_EVIDENCE
                        else "Implementation Evidence"
                    )
                    confidence = round(min(0.80, 0.50 + primary_ev.relevance_score * 10), 2)
                    gap = (
                        f"Technical evidence was identified for {req_code}, but relevance score ({primary_ev.relevance_score:.4f}) "
                        "indicates only partial topical match."
                    )
                    recommendation = f"Provide explicit control evidence directly mapping to all clauses of {req_code}."
                    human_review = True
                    rationale = (
                        f"Technical evidence identified in '{primary_ev.document_name}', but search density is borderline. "
                        "Flagged for human auditor validation."
                    )
                else:
                    status = "COVERED"
                    assurance_level = (
                        "Operating Evidence"
                        if ev_category == EvidenceCategory.OPERATING_EVIDENCE
                        else "Implementation Evidence"
                    )
                    # Heuristic confidence indicator
                    confidence = round(min(0.96, 0.70 + primary_ev.relevance_score * 8 + primary_ev.quality_score * 0.1), 2)
                    gap = None
                    recommendation = (
                        f"Maintain continuous operational logging and periodic compliance reviews for {req_code}."
                    )
                    human_review = False
                    rationale = (
                        f"Verified active {assurance_level.lower()} in '{primary_ev.document_name}' "
                        f"(Locator: {primary_ev.locator}). Control requirements satisfied."
                    )
            else:
                # Unclassified content
                status = "PARTIALLY_COVERED"
                assurance_level = "Unclassified"
                confidence = 0.50
                gap = f"Evidence was located for {req_code}, but content lacks verified technical or policy control criteria."
                recommendation = f"Replace unclassified notes with formal policy or system configuration exports for {req_code}."
                human_review = True
                rationale = f"Chunk located in '{primary_ev.document_name}' could not be classified into a standard assurance tier."

        # Compare with historical evaluation if provided
        prev_status = None
        status_changed = False
        if previous_evaluation:
            prev_status = previous_evaluation.get("status")
            if prev_status and prev_status != status:
                status_changed = True

        return ComplianceAssessmentResult(
            requirement_id=req_id,
            requirement_code=req_code,
            framework_id=framework_id,
            title=title,
            category=category,
            status=status,
            confidence_score=confidence,
            assurance_level=assurance_level,
            evidence_category=ev_category,
            evidence=evidence_item,
            additional_evidence=additional,
            gap=gap,
            recommendation=recommendation,
            human_review_required=human_review,
            control_objective=obj_text,
            assessment_rationale=rationale,
            previous_status=prev_status,
            status_changed=status_changed,
        )


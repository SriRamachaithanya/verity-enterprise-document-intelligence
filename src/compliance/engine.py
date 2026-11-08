import logging
import uuid
from typing import Any

from src.compliance.assessment import ComplianceAssessmentEngine
from src.compliance.evidence_classifier import EvidenceClassifier
from src.compliance.gap_analyzer import GapAnalyzer
from src.compliance.models import (
    ComplianceAssessmentResult,
    HistoricalAssessmentDiff,
    RemediationTask,
)
from src.compliance.remediation import RemediationPlanner
from src.compliance.requirement_mapper import RequirementMapper
from src.indexing.hybrid_search import HybridSearchEngine
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class ComplianceIntelligenceEngine:
    """
    Unified compliance intelligence engine coordinating evidence extraction,
    assurance tier evaluation, gap analysis, historical tracking, and remediation planning.
    """

    def __init__(
        self,
        db: DatabaseManager,
        hybrid_engine: HybridSearchEngine,
    ) -> None:
        self.db = db
        self.hybrid_engine = hybrid_engine
        self.classifier = EvidenceClassifier()
        self.requirement_mapper = RequirementMapper(hybrid_engine, self.classifier)
        self.assessment_engine = ComplianceAssessmentEngine()
        self.gap_analyzer = GapAnalyzer()
        self.remediation_planner = RemediationPlanner()

    def evaluate_framework(
        self,
        framework_id: str,
        requirement_id: str | None = None,
        evidence_document_ids: list[str] | None = None,
        persist: bool = True,
    ) -> list[ComplianceAssessmentResult]:
        """
        Evaluate compliance requirements for a framework against repository evidence.
        """
        clean_fw = framework_id.strip()
        if not clean_fw:
            raise ValueError("Argument 'framework_id' cannot be empty.")

        framework = self.db.get_framework(clean_fw)
        if not framework:
            raise ValueError(f"Compliance framework '{clean_fw}' not found.")

        if requirement_id:
            clean_req = requirement_id.strip()
            single_req = self.db.get_requirement(clean_req, framework_id=framework["id"])
            if not single_req:
                raise ValueError(
                    f"Requirement '{clean_req}' not found under framework '{framework['name']}'."
                )
            requirements = [single_req]
        else:
            requirements = self.db.get_requirements_by_framework(framework["id"])

        if not requirements:
            raise ValueError(f"No requirements found for framework '{framework['name']}'.")

        results: list[ComplianceAssessmentResult] = []

        for req in requirements:
            req_id = req["id"]
            # Retrieve latest previous evaluation for comparison
            prev_eval = self.db.get_latest_evaluation_for_requirement(req_id)

            # Map to candidate evidence
            control_objectives = self.requirement_mapper.extract_control_objectives(req)
            candidate_evidence = self.requirement_mapper.map_requirement_to_evidence(
                req=req,
                top_k=5,
                allowed_document_ids=evidence_document_ids,
            )

            # Perform zero-trust assurance assessment
            assessment = self.assessment_engine.evaluate_requirement(
                req=req,
                candidate_evidence=candidate_evidence,
                control_objectives=control_objectives,
                previous_evaluation=prev_eval,
            )

            # Persist to database if requested
            if persist:
                eval_id = f"eval_{uuid.uuid4().hex[:12]}"
                primary_ev = assessment.evidence
                self.db.insert_evaluation(
                    eval_id=eval_id,
                    requirement_id=req_id,
                    status=assessment.status,
                    confidence_score=assessment.confidence_score,
                    evidence_chunk_id=primary_ev.chunk_id if primary_ev else None,
                    evidence_quote=primary_ev.quote if primary_ev else None,
                    gap_analysis=assessment.gap,
                    recommended_action=assessment.recommendation,
                    human_review_required=assessment.human_review_required,
                    evidence_category=assessment.evidence_category.value,
                    assessment_rationale=assessment.assessment_rationale,
                    previous_status=assessment.previous_status,
                    status_changed=assessment.status_changed,
                    control_objective=assessment.control_objective,
                )

            results.append(assessment)

        return results

    def analyze_framework_gaps(
        self,
        framework_id: str,
    ) -> tuple[dict[str, Any], list[RemediationTask]]:
        """
        Produce a full gap analysis and prioritized remediation roadmap.
        """
        # Run live evaluation across all framework requirements
        assessments = self.evaluate_framework(framework_id=framework_id, persist=True)

        framework = self.db.get_framework(framework_id)
        gap_summary = self.gap_analyzer.analyze_gaps(assessments, framework_metadata=framework)
        remediation_roadmap = self.remediation_planner.generate_roadmap(gap_summary["gaps"])

        return gap_summary, remediation_roadmap

    def compare_historical_assessments(
        self,
        framework_id: str,
    ) -> list[HistoricalAssessmentDiff]:
        """
        Compare the latest evaluation of each requirement against its immediately preceding evaluation.
        """
        clean_fw = framework_id.strip()
        framework = self.db.get_framework(clean_fw)
        if not framework:
            raise ValueError(f"Compliance framework '{clean_fw}' not found.")

        requirements = self.db.get_requirements_by_framework(framework["id"])
        diffs: list[HistoricalAssessmentDiff] = []

        for req in requirements:
            req_id = req["id"]
            history = self.db.get_historical_evaluations_for_requirement(req_id, limit=2)

            if not history:
                continue

            current = history[0]
            if len(history) < 2:
                # Only one evaluation exists in history
                diffs.append(
                    HistoricalAssessmentDiff(
                        requirement_id=req_id,
                        requirement_code=req["req_code"],
                        current_status=current["status"],
                        previous_status=None,
                        status_changed=False,
                        current_confidence=current["confidence_score"],
                        previous_confidence=None,
                        new_evidence_found=bool(current.get("evidence_chunk_id")),
                        summary=f"Initial baseline evaluation recorded as {current['status']}.",
                    )
                )
                continue

            previous = history[1]
            status_changed = current["status"] != previous["status"]
            new_evidence = current.get("evidence_chunk_id") != previous.get("evidence_chunk_id")

            if status_changed:
                summary = (
                    f"Status shifted from {previous['status']} to {current['status']} "
                    f"(Confidence: {previous['confidence_score']:.2f} -> {current['confidence_score']:.2f})."
                )
            elif new_evidence:
                summary = f"Status remained {current['status']}, but fresh evidence chunk was linked."
            else:
                summary = f"Status unchanged ({current['status']})."

            diffs.append(
                HistoricalAssessmentDiff(
                    requirement_id=req_id,
                    requirement_code=req["req_code"],
                    current_status=current["status"],
                    previous_status=previous["status"],
                    status_changed=status_changed,
                    current_confidence=current["confidence_score"],
                    previous_confidence=previous["confidence_score"],
                    new_evidence_found=new_evidence,
                    summary=summary,
                )
            )

        return diffs


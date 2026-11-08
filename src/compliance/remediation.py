import logging
from typing import Any

from src.compliance.models import RemediationTask

logger = logging.getLogger(__name__)

BASE_EFFORT_DAYS = {
    "Critical": 10,
    "High": 5,
    "Medium": 3,
    "Low": 1,
}

DISCLAIMER = (
    "Engineering planning estimate based on typical industry implementation complexity. "
    "Not a factual commitment or binding timeline."
)


class RemediationPlanner:
    """
    Generates actionable, prioritized remediation tasks and engineering planning estimates
    for identified compliance gaps.
    """

    def generate_roadmap(self, gap_details: list[dict[str, Any]]) -> list[RemediationTask]:
        """
        Transform raw gap items into an ordered remediation roadmap.
        """
        tasks: list[RemediationTask] = []

        for rank, gap in enumerate(gap_details, start=1):
            severity = gap.get("severity", "Medium")
            base_days = BASE_EFFORT_DAYS.get(severity, 3)

            # Partially covered controls require less effort than creating from scratch
            is_partial = gap.get("current_status") == "PARTIALLY_COVERED"
            effort_days = max(1, int(base_days * 0.6)) if is_partial else base_days

            # Identify probable architectural dependencies based on category
            category = gap.get("category", "")
            dependencies: list[str] = []
            if "mfa" in gap.get("requirement_code", "").lower() or "access" in category.lower():
                dependencies.append("Identity Provider (IdP) Core Configuration")
            if "encryption" in category.lower():
                dependencies.append("Key Management Service (KMS) Provisioning")
            if "incident" in category.lower():
                dependencies.append("Centralized Log Aggregation Pipeline")

            task = RemediationTask(
                priority_rank=rank,
                requirement_code=gap["requirement_code"],
                title=gap["title"],
                category=category,
                current_status=gap["current_status"],
                severity=severity,
                identified_gap=gap["identified_gap"],
                remediation_recommendation=gap["recommendation"],
                human_review_required=gap["human_review_required"],
                estimated_effort_days=effort_days,
                effort_rationale=DISCLAIMER,
                dependencies=dependencies,
            )
            tasks.append(task)

        return tasks


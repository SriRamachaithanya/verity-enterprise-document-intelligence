import logging
from typing import Any

from src.compliance.evidence_classifier import EvidenceClassifier
from src.compliance.models import EvidenceItem
from src.indexing.hybrid_search import HybridSearchEngine

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "with", "that", "this", "from", "have", "entity", "controls", "requirement",
    "must", "shall", "should", "ensure", "provides", "including", "system",
}


class RequirementMapper:
    """
    Deconstructs regulatory requirements into control objectives and maps them
    against the indexed document repository via hybrid retrieval.
    """

    def __init__(
        self,
        hybrid_engine: HybridSearchEngine,
        classifier: EvidenceClassifier | None = None,
    ) -> None:
        self.hybrid_engine = hybrid_engine
        self.classifier = classifier or EvidenceClassifier()

    def extract_control_objectives(self, req: dict[str, Any]) -> list[str]:
        """
        Deconstruct requirement text and title into distinct actionable control objectives.
        """
        title = req.get("title", "")
        desc = req.get("description", "")
        combined = f"{title}. {desc}".strip()

        # Split on sentence boundaries or semicolons
        raw_parts = [p.strip() for p in combined.replace(";", ".").split(".") if len(p.strip()) > 10]
        if not raw_parts:
            return [f"Implement baseline controls for {req.get('req_code', 'requirement')}"]
        return raw_parts

    def map_requirement_to_evidence(
        self,
        req: dict[str, Any],
        top_k: int = 5,
        allowed_document_ids: list[str] | None = None,
    ) -> list[EvidenceItem]:
        """
        Execute hybrid search and filter/rank candidate chunks for a specific requirement.
        Only chunks with genuine topical overlap (requirement code or keywords) are admitted.
        """
        req_code = req.get("req_code", "").strip()
        title = req.get("title", "").strip()
        search_query = f"{req_code} {title}".strip()

        raw_results = self.hybrid_engine.search(query=search_query, top_k=top_k)

        # Filter by document IDs if constrained
        if allowed_document_ids:
            allowed_set = set(allowed_document_ids)
            raw_results = [r for r in raw_results if r.document_id in allowed_set]

        if not raw_results:
            return []

        # Extract title keywords for topical overlap verification
        keywords = {
            w.lower().strip(",.:;()[]'\"")
            for w in title.split()
            if len(w) > 3 and w.lower() not in STOP_WORDS
        }

        evidence_items: list[EvidenceItem] = []
        for r in raw_results:
            content_lower = r.content.lower()
            code_matched = bool(req_code and req_code.lower() in content_lower)
            kw_overlap_count = sum(1 for kw in keywords if kw in content_lower)

            # Strict guard: candidate chunk must have topical relevance
            # Either explicit requirement code match or at least one title keyword match
            if not (code_matched or kw_overlap_count >= 1):
                continue

            chunk_dict = {
                "id": r.chunk_id,
                "document_id": r.document_id,
                "document_name": r.document_name,
                "page_number": r.page_number,
                "section_heading": r.section_heading,
                "locator": r.locator,
                "content": r.content,
            }
            ev_item = self.classifier.evaluate_chunk(chunk_dict, rrf_score=r.rrf_score)
            evidence_items.append(ev_item)

        # Sort candidate evidence: primarily by hybrid retrieval score, secondary by quality
        evidence_items.sort(
            key=lambda x: (x.relevance_score, x.quality_score),
            reverse=True,
        )
        return evidence_items

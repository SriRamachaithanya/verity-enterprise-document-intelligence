import re
from typing import Any

from src.agent.models import IntentResult, UserIntent

# Regex patterns for entity extraction
FRAMEWORK_PATTERN = re.compile(r"\b(SOC\s*2|ISO\s*27001|HIPAA|PCI-?DSS|NIST)\b", re.IGNORECASE)
REQUIREMENT_PATTERN = re.compile(
    r"\b(CC\d+\.\d+|A\.\d+\.\d+(\.\d+)?|REQ-\d+|CR-\d+)\b", re.IGNORECASE
)
CHUNK_ID_PATTERN = re.compile(r"\b(chk_[a-zA-Z0-9_-]+)\b")
DOC_ID_PATTERN = re.compile(r"\b(doc_[a-zA-Z0-9_-]+)\b")
SLUG_PATTERN = re.compile(r"\b([a-z0-9]+(?:-[a-z0-9]+)+)\b")
SEVERITY_PATTERN = re.compile(r"\b(critical|high|medium|low)\b", re.IGNORECASE)


class IntentRouter:
    """
    Deterministic and rule-assisted Intent Router.
    Classifies user queries into the 7 supported intents and extracts entities.
    Prevents LLMs from hallucinating arbitrary tool names.
    """

    def route(self, user_query: str) -> IntentResult:
        query = user_query.strip()
        lower = query.lower()

        entities: dict[str, Any] = {}

        # 1. Entity Extraction
        fw_match = FRAMEWORK_PATTERN.search(query)
        if fw_match:
            raw_fw = fw_match.group(1).upper().replace(" ", "")
            entities["framework_id"] = "SOC2" if "SOC2" in raw_fw else raw_fw

        req_match = REQUIREMENT_PATTERN.search(query)
        if req_match:
            entities["requirement_id"] = req_match.group(1).upper()

        chunk_match = CHUNK_ID_PATTERN.search(query)
        if chunk_match:
            entities["chunk_id"] = chunk_match.group(1)

        doc_match = DOC_ID_PATTERN.search(query)
        if doc_match:
            entities["document_id"] = doc_match.group(1)

        sev_match = SEVERITY_PATTERN.search(query)
        if sev_match:
            entities["severity_filter"] = sev_match.group(1).capitalize()
        else:
            entities["severity_filter"] = "All"

        slug_match = SLUG_PATTERN.search(query)
        if slug_match and not chunk_match and not doc_match:
            entities["node_slug"] = slug_match.group(1)

        # 2. Intent Classification Rules

        # A. Citation Verification (checks chunk_id or explicit citation validation)
        if (
            "verify citation" in lower
            or "validate citation" in lower
            or "check citation" in lower
            or "citation verification" in lower
            or ("citation" in lower and "chk_" in lower)
            or ("verify" in lower and "chk_" in lower)
        ):
            return IntentResult(
                intent=UserIntent.CITATION_VERIFICATION,
                confidence=0.95,
                extracted_entities=entities,
                reasoning="Query explicitly requests citation verification or targets a chunk ID.",
            )

        # B. Document Discovery (list/show/catalog of documents)
        if (
            ("list" in lower or "show" in lower or "catalog" in lower or "what" in lower)
            and ("document" in lower or "documents" in lower or "files" in lower)
            and not any(k in lower for k in ("search", "find", "verify", "check", "audit", "compliant", "gap"))
        ) or any(
            phrase in lower
            for phrase in (
                "list documents",
                "show documents",
                "what documents",
                "available documents",
                "list files",
                "uploaded documents",
                "document catalog",
                "get documents",
            )
        ):
            return IntentResult(
                intent=UserIntent.DOCUMENT_DISCOVERY,
                confidence=0.98,
                extracted_entities=entities,
                reasoning="Query matches document catalog/listing intent.",
            )

        # C. Compliance Gap Analysis
        if any(
            phrase in lower
            for phrase in (
                "gap analysis",
                "gaps",
                "missing controls",
                "remediation",
                "remediation plan",
                "action items",
                "deficiencies",
            )
        ):
            if "framework_id" not in entities:
                entities["framework_id"] = "SOC2"  # default fallback framework
            return IntentResult(
                intent=UserIntent.COMPLIANCE_GAP_ANALYSIS,
                confidence=0.94,
                extracted_entities=entities,
                reasoning="Query explicitly asks for compliance gap or remediation analysis.",
            )

        # D. Compliance Evaluation
        if any(
            phrase in lower
            for phrase in (
                "compliant with",
                "compliance evaluation",
                "audit against",
                "evaluate compliance",
                "are we compliant",
                "check compliance",
                "is requirement",
                "is covered",
                "requirement coverage",
            )
        ) or (("soc 2" in lower or "soc2" in lower or "iso 27001" in lower) and ("audit" in lower or "covered" in lower or "compliance" in lower)):
            if "framework_id" not in entities:
                entities["framework_id"] = "SOC2"
            return IntentResult(
                intent=UserIntent.COMPLIANCE_EVALUATION,
                confidence=0.95,
                extracted_entities=entities,
                reasoning="Query requests compliance evaluation against a framework or requirement.",
            )

        # E. Knowledge Exploration
        if any(
            phrase in lower
            for phrase in (
                "knowledge graph",
                "linked notes",
                "backlinks",
                "wiki links",
                "related concepts",
                "explore knowledge",
                "note graph",
            )
        ) or ("node" in lower and "slug" in lower):
            if "node_slug" not in entities:
                entities["node_slug"] = "mfa-policy"
            return IntentResult(
                intent=UserIntent.KNOWLEDGE_EXPLORATION,
                confidence=0.92,
                extracted_entities=entities,
                reasoning="Query requests knowledge graph or linked concepts exploration.",
            )

        # F. Explicit Document Search
        if lower.startswith(("search for", "find passages", "search documents")):
            clean_search_query = re.sub(r"^(search for|find passages on|search documents for)\s*", "", query, flags=re.IGNORECASE)
            entities["query_text"] = clean_search_query
            return IntentResult(
                intent=UserIntent.DOCUMENT_SEARCH,
                confidence=0.90,
                extracted_entities=entities,
                reasoning="Query starts with explicit search directive.",
            )

        # G. General Document Q&A (default for questions about policies/documents)
        entities["query_text"] = query
        return IntentResult(
            intent=UserIntent.DOCUMENT_QA,
            confidence=0.85,
            extracted_entities=entities,
            reasoning="Query represents a natural language domain question against enterprise documents.",
        )

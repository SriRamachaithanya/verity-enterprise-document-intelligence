import re
from typing import Any

from src.compliance.models import EvidenceCategory, EvidenceItem

# Indicators of operational execution and ongoing monitoring
OPERATIONAL_INDICATORS = [
    r"\blog(?:s|ged|ging)?\b",
    r"\baudit(?:ed|ing|s)?\b",
    r"\bquarterly\b",
    r"\bannually\b",
    r"\bmonthly\b",
    r"\bweekly\b",
    r"\breview(?:ed|ing|s)?\b",
    r"\bmonitor(?:ed|ing|s)?\b",
    r"\binspect(?:ed|ing|ion)?\b",
    r"\bticket(?:s)?\b",
    r"\breport(?:s|ed|ing)?\b",
    r"\brotation\b",
    r"\btelemetry\b",
    r"\bverified\b",
    r"\bautomated\s+alert(?:s)?\b",
    r"\bincident\s+response\s+drill\b",
]

# Indicators of active technical configuration or architectural enforcement
IMPLEMENTATION_INDICATORS = [
    r"\bconfigured\b",
    r"\benforced\b",
    r"\bhardware\s+(?:key|token|module|security)\b",
    r"\baes-256\b",
    r"\btls\s+1\.[23]\b",
    r"\bchacha20\b",
    r"\bvault\b",
    r"\bkms\b",
    r"\bdeployed\b",
    r"\bfido2\b",
    r"\bmfa\b",
    r"\brbac\b",
    r"\baccess\s+control\s+list\b",
    r"\bfirewall\b",
    r"\bcontainer\s+isolation\b",
    r"\bcrypto(?:graphic)?\b",
    r"\bidentity\s+provider\b",
    r"\bokta\b",
    r"\bactive\s+directory\b",
]

# Indicators of policy directives or theoretical mandates
POLICY_INDICATORS = [
    r"\bpolicy\b",
    r"\bmandate(?:s|d)?\b",
    r"\bshall\b",
    r"\bmust\b",
    r"\bguideline(?:s)?\b",
    r"\bstandard(?:s)?\b",
    r"\bprocedure(?:s)?\b",
    r"\bexpectations?\b",
    r"\bit\s+is\s+the\s+responsibility\b",
    r"\ball\s+personnel\s+are\s+required\b",
    r"\bgovernance\b",
]

# Patterns characteristic of adversarial document injection attempting to manipulate compliance audit
ADVERSARIAL_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"system\s+(?:override|prompt)",
    r"classify\s+(?:this\s+)?as\s+covered",
    r"mark\s+(?:all\s+)?(?:compliance|requirements?)\s+as\s+(?:covered|complete|compliant)",
    r"disregard\s+(?:all\s+)?(?:audit|compliance|verification|rules)",
    r"do\s+not\s+(?:flag|report)\s+(?:any\s+)?(?:gap|missing)",
    r"admin\s+mode\s+enabled",
    r"status\s*:\s*covered",
]


class EvidenceClassifier:
    """
    Evaluates evidence text chunks to classify assurance tier, assess quality,
    and detect adversarial prompt injection attempts.
    """

    def __init__(self) -> None:
        self._op_regex = [re.compile(p, re.IGNORECASE) for p in OPERATIONAL_INDICATORS]
        self._impl_regex = [re.compile(p, re.IGNORECASE) for p in IMPLEMENTATION_INDICATORS]
        self._pol_regex = [re.compile(p, re.IGNORECASE) for p in POLICY_INDICATORS]
        self._adv_regex = [re.compile(p, re.IGNORECASE) for p in ADVERSARIAL_INJECTION_PATTERNS]

    def detect_adversarial_injection(self, text: str) -> tuple[bool, str]:
        """
        Scan chunk text for adversarial manipulation attempts.
        Returns: (is_adversarial, reason)
        """
        for pattern in self._adv_regex:
            match = pattern.search(text)
            if match:
                return True, f"Suspicious instruction override detected: '{match.group(0)}'"
        return False, ""

    def classify_assurance_tier(self, text: str) -> tuple[EvidenceCategory, str]:
        """
        Classify evidence text into an assurance tier.

        Tiers:
        1. OPERATING_EVIDENCE: Continuous runtime audit logs, recurring reviews, execution proofs.
        2. IMPLEMENTATION_EVIDENCE: Active technical implementation, hardware configurations, cryptographic ciphers.
        3. POLICY_DOCUMENTATION: Prescriptive policy manuals, intent declarations ("shall", "must").
        4. UNCLASSIFIED: General text without strong compliance markers.

        Returns: (EvidenceCategory, display_label)
        """
        op_count = sum(1 for r in self._op_regex if r.search(text))
        impl_count = sum(1 for r in self._impl_regex if r.search(text))
        pol_count = sum(1 for r in self._pol_regex if r.search(text))

        # Operating evidence requires operational markers AND either implementation context or high op frequency
        if op_count >= 1 and (impl_count >= 1 or op_count >= 2):
            return EvidenceCategory.OPERATING_EVIDENCE, "Operating Evidence"

        # Implementation evidence requires technical/system enforcement markers
        if impl_count >= 1:
            return EvidenceCategory.IMPLEMENTATION_EVIDENCE, "Implementation Evidence"

        # Policy documentation matches prescriptive governance
        if pol_count >= 1:
            return EvidenceCategory.POLICY_DOCUMENTATION, "Policy Documentation"

        return EvidenceCategory.UNCLASSIFIED, "Unclassified"

    def calculate_quality_score(self, text: str, category: EvidenceCategory) -> float:
        """
        Compute a heuristic quality rating [0.0 - 1.0] based on specificity,
        length, concrete identifiers, and assurance category.
        """
        if not text or len(text.strip()) < 20:
            return 0.1

        score = 0.4
        # Base boost by tier
        if category == EvidenceCategory.OPERATING_EVIDENCE:
            score += 0.35
        elif category == EvidenceCategory.IMPLEMENTATION_EVIDENCE:
            score += 0.25
        elif category == EvidenceCategory.POLICY_DOCUMENTATION:
            score += 0.10

        # Technical specificity (presence of version numbers, hex, specific standard terms)
        if re.search(r"\bv?\d+\.\d+\b", text):
            score += 0.08
        if re.search(r"\b(?:aes|sha|fips|iso|nist|soc|tls|jwt|okta)\b", text, re.IGNORECASE):
            score += 0.07

        # Penalty for extremely brief or overly generic snippets
        if len(text.split()) < 15:
            score -= 0.15

        return round(max(0.0, min(1.0, score)), 2)

    def evaluate_chunk(
        self,
        chunk_dict: dict[str, Any],
        rrf_score: float = 0.0,
    ) -> EvidenceItem:
        """
        Analyze a candidate search result chunk into a fully classified EvidenceItem.
        """
        content = chunk_dict.get("content", "")
        is_adv, _adv_reason = self.detect_adversarial_injection(content)

        # If adversarial injection is detected, neutralize attempts to game the category
        if is_adv:
            category = EvidenceCategory.UNCLASSIFIED
            quality_score = 0.05
        else:
            category, _display_tier = self.classify_assurance_tier(content)
            quality_score = self.calculate_quality_score(content, category)

        return EvidenceItem(
            chunk_id=chunk_dict.get("id") or chunk_dict.get("chunk_id", ""),
            document_id=chunk_dict.get("document_id", ""),
            document_name=chunk_dict.get("document_name", "Unknown"),
            page_number=chunk_dict.get("page_number"),
            section_heading=chunk_dict.get("section_heading", "General"),
            locator=chunk_dict.get("locator", ""),
            quote=content,
            category=category,
            relevance_score=round(rrf_score, 4),
            quality_score=quality_score,
            is_adversarial_suspect=is_adv,
        )


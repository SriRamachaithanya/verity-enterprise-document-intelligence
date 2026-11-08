import html
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that suggest an adversarial prompt injection attempt
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules)", re.IGNORECASE),
    re.compile(r"override\s+(the\s+)?system\s+(prompt|instructions|rules)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|unrestricted)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(rules|instructions|constraints)", re.IGNORECASE),
    re.compile(r"forget\s+all\s+(your\s+)?(rules|instructions)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"bypass\s+(safety|security|compliance)\s+checks?", re.IGNORECASE),
]


def sanitize_user_input(text: str) -> str:
    """Strip terminal escape codes and null bytes from user input."""
    if not text:
        return ""
    # Strip null bytes and non-printable control characters except \n, \r, \t
    cleaned = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 127))
    return cleaned.strip()


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """
    Inspect input text for known prompt-injection signatures.
    Returns: (is_injection, matched_pattern_description)
    """
    if not text:
        return False, None
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Suspicious phrase detected: '{match.group(0)}'"
    return False, None


def wrap_evidence_in_xml(evidence_items: list[dict[str, Any]]) -> str:
    """
    Enclose untrusted document evidence chunks in strict XML boundaries
    to prevent prompt-injection attacks from overriding agent reasoning.
    """
    if not evidence_items:
        return "<document_evidence_block>\n  <!-- No supporting evidence retrieved -->\n</document_evidence_block>"

    blocks: list[str] = ["<document_evidence_block>"]
    for item in evidence_items:
        chunk_id = html.escape(str(item.get("chunk_id", "unknown")))
        doc_name = html.escape(str(item.get("document_name", "unknown")))
        page = item.get("page_number")
        page_str = str(page) if page is not None else "N/A"
        locator = html.escape(str(item.get("locator", "")))
        heading = html.escape(str(item.get("section_heading", "General")))
        raw_text = str(item.get("content") or item.get("quote") or item.get("exact_text") or "")

        # Neutralize any potential XML closing tags in raw text
        safe_text = raw_text.replace("</chunk>", "").replace("</document_evidence_block>", "")

        blocks.append(
            f'  <chunk id="{chunk_id}" document="{doc_name}" page="{page_str}" locator="{locator}" section="{heading}">\n'
            f"    <![CDATA[\n{safe_text}\n    ]]>\n"
            f"  </chunk>"
        )
    blocks.append("</document_evidence_block>")
    return "\n".join(blocks)


def enforce_tool_allowlist(tool_name: str, allowlist: set[str]) -> bool:
    """Verify tool name exists in discovered allowlist."""
    return tool_name in allowlist


def sanitize_log_payload(payload: dict[str, Any], max_length: int = 300) -> dict[str, Any]:
    """
    Sanitize arguments and output payloads for audit logs.
    Truncates large text bodies to protect sensitive document content and RAM.
    """
    sanitized: dict[str, Any] = {}
    for k, v in payload.items():
        if isinstance(v, str):
            if len(v) > max_length:
                sanitized[k] = v[:max_length] + f"... [truncated {len(v) - max_length} chars]"
            else:
                sanitized[k] = v
        elif isinstance(v, dict):
            sanitized[k] = sanitize_log_payload(v, max_length)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_log_payload(item, max_length) if isinstance(item, dict)
                else (item[:max_length] + "..." if isinstance(item, str) and len(item) > max_length else item)
                for item in v[:10]  # cap list at 10 items
            ]
        else:
            sanitized[k] = v
    return sanitized


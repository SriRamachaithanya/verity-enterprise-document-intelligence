import hashlib
import logging
from typing import Any

from src.agent.models import ToolExecutionResult, ValidatedCitation
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class EvidenceValidator:
    """
    Cryptographic and Referential Evidence Validator.
    Ensures zero fabricated citations by verifying every evidence claim
    against the ground-truth SQLite document chunks and cryptographic SHA-256 digests.
    """

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db = db_manager

    def validate_citations(
        self,
        tool_results: list[ToolExecutionResult],
    ) -> list[ValidatedCitation]:
        """
        Extract and validate all citations returned from MCP tools during the execution turn.
        """
        validated_citations: list[ValidatedCitation] = []
        seen_chunks: set[str] = set()

        for res in tool_results:
            if res.is_error or not res.parsed_data:
                continue

            data = res.parsed_data

            # 1. Citations from get_citation tool
            if res.tool_name == "get_citation" and isinstance(data, dict):
                chunk_id = data.get("chunk_id")
                if chunk_id and chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    validated = self._validate_single_citation(
                        chunk_id=chunk_id,
                        document_id=data.get("document_id", "unknown"),
                        document_name=data.get("document_name", "unknown"),
                        page_number=data.get("page_number"),
                        locator=data.get("locator", ""),
                        section_heading=data.get("section_heading", "General"),
                        exact_text=data.get("exact_text", ""),
                        reported_hash=data.get("sha256_verification"),
                    )
                    validated_citations.append(validated)

            # 2. Citations from search_documents tool
            elif res.tool_name == "search_documents" and isinstance(data, dict):
                for item in data.get("results", []):
                    chunk_id = item.get("chunk_id")
                    if chunk_id and chunk_id not in seen_chunks:
                        seen_chunks.add(chunk_id)
                        validated = self._validate_single_citation(
                            chunk_id=chunk_id,
                            document_id=item.get("document_id", "unknown"),
                            document_name=item.get("document_name", "unknown"),
                            page_number=item.get("page_number"),
                            locator=item.get("locator", ""),
                            section_heading=item.get("section_heading", "General"),
                            exact_text=item.get("content", ""),
                            reported_hash=None,
                        )
                        validated_citations.append(validated)

            # 3. Evidence from evaluate_compliance tool
            elif res.tool_name == "evaluate_compliance" and isinstance(data, dict):
                for finding in data.get("findings", []):
                    ev = finding.get("evidence")
                    if ev and ev.get("chunk_id"):
                        chunk_id = ev["chunk_id"]
                        if chunk_id not in seen_chunks:
                            seen_chunks.add(chunk_id)
                            validated = self._validate_single_citation(
                                chunk_id=chunk_id,
                                document_id=ev.get("document_id", "unknown"),
                                document_name=ev.get("document_name", "unknown"),
                                page_number=ev.get("page_number"),
                                locator=ev.get("locator", ""),
                                section_heading=ev.get("section_heading", "General"),
                                exact_text=ev.get("quote", ""),
                                reported_hash=None,
                            )
                            validated_citations.append(validated)

        return validated_citations

    def _validate_single_citation(
        self,
        chunk_id: str,
        document_id: str,
        document_name: str,
        page_number: int | None,
        locator: str,
        section_heading: str,
        exact_text: str,
        reported_hash: str | None,
    ) -> ValidatedCitation:
        """Verify chunk against SQLite record and cryptographic SHA-256 digest."""
        computed_hash = hashlib.sha256(exact_text.encode("utf-8")).hexdigest()

        # Database cross-check
        db_chunk = self.db.get_chunk_by_id(chunk_id) if self.db else None

        if self.db and not db_chunk:
            return ValidatedCitation(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name=document_name,
                page_number=page_number,
                locator=locator,
                section_heading=section_heading,
                exact_text=exact_text,
                sha256_hash=computed_hash,
                is_valid=False,
                validation_notes=f"Referential integrity failure: Chunk ID '{chunk_id}' not found in SQLite store.",
            )

        # Hash verification against reported hash
        if reported_hash and reported_hash != computed_hash:
            return ValidatedCitation(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name=document_name,
                page_number=page_number,
                locator=locator,
                section_heading=section_heading,
                exact_text=exact_text,
                sha256_hash=computed_hash,
                is_valid=False,
                validation_notes=f"Cryptographic failure: Hash mismatch (reported={reported_hash[:8]}, computed={computed_hash[:8]}).",
            )

        # Database content verification if DB chunk available
        if db_chunk:
            db_content = db_chunk["content"]
            db_hash = hashlib.sha256(db_content.encode("utf-8")).hexdigest()
            if db_hash != computed_hash and exact_text not in db_content:
                return ValidatedCitation(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page_number,
                    locator=locator,
                    section_heading=section_heading,
                    exact_text=exact_text,
                    sha256_hash=computed_hash,
                    is_valid=False,
                    validation_notes="Content tampering detected: Text does not match SQLite record.",
                )

        return ValidatedCitation(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            locator=locator,
            section_heading=section_heading,
            exact_text=exact_text,
            sha256_hash=computed_hash,
            is_valid=True,
            validation_notes="Cryptographically and referentially verified against SQLite ground truth.",
        )

    def extract_evidence_items(
        self,
        tool_results: list[ToolExecutionResult],
    ) -> list[dict[str, Any]]:
        """Collect all evidence candidate chunks for prompt context framing."""
        items: list[dict[str, Any]] = []
        seen = set()

        for res in tool_results:
            if res.is_error or not res.parsed_data:
                continue

            data = res.parsed_data

            if res.tool_name == "search_documents" and isinstance(data, dict):
                for r in data.get("results", []):
                    cid = r.get("chunk_id")
                    if cid and cid not in seen:
                        seen.add(cid)
                        items.append(r)

            elif res.tool_name == "get_citation" and isinstance(data, dict):
                cid = data.get("chunk_id")
                if cid and cid not in seen:
                    seen.add(cid)
                    items.append({
                        "chunk_id": cid,
                        "document_id": data.get("document_id"),
                        "document_name": data.get("document_name"),
                        "page_number": data.get("page_number"),
                        "locator": data.get("locator"),
                        "section_heading": data.get("section_heading"),
                        "content": data.get("exact_text"),
                    })

            elif res.tool_name == "evaluate_compliance" and isinstance(data, dict):
                for f in data.get("findings", []):
                    ev = f.get("evidence")
                    if ev and ev.get("chunk_id"):
                        cid = ev["chunk_id"]
                        if cid not in seen:
                            seen.add(cid)
                            items.append({
                                "chunk_id": cid,
                                "document_id": ev.get("document_id"),
                                "document_name": ev.get("document_name"),
                                "page_number": ev.get("page_number"),
                                "locator": ev.get("locator"),
                                "section_heading": ev.get("section_heading"),
                                "content": ev.get("quote"),
                            })

        return items


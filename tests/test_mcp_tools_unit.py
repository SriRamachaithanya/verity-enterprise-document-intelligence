import hashlib
import uuid

import pytest

from src.indexing.chunker import DocumentChunker
from src.indexing.embedding_service import get_embedding_service
from src.indexing.hybrid_search import HybridSearchEngine
from src.mcp_server.dependencies import set_dependencies
from src.mcp_server.tools import (
    evaluate_compliance,
    gap_analysis,
    get_citation,
    get_document_metadata,
    get_related_knowledge,
    list_documents,
    search_documents,
)
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore


@pytest.fixture
def mcp_test_env(tmp_path):
    """
    Sets up an isolated SQLite DB, FAISS vector store, and dependencies
    populated with synthetic compliance and document fixtures.
    """
    db_path = tmp_path / "mcp_test.db"
    faiss_dir = tmp_path / "faiss_test"

    db = DatabaseManager(db_path=db_path)
    store = FAISSVectorStore(index_dir=faiss_dir)
    embed_svc = get_embedding_service()
    hybrid_search = HybridSearchEngine(db_manager=db, vector_store=store, embedding_service=embed_svc)

    set_dependencies(db=db, vector_store=store, embedding_service=embed_svc, hybrid_search=hybrid_search)

    # 1. Ingest synthetic document
    doc_id = "doc_test_sec_01"
    doc_text = (
        "Section 1.0 General Administration\n"
        "This policy defines mandatory baseline security controls for all cloud services.\n\n"
        "Section 2.1 Multi-Factor Authentication\n"
        "All corporate and production system access mandates multi-factor authentication (MFA) "
        "with FIDO2 hardware tokens or TOTP authenticator applications. Passwords must be at least "
        "16 characters and rotated annually. Engineering personnel must maintain active audit logs "
        "and quarterly review records of authentication events.\n\n"
        "Section 4.3 Data Storage Encryption Standards\n"
        "All customer sensitive and confidential records residing on production relational databases "
        "and storage buckets must be encrypted at rest using NIST-approved AES-256 GCM or ChaCha20-Poly1305. "
        "Cryptographic keys must rotate automatically every 90 days via AWS KMS or HashiCorp Vault.\n\n"
        "Section 5.0 Incident Reporting\n"
        "Employees should notify security upon observing suspicious activity."
    )
    meta = DocumentMetadata(
        filename="Corporate_Security_Policy_2026.pdf",
        file_hash=hashlib.sha256(doc_text.encode("utf-8")).hexdigest(),
        mime_type="application/pdf",
        file_size_bytes=len(doc_text.encode("utf-8")),
        page_count=3,
        extra={"department": "Security & Compliance"},
    )
    db.insert_document(doc_id=doc_id, meta=meta, filepath=str(tmp_path / "doc.pdf"))

    # 2. Chunk and index
    chunker = DocumentChunker(target_tokens=60, overlap_tokens=10)
    extracted = ExtractedDocument(
        metadata=meta,
        elements=[
            ParsedElement(
                text=(
                    "Section 1.0 General Administration\n"
                    "This policy defines mandatory baseline security controls for all cloud services."
                ),
                page_number=1,
                section_heading="Section 1.0",
                locator="Page 1",
            ),
            ParsedElement(
                text=(
                    "Section 2.1 Multi-Factor Authentication\n"
                    "All corporate and production system access mandates multi-factor authentication (MFA) "
                    "with FIDO2 hardware tokens or TOTP authenticator applications. Passwords must be at least "
                    "16 characters and rotated annually. Engineering personnel must maintain active audit logs "
                    "and quarterly review records of authentication events."
                ),
                page_number=1,
                section_heading="Section 2.1",
                locator="Page 1",
            ),
            ParsedElement(
                text=(
                    "Section 4.3 Data Storage Encryption Standards\n"
                    "All customer sensitive and confidential records residing on production relational databases "
                    "and storage buckets must be encrypted at rest using NIST-approved AES-256 GCM or ChaCha20-Poly1305. "
                    "Cryptographic keys must rotate automatically every 90 days via AWS KMS or HashiCorp Vault."
                ),
                page_number=2,
                section_heading="Section 4.3",
                locator="Page 2",
            ),
        ],
    )
    chunks = chunker.chunk_document(extracted, doc_id)

    chunk_ids = [c.id for c in chunks]
    vectors = embed_svc.embed_texts([c.content for c in chunks])
    store.add_vectors(chunk_ids, vectors)
    db.insert_chunks(chunks)

    # 3. Seed compliance framework and requirements
    fw_id = "fw_soc2_test"
    db.insert_framework(
        framework_id=fw_id,
        name="SOC2",
        version="2026.1",
        description="AICPA SOC 2 Trust Services Criteria",
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC6.1",
        title="Logical Access and Authentication Controls",
        description="The entity implements logical access security software, multi-factor authentication, and infrastructure credentials.",
        category="Access Control",
        severity_level=1,  # Critical
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC6.6",
        title="Encryption of Sensitive Data at Rest",
        description="Data at rest on production datastores is protected using strong AES-256 or ChaCha20 cryptography with key rotation.",
        category="Cryptography",
        severity_level=2,  # High
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC7.1",
        title="Vulnerability Assessment and Penetration Testing",
        description="The entity conducts automated vulnerability scans monthly and annual external penetration testing by certified third parties.",
        category="Vulnerability Management",
        severity_level=2,  # High
    )

    # 4. Seed knowledge graph notes and links
    node1_id = "kn_mfa"
    db.insert_knowledge_node(
        node_id=node1_id,
        slug="mfa-policy",
        title="Multi-Factor Authentication Standard",
        node_type="control",
        content_markdown="# Multi-Factor Authentication\nMandates hardware tokens per [[soc2-cc6-1]]. Cross-references [[cloud-security]].",
    )
    node2_id = "kn_cloud"
    db.insert_knowledge_node(
        node_id=node2_id,
        slug="cloud-security",
        title="Cloud Infrastructure Security Baseline",
        node_type="document",
        content_markdown="# Cloud Baseline\nApplies across AWS accounts. Links to [[encryption-standard]].",
    )
    node3_id = "kn_enc"
    db.insert_knowledge_node(
        node_id=node3_id,
        slug="encryption-standard",
        title="Data Storage Encryption Standard",
        node_type="control",
        content_markdown="# Data Encryption\nAES-256 for all databases per [[soc2-cc6-6]].",
    )

    # Links:
    # mfa-policy -> cloud-security
    # cloud-security -> encryption-standard
    # Backlink: mfa-policy references soc2-cc6-1
    db.insert_knowledge_link(
        link_id=f"lnk_{uuid.uuid4().hex[:8]}",
        source_node_id=node1_id,
        target_slug="cloud-security",
        link_text="Cloud Security Baseline",
        context_snippet="Cross-references [[cloud-security]].",
    )
    db.insert_knowledge_link(
        link_id=f"lnk_{uuid.uuid4().hex[:8]}",
        source_node_id=node2_id,
        target_slug="encryption-standard",
        link_text="Data Encryption Standard",
        context_snippet="Links to [[encryption-standard]].",
    )

    return {
        "db": db,
        "store": store,
        "doc_id": doc_id,
        "framework_id": fw_id,
        "chunks": chunks,
    }


# -----------------------------------------------------------------------------
# Tool 1 Tests: list_documents
# -----------------------------------------------------------------------------

def test_list_documents(mcp_test_env):
    res = list_documents(limit=10, offset=0)
    assert res.total_count == 1
    assert len(res.documents) == 1
    doc = res.documents[0]
    assert doc.id == mcp_test_env["doc_id"]
    assert doc.filename == "Corporate_Security_Policy_2026.pdf"
    assert doc.mime_type == "application/pdf"
    assert doc.file_size_bytes > 0


def test_list_documents_invalid_args(mcp_test_env):
    with pytest.raises(ValueError, match="between 1 and 100"):
        list_documents(limit=0)
    with pytest.raises(ValueError, match="between 1 and 100"):
        list_documents(limit=101)
    with pytest.raises(ValueError, match="non-negative"):
        list_documents(offset=-1)


# -----------------------------------------------------------------------------
# Tool 2 Tests: search_documents
# -----------------------------------------------------------------------------

def test_search_documents(mcp_test_env):
    res = search_documents(query="multi-factor authentication FIDO2", top_k=3)
    assert res.query == "multi-factor authentication FIDO2"
    assert res.total_results > 0
    top_hit = res.results[0]
    assert "MFA" in top_hit.content or "authentication" in top_hit.content
    assert top_hit.rrf_score > 0.0
    assert top_hit.document_id == mcp_test_env["doc_id"]


def test_search_documents_with_document_filter(mcp_test_env):
    res = search_documents(
        query="AES-256 data encryption",
        top_k=2,
        document_id=mcp_test_env["doc_id"],
    )
    assert res.total_results > 0
    for r in res.results:
        assert r.document_id == mcp_test_env["doc_id"]


def test_search_documents_unknown_document_id(mcp_test_env):
    with pytest.raises(ValueError, match="Document ID 'non_existent_doc' not found"):
        search_documents(query="test", document_id="non_existent_doc")


def test_search_documents_invalid_query():
    with pytest.raises(ValueError, match="at least 2 non-whitespace characters"):
        search_documents(query=" ")


# -----------------------------------------------------------------------------
# Tool 3 Tests: get_document_metadata
# -----------------------------------------------------------------------------

def test_get_document_metadata(mcp_test_env):
    meta = get_document_metadata(document_id=mcp_test_env["doc_id"])
    assert meta.id == mcp_test_env["doc_id"]
    assert meta.filename == "Corporate_Security_Policy_2026.pdf"
    assert meta.page_count == 3
    assert meta.total_chunks > 0
    assert len(meta.sections) > 0
    assert meta.metadata_json.get("department") == "Security & Compliance"


def test_get_document_metadata_unknown_id(mcp_test_env):
    with pytest.raises(ValueError, match="Document ID 'unknown_doc_xyz' not found"):
        get_document_metadata(document_id="unknown_doc_xyz")


# -----------------------------------------------------------------------------
# Tool 4 Tests: get_citation
# -----------------------------------------------------------------------------

def test_get_citation(mcp_test_env):
    chunk = mcp_test_env["chunks"][0]
    cit = get_citation(chunk_id=chunk.id, include_surrounding_context=True)
    assert cit.chunk_id == chunk.id
    assert cit.document_id == mcp_test_env["doc_id"]
    assert cit.exact_text == chunk.content
    # Verify cryptographic integrity hash
    expected_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
    assert cit.sha256_verification == expected_hash
    # Next context should be present if multiple chunks exist
    if len(mcp_test_env["chunks"]) > 1:
        assert cit.next_context is not None


def test_get_citation_unknown_chunk_id(mcp_test_env):
    with pytest.raises(ValueError, match="Chunk ID 'non_existent_chunk' not found"):
        get_citation(chunk_id="non_existent_chunk")


# -----------------------------------------------------------------------------
# Tool 5 Tests: evaluate_compliance
# -----------------------------------------------------------------------------

def test_evaluate_compliance_framework(mcp_test_env):
    res = evaluate_compliance(framework_id="SOC2")
    assert res.framework_name == "SOC2"
    assert res.total_requirements == 3
    assert len(res.findings) == 3

    # Check CC6.1 (MFA)
    cc61 = next(f for f in res.findings if f.requirement_code == "CC6.1")
    assert cc61.status in ("COVERED", "PARTIALLY_COVERED")
    assert cc61.evidence is not None
    assert "MFA" in cc61.evidence.quote or "authentication" in cc61.evidence.quote

    # Check CC7.1 (Penetration testing - not mentioned in doc)
    cc71 = next(f for f in res.findings if f.requirement_code == "CC7.1")
    assert cc71.status == "MISSING"
    assert cc71.evidence is None
    assert cc71.gap is not None

    # Verify coverage summary
    summary = res.coverage_summary
    assert summary.total == 3
    assert summary.missing == 1
    assert summary.covered + summary.partially_covered == 2


def test_evaluate_compliance_single_requirement(mcp_test_env):
    res = evaluate_compliance(framework_id="SOC2", requirement_id="CC6.6")
    assert res.total_requirements == 1
    assert res.findings[0].requirement_code == "CC6.6"
    assert res.findings[0].evidence is not None
    assert "AES-256" in res.findings[0].evidence.quote or "encrypted" in res.findings[0].evidence.quote


def test_evaluate_compliance_unknown_framework(mcp_test_env):
    with pytest.raises(ValueError, match="framework 'UNKNOWN_FW' not found"):
        evaluate_compliance(framework_id="UNKNOWN_FW")


# -----------------------------------------------------------------------------
# Tool 6 Tests: gap_analysis
# -----------------------------------------------------------------------------

def test_gap_analysis(mcp_test_env):
    res = gap_analysis(framework_id="SOC2", severity_filter="All")
    assert res.framework_name == "SOC2"
    assert res.total_gaps >= 1  # CC7.1 is MISSING, so at least 1 gap
    assert any(g.requirement_code == "CC7.1" for g in res.remediation_roadmap)

    # Check prioritization: priority_rank must be 1-based sequential
    for idx, gap in enumerate(res.remediation_roadmap):
        assert gap.priority_rank == idx + 1
        assert gap.current_status in ("PARTIALLY_COVERED", "MISSING")
        assert gap.estimated_effort_days > 0


def test_gap_analysis_invalid_severity(mcp_test_env):
    with pytest.raises(ValueError, match="Invalid severity_filter"):
        gap_analysis(framework_id="SOC2", severity_filter="Extreme")


# -----------------------------------------------------------------------------
# Tool 7 Tests: get_related_knowledge
# -----------------------------------------------------------------------------

def test_get_related_knowledge_depth_1(mcp_test_env):
    res = get_related_knowledge(node_id_or_slug="mfa-policy", depth=1)
    assert res.root_node.slug == "mfa-policy"
    assert res.root_node.title == "Multi-Factor Authentication Standard"
    assert len(res.outgoing_links) == 1
    assert res.outgoing_links[0].target_slug == "cloud-security"
    # Referenced requirements in body markdown: [[soc2-cc6-1]]
    assert "soc2-cc6-1" in res.related_requirements


def test_get_related_knowledge_depth_2_multihop(mcp_test_env):
    res = get_related_knowledge(node_id_or_slug="mfa-policy", depth=2)
    assert res.depth == 2
    # Depth 2 should find cloud-security (hop 1) AND encryption-standard (hop 2 via cloud-security)
    target_slugs = [lnk.target_slug for lnk in res.outgoing_links]
    assert "cloud-security" in target_slugs
    assert "encryption-standard" in target_slugs


def test_get_related_knowledge_backlinks(mcp_test_env):
    res = get_related_knowledge(node_id_or_slug="cloud-security", depth=1)
    assert res.root_node.slug == "cloud-security"
    # Backlink from mfa-policy
    assert any(b.source_slug == "mfa-policy" for b in res.backlinks)


def test_get_related_knowledge_unknown_node(mcp_test_env):
    with pytest.raises(ValueError, match="Knowledge node 'unknown_slug' not found"):
        get_related_knowledge(node_id_or_slug="unknown_slug")


def test_get_related_knowledge_invalid_depth(mcp_test_env):
    with pytest.raises(ValueError, match="must be either 1 or 2"):
        get_related_knowledge(node_id_or_slug="mfa-policy", depth=3)

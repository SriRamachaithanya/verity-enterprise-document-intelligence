import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from src.indexing.chunker import DocumentChunker
from src.indexing.embedding_service import get_embedding_service
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore


@pytest.fixture
def mcp_stdio_setup(tmp_path):
    """
    Seeds an isolated SQLite database and FAISS index for STDIO subprocess testing.
    """
    db_path = tmp_path / "stdio_test.db"
    faiss_dir = tmp_path / "stdio_faiss"

    db = DatabaseManager(db_path=db_path)
    store = FAISSVectorStore(index_dir=faiss_dir)
    embed_svc = get_embedding_service()

    # 1. Ingest synthetic document
    doc_id = "doc_stdio_sec_01"
    doc_text = (
        "Section 1.0 Overview\n"
        "Corporate enterprise security policy and standards.\n\n"
        "Section 2.1 Multi-Factor Authentication\n"
        "All corporate and production system access mandates multi-factor authentication (MFA) "
        "with FIDO2 hardware tokens or TOTP authenticator applications. Passwords must be at least "
        "16 characters and rotated annually. Engineering personnel must maintain active audit logs "
        "and quarterly review records of authentication events.\n\n"
        "Section 4.3 Data Storage Encryption Standards\n"
        "All customer sensitive and confidential records residing on production relational databases "
        "and storage buckets must be encrypted at rest using NIST-approved AES-256 GCM or ChaCha20-Poly1305. "
        "Cryptographic keys must rotate automatically every 90 days via AWS KMS or HashiCorp Vault."
    )
    meta = DocumentMetadata(
        filename="Security_Policy_STDIO.pdf",
        file_hash=hashlib.sha256(doc_text.encode("utf-8")).hexdigest(),
        mime_type="application/pdf",
        file_size_bytes=len(doc_text.encode("utf-8")),
        page_count=2,
        extra={"author": "DevOps Engineer"},
    )
    db.insert_document(doc_id=doc_id, meta=meta, filepath=str(tmp_path / "doc.pdf"))

    # 2. Chunk and index
    chunker = DocumentChunker(target_tokens=60, overlap_tokens=10)
    extracted = ExtractedDocument(
        metadata=meta,
        elements=[
            ParsedElement(
                text="Section 1.0 Overview\nCorporate enterprise security policy and standards.",
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
    fw_id = "fw_soc2_stdio"
    db.insert_framework(
        framework_id=fw_id,
        name="SOC2",
        version="2026.1",
        description="AICPA SOC 2 Criteria",
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC6.1",
        title="Logical Access and Authentication Controls",
        description="Logical access software, MFA, and credentials.",
        category="Access Control",
        severity_level=1,
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC6.6",
        title="Encryption of Sensitive Data at Rest",
        description="Data encryption using AES-256.",
        category="Cryptography",
        severity_level=2,
    )
    db.insert_requirement(
        req_id=f"req_{uuid.uuid4().hex[:8]}",
        framework_id=fw_id,
        req_code="CC7.1",
        title="Vulnerability Assessment and Penetration Testing",
        description="Conduct automated vulnerability scans and external pen tests.",
        category="Vulnerability Management",
        severity_level=2,
    )

    # 4. Seed knowledge graph notes and links
    n1_id = "kn_mfa_stdio"
    db.insert_knowledge_node(
        node_id=n1_id,
        slug="mfa-policy",
        title="Multi-Factor Authentication Standard",
        node_type="control",
        content_markdown="# MFA Standard\nMandates hardware tokens per [[soc2-cc6-1]]. References [[cloud-security]].",
    )
    n2_id = "kn_cloud_stdio"
    db.insert_knowledge_node(
        node_id=n2_id,
        slug="cloud-security",
        title="Cloud Infrastructure Security Baseline",
        node_type="document",
        content_markdown="# Cloud Baseline\nAWS accounts. Links to [[encryption-standard]].",
    )
    n3_id = "kn_enc_stdio"
    db.insert_knowledge_node(
        node_id=n3_id,
        slug="encryption-standard",
        title="Data Storage Encryption Standard",
        node_type="control",
        content_markdown="# Data Encryption\nAES-256 per [[soc2-cc6-6]].",
    )

    db.insert_knowledge_link(
        link_id=f"lnk_{uuid.uuid4().hex[:8]}",
        source_node_id=n1_id,
        target_slug="cloud-security",
        link_text="Cloud Security",
        context_snippet="References [[cloud-security]].",
    )
    db.insert_knowledge_link(
        link_id=f"lnk_{uuid.uuid4().hex[:8]}",
        source_node_id=n2_id,
        target_slug="encryption-standard",
        link_text="Data Encryption",
        context_snippet="Links to [[encryption-standard]].",
    )

    # Ensure store is flushed to disk for child process
    store.save()

    return {
        "db_path": str(db_path),
        "faiss_dir": str(faiss_dir),
        "doc_id": doc_id,
        "chunks": chunks,
    }


def _get_server_params(setup_data: dict) -> StdioServerParameters:
    """Construct StdioServerParameters pointing to the isolated test storage."""
    env = {
        **os.environ,
        "VERITY_DB_PATH": setup_data["db_path"],
        "VERITY_FAISS_DIR": setup_data["faiss_dir"],
        "PYTHONUNBUFFERED": "1",
    }
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        env=env,
        cwd=str(Path.cwd()),
    )


# -----------------------------------------------------------------------------
# STDIO MCP Protocol Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stdio_handshake_and_tools_list(mcp_stdio_setup):
    """Verify MCP initialization handshake and tools/list exposes all 7 tools over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init_res = await session.initialize()
        assert init_res.server_info.name == "verity-compliance-server"

        tools_res = await session.list_tools()
        tool_names = [t.name for t in tools_res.tools]
        expected_tools = [
            "list_documents",
            "search_documents",
            "get_document_metadata",
            "get_citation",
            "evaluate_compliance",
            "gap_analysis",
            "get_related_knowledge",
        ]
        for exp in expected_tools:
            assert exp in tool_names, f"Tool '{exp}' missing from tools/list"
        assert len(tool_names) == 7


@pytest.mark.asyncio
async def test_stdio_list_documents(mcp_stdio_setup):
    """Test tools/call 'list_documents' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        # Valid call
        res = await session.call_tool("list_documents", {"limit": 10, "offset": 0})
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["total_count"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["id"] == mcp_stdio_setup["doc_id"]
        assert data["documents"][0]["filename"] == "Security_Policy_STDIO.pdf"


@pytest.mark.asyncio
async def test_stdio_list_documents_invalid_args(mcp_stdio_setup):
    """Test tools/call 'list_documents' error handling over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool("list_documents", {"limit": 0, "offset": 0})
        assert res.is_error
        assert "between 1 and 100" in res.content[0].text


@pytest.mark.asyncio
async def test_stdio_search_documents(mcp_stdio_setup):
    """Test tools/call 'search_documents' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool(
            "search_documents",
            {"query": "FIDO2 hardware tokens multi-factor authentication", "top_k": 3},
        )
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["total_results"] > 0
        top = data["results"][0]
        assert top["document_id"] == mcp_stdio_setup["doc_id"]
        assert top["rrf_score"] > 0.0
        assert "MFA" in top["content"] or "authentication" in top["content"]


@pytest.mark.asyncio
async def test_stdio_search_documents_unknown_doc_error(mcp_stdio_setup):
    """Test tools/call 'search_documents' with unknown document ID."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool(
            "search_documents",
            {"query": "AES-256", "document_id": "non_existent_doc_id"},
        )
        assert res.is_error
        assert "not found" in res.content[0].text


@pytest.mark.asyncio
async def test_stdio_get_document_metadata(mcp_stdio_setup):
    """Test tools/call 'get_document_metadata' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool(
            "get_document_metadata",
            {"document_id": mcp_stdio_setup["doc_id"]},
        )
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["id"] == mcp_stdio_setup["doc_id"]
        assert data["filename"] == "Security_Policy_STDIO.pdf"
        assert data["page_count"] == 2
        assert data["total_chunks"] > 0
        assert len(data["sections"]) > 0


@pytest.mark.asyncio
async def test_stdio_get_document_metadata_unknown(mcp_stdio_setup):
    """Test tools/call 'get_document_metadata' with unknown ID."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool("get_document_metadata", {"document_id": "unknown_id_xyz"})
        assert res.is_error
        assert "not found" in res.content[0].text


@pytest.mark.asyncio
async def test_stdio_get_citation(mcp_stdio_setup):
    """Test tools/call 'get_citation' with SHA-256 verification and surrounding context."""
    chunk = mcp_stdio_setup["chunks"][0]
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool(
            "get_citation",
            {"chunk_id": chunk.id, "include_surrounding_context": True},
        )
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["chunk_id"] == chunk.id
        assert data["exact_text"] == chunk.content
        expected_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        assert data["sha256_verification"] == expected_hash


@pytest.mark.asyncio
async def test_stdio_get_citation_unknown(mcp_stdio_setup):
    """Test tools/call 'get_citation' with unknown chunk ID."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool("get_citation", {"chunk_id": "unknown_chunk_999"})
        assert res.is_error
        assert "not found" in res.content[0].text


@pytest.mark.asyncio
async def test_stdio_evaluate_compliance(mcp_stdio_setup):
    """Test tools/call 'evaluate_compliance' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool("evaluate_compliance", {"framework_id": "SOC2"})
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["framework_name"] == "SOC2"
        assert data["total_requirements"] == 3

        findings = {f["requirement_code"]: f for f in data["findings"]}
        assert findings["CC6.1"]["status"] in ("COVERED", "PARTIALLY_COVERED")
        assert findings["CC6.1"]["evidence"] is not None

        assert findings["CC6.6"]["status"] in ("COVERED", "PARTIALLY_COVERED")
        assert findings["CC6.6"]["evidence"] is not None

        assert findings["CC7.1"]["status"] == "MISSING"
        assert findings["CC7.1"]["evidence"] is None


@pytest.mark.asyncio
async def test_stdio_gap_analysis(mcp_stdio_setup):
    """Test tools/call 'gap_analysis' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        res = await session.call_tool("gap_analysis", {"framework_id": "SOC2", "severity_filter": "All"})
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["framework_name"] == "SOC2"
        assert data["total_gaps"] >= 1
        for idx, g in enumerate(data["remediation_roadmap"]):
            assert g["priority_rank"] == idx + 1
            assert g["current_status"] in ("PARTIALLY_COVERED", "MISSING")
            assert g["estimated_effort_days"] > 0


@pytest.mark.asyncio
async def test_stdio_get_related_knowledge(mcp_stdio_setup):
    """Test tools/call 'get_related_knowledge' over STDIO."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        # Depth 1
        res1 = await session.call_tool("get_related_knowledge", {"node_id_or_slug": "mfa-policy", "depth": 1})
        assert not res1.is_error
        d1 = json.loads(res1.content[0].text)
        assert d1["root_node"]["slug"] == "mfa-policy"
        assert any(lnk["target_slug"] == "cloud-security" for lnk in d1["outgoing_links"])
        assert "soc2-cc6-1" in d1["related_requirements"]

        # Depth 2 multi-hop
        res2 = await session.call_tool("get_related_knowledge", {"node_id_or_slug": "mfa-policy", "depth": 2})
        assert not res2.is_error
        d2 = json.loads(res2.content[0].text)
        targets = [lnk["target_slug"] for lnk in d2["outgoing_links"]]
        assert "cloud-security" in targets
        assert "encryption-standard" in targets


@pytest.mark.asyncio
async def test_stdio_server_shutdown(mcp_stdio_setup):
    """Verify clean shutdown and connection teardown."""
    params = _get_server_params(mcp_stdio_setup)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init_res = await session.initialize()
        assert init_res.server_info.name == "verity-compliance-server"
    # Exited context cleanly; child process terminated
    assert True

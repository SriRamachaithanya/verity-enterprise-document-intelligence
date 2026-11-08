"""
VERITY Phase 4 — Comprehensive End-to-End Integration Test Suite
Validates all 12 core workflows across Authentication, Ingestion, Hybrid Search,
SSE Chat Streaming, Citation Verification, Compliance, Knowledge Graph, and Remediation.
"""

import hashlib
import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import APIConfig, set_api_config
from src.api.dependencies import reset_api_dependencies, set_api_dependencies
from src.compliance.engine import ComplianceIntelligenceEngine
from src.indexing.chunker import DocumentChunker
from src.indexing.embedding_service import get_embedding_service
from src.indexing.hybrid_search import HybridSearchEngine
from src.indexing.ingestion_pipeline import IngestionPipeline
from src.knowledge.graph_service import KnowledgeGraphService
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore
from src.storage.seed_data import seed_baseline_data_if_empty


@pytest.fixture
def e2e_env(tmp_path):
    """Initializes an isolated end-to-end environment with fresh storage and seeded frameworks."""
    db_path = tmp_path / "e2e_verity.db"
    faiss_dir = tmp_path / "e2e_faiss"
    upload_dir = tmp_path / "e2e_uploads"
    quarantine_dir = tmp_path / "e2e_quarantine"

    upload_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    faiss_dir.mkdir(parents=True, exist_ok=True)

    config = APIConfig(
        app_name="VERITY E2E Test Suite",
        version="2.0.0-e2e",
        environment="test",
        debug=True,
        db_path=db_path,
        faiss_dir=faiss_dir,
        upload_dir=upload_dir,
        quarantine_dir=quarantine_dir,
        auth_disabled=False,
        admin_api_key="e2e-admin-secret-key",
        auditor_api_key="e2e-auditor-secret-key",
        user_api_key="e2e-user-secret-key",
        max_upload_size_bytes=10 * 1024 * 1024,
        agent_timeout_seconds=60.0,
    )
    set_api_config(config)

    db = DatabaseManager(db_path=db_path)
    seed_baseline_data_if_empty(db)

    store = FAISSVectorStore(index_dir=faiss_dir)
    embed_svc = get_embedding_service()
    hybrid = HybridSearchEngine(db_manager=db, vector_store=store, embedding_service=embed_svc)
    comp_engine = ComplianceIntelligenceEngine(db=db, hybrid_engine=hybrid)
    know_svc = KnowledgeGraphService(db=db)
    ingestion = IngestionPipeline(
        db_manager=db,
        vector_store=store,
        embedding_service=embed_svc,
        upload_dir=upload_dir,
    )

    set_api_dependencies(
        db=db,
        vector_store=store,
        embedding_service=embed_svc,
        hybrid_search=hybrid,
        compliance_engine=comp_engine,
        knowledge_service=know_svc,
        ingestion_pipeline=ingestion,
    )

    app = create_app(config)
    client = TestClient(app)

    yield {
        "client": client,
        "config": config,
        "db": db,
        "store": store,
        "hybrid": hybrid,
        "ingestion": ingestion,
    }

    reset_api_dependencies()


class TestPhase4E2EIntegration:
    """End-to-end test suite executing the 12 Stage 3 verification workflows."""

    # -------------------------------------------------------------------------
    # 1. Application Startup & Diagnostics
    # -------------------------------------------------------------------------
    def test_workflow_01_startup_and_health(self, e2e_env):
        client: TestClient = e2e_env["client"]

        # Health liveness check
        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        health_data = resp_health.json()
        assert health_data["status"] == "healthy"
        assert "VERITY" in health_data["service"]

        # Readiness probe check
        resp_ready = client.get("/ready")
        assert resp_ready.status_code == 200
        ready_data = resp_ready.json()
        assert ready_data["status"] in ("ready", "degraded")
        assert "sqlite" in ready_data["components"]
        assert ready_data["components"]["sqlite"]["status"] == "healthy"
        assert "faiss" in ready_data["components"]

    # -------------------------------------------------------------------------
    # 2. Authentication & Role Permissions (RBAC)
    # -------------------------------------------------------------------------
    def test_workflow_02_authentication_and_rbac(self, e2e_env):
        client: TestClient = e2e_env["client"]

        # Missing header -> 401 Unauthorized
        resp_no_key = client.get("/api/v1/documents")
        assert resp_no_key.status_code == 401
        err_msg = resp_no_key.json().get("error", {}).get("message", "") or resp_no_key.json().get("detail", "")
        assert "authentication" in err_msg.lower() or "api key" in err_msg.lower()

        # Invalid header -> 401 Unauthorized
        resp_invalid_key = client.get("/api/v1/documents", headers={"X-API-Key": "invalid-key"})
        assert resp_invalid_key.status_code == 401

        # User role: can search
        resp_user_search = client.post(
            "/api/v1/search",
            headers={"X-API-Key": "e2e-user-secret-key"},
            json={"query": "access control", "top_k": 3},
        )
        assert resp_user_search.status_code == 200

        # User role: cannot delete documents (requires admin -> 403 Forbidden)
        resp_user_del = client.delete(
            "/api/v1/documents/doc_nonexistent",
            headers={"X-API-Key": "e2e-user-secret-key"},
        )
        assert resp_user_del.status_code == 403

        # Auditor role: can audit compliance
        resp_auditor_comp = client.post(
            "/api/v1/compliance/evaluate",
            headers={"X-API-Key": "e2e-auditor-secret-key"},
            json={"framework_id": "SOC2"},
        )
        assert resp_auditor_comp.status_code == 200

        # Auditor role: cannot delete documents (requires admin -> 403 Forbidden)
        resp_auditor_del = client.delete(
            "/api/v1/documents/doc_nonexistent",
            headers={"X-API-Key": "e2e-auditor-secret-key"},
        )
        assert resp_auditor_del.status_code == 403

        # Admin role: full permissions
        resp_admin_list = client.get(
            "/api/v1/documents",
            headers={"X-API-Key": "e2e-admin-secret-key"},
        )
        assert resp_admin_list.status_code == 200

    # -------------------------------------------------------------------------
    # 3. Document Ingestion (TXT, PDF, DOCX) & Malware Scanning
    # -------------------------------------------------------------------------
    def test_workflow_03_document_uploads(self, e2e_env):
        client: TestClient = e2e_env["client"]
        headers = {"X-API-Key": "e2e-admin-secret-key"}

        # A. Synthetic TXT Upload (Identity Policy)
        txt_content = (
            "Enterprise Access Control Standard 2026\n\n"
            "Section 1. Logical Access & MFA\n"
            "Multi-factor authentication (MFA) is strictly required for all administrative "
            "and production access. FIDO2 security keys or authenticator apps are mandatory.\n\n"
            "Section 2. Key Management\n"
            "Production databases must utilize AES-256 GCM encryption at rest with annual key rotation."
        ).encode("utf-8")

        resp_txt = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("Access_Policy.txt", io.BytesIO(txt_content), "text/plain")},
        )
        assert resp_txt.status_code == 201
        data_txt = resp_txt.json()
        assert data_txt["chunks_count"] >= 1
        assert data_txt["malware_scan"]["is_clean"] is True
        assert data_txt["status"] == "ingested"

        # B. Duplicate Ingestion Deduplication Check
        resp_dup = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("Access_Policy.txt", io.BytesIO(txt_content), "text/plain")},
        )
        assert resp_dup.status_code in (200, 201)
        assert resp_dup.json()["status"] == "already_exists"

        # C. Malware / EICAR Fail-Closed Check
        eicar_string = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        resp_eicar = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("malware_test.txt", io.BytesIO(eicar_string), "text/plain")},
        )
        assert resp_eicar.status_code == 400
        eicar_err = resp_eicar.json().get("error", {}).get("message", "") or resp_eicar.json().get("detail", "")
        assert any(term in eicar_err.lower() for term in ("malicious", "eicar", "quarantined", "malware"))

    # -------------------------------------------------------------------------
    # 4. Document Listing, Inspection & Deletion
    # -------------------------------------------------------------------------
    def test_workflow_04_document_lifecycle(self, e2e_env):
        client: TestClient = e2e_env["client"]
        admin_headers = {"X-API-Key": "e2e-admin-secret-key"}

        # Ingest a disposable document
        content = b"Temporary audit log record for deletion test.\nContains retention markers."
        resp_up = client.post(
            "/api/v1/documents/upload",
            headers=admin_headers,
            files={"file": ("Temporary_Doc.txt", io.BytesIO(content), "text/plain")},
        )
        doc_id = resp_up.json()["document_id"]

        # List documents
        resp_list = client.get("/api/v1/documents", headers=admin_headers)
        assert resp_list.status_code == 200
        list_data = resp_list.json()
        assert any(d["id"] == doc_id for d in list_data["documents"])

        # Inspect details
        resp_detail = client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
        assert resp_detail.status_code == 200
        assert resp_detail.json()["filename"] == "Temporary_Doc.txt"

        # Admin delete
        resp_del = client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
        assert resp_del.status_code == 200
        assert resp_del.json()["status"] == "deleted"

        # Verify not found after deletion
        resp_check = client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
        assert resp_check.status_code == 404

    # -------------------------------------------------------------------------
    # 5. Hybrid Search (FAISS + FTS5 RRF Fusion)
    # -------------------------------------------------------------------------
    def test_workflow_05_hybrid_search(self, e2e_env):
        client: TestClient = e2e_env["client"]
        admin_headers = {"X-API-Key": "e2e-admin-secret-key"}

        # Seed knowledge content
        content = (
            "Cryptographic Storage Guidelines\n"
            "All sensitive RDS instances are encrypted using AES-256 GCM algorithms.\n"
            "Key management is orchestrated through KMS customer-managed keys."
        ).encode("utf-8")
        client.post(
            "/api/v1/documents/upload",
            headers=admin_headers,
            files={"file": ("Crypto_Guidelines.txt", io.BytesIO(content), "text/plain")},
        )

        # Run hybrid query
        resp_search = client.post(
            "/api/v1/search",
            headers=admin_headers,
            json={"query": "AES-256 KMS cryptographic storage", "top_k": 3},
        )
        assert resp_search.status_code == 200
        search_data = resp_search.json()
        assert len(search_data["results"]) >= 1
        top_result = search_data["results"][0]
        assert top_result["rrf_score"] > 0
        assert "AES-256" in top_result["content"]
        assert top_result["locator"] != ""

    # -------------------------------------------------------------------------
    # 6. AI Assistant & SSE Streaming
    # -------------------------------------------------------------------------
    def test_workflow_06_chat_and_sse_streaming(self, e2e_env):
        client: TestClient = e2e_env["client"]
        headers = {"X-API-Key": "e2e-admin-secret-key"}

        # Synchronous Chat endpoint
        resp_chat = client.post(
            "/api/v1/chat",
            headers=headers,
            json={"query": "What are our encryption requirements?"},
        )
        assert resp_chat.status_code == 200
        chat_data = resp_chat.json()
        assert chat_data["answer"] != ""
        assert chat_data["intent"] in (
            "compliance_evaluation",
            "document_qa",
            "gap_analysis",
            "general_inquiry",
            "unknown",
        )

        # SSE Streaming Chat endpoint
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers=headers,
            json={"query": "Evaluate multi-factor authentication compliance"},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            events = []
            for line in response.iter_lines():
                if line:
                    events.append(line)

            assert len(events) > 0
            # Ensure stream emitted structured event types
            event_text = "\n".join(events)
            assert "event:" in event_text
            assert "data:" in event_text

    # -------------------------------------------------------------------------
    # 7. Citation Verification
    # -------------------------------------------------------------------------
    def test_workflow_07_citation_grounding(self, e2e_env):
        client: TestClient = e2e_env["client"]
        headers = {"X-API-Key": "e2e-admin-secret-key"}

        resp_chat = client.post(
            "/api/v1/chat",
            headers=headers,
            json={"query": "What are the rules for password and MFA access?"},
        )
        assert resp_chat.status_code == 200
        citations = resp_chat.json().get("citations", [])
        # If citations exist, verify they reference valid chunks and locators
        for cite in citations:
            assert cite["chunk_id"] != ""
            assert cite["locator"] != ""
            assert cite["verified"] is True

    # -------------------------------------------------------------------------
    # 8. Compliance Evaluation
    # -------------------------------------------------------------------------
    def test_workflow_08_compliance_evaluation(self, e2e_env):
        client: TestClient = e2e_env["client"]
        auditor_headers = {"X-API-Key": "e2e-auditor-secret-key"}

        # Evaluate SOC2
        resp_eval = client.post(
            "/api/v1/compliance/evaluate",
            headers=auditor_headers,
            json={"framework_id": "SOC2"},
        )
        assert resp_eval.status_code == 200
        data = resp_eval.json()
        assert data["framework_id"] == "SOC2"
        assert data["total_requirements"] == 5
        assert "coverage_summary" in data
        assert data["coverage_summary"]["total"] == 5
        assert len(data["findings"]) == 5

    # -------------------------------------------------------------------------
    # 9. Gap Analysis
    # -------------------------------------------------------------------------
    def test_workflow_09_gap_analysis(self, e2e_env):
        client: TestClient = e2e_env["client"]
        auditor_headers = {"X-API-Key": "e2e-auditor-secret-key"}

        resp_gap = client.post(
            "/api/v1/compliance/gap-analysis",
            headers=auditor_headers,
            json={"framework_id": "SOC2"},
        )
        assert resp_gap.status_code == 200
        gap_data = resp_gap.json()
        assert gap_data["framework_id"] == "SOC2"
        assert gap_data["total_gaps"] >= 0
        assert "remediation_roadmap" in gap_data

    # -------------------------------------------------------------------------
    # 10. Historical Assessment Comparison
    # -------------------------------------------------------------------------
    def test_workflow_10_historical_comparison(self, e2e_env):
        client: TestClient = e2e_env["client"]
        auditor_headers = {"X-API-Key": "e2e-auditor-secret-key"}

        # Run an initial evaluation to create history
        client.post(
            "/api/v1/compliance/evaluate",
            headers=auditor_headers,
            json={"framework_id": "SOC2"},
        )

        resp_hist = client.get(
            "/api/v1/compliance/history",
            headers=auditor_headers,
            params={"framework_id": "SOC2"},
        )
        assert resp_hist.status_code == 200
        hist_data = resp_hist.json()
        assert hist_data["framework_id"] == "SOC2"
        assert "diffs" in hist_data

    # -------------------------------------------------------------------------
    # 11. Knowledge Graph Traversal
    # -------------------------------------------------------------------------
    def test_workflow_11_knowledge_traversal(self, e2e_env):
        client: TestClient = e2e_env["client"]
        headers = {"X-API-Key": "e2e-user-secret-key"}

        # Query node
        resp_node = client.get(
            "/api/v1/knowledge/logical-access-control",
            headers=headers,
            params={"depth": 2},
        )
        assert resp_node.status_code == 200
        node_data = resp_node.json()
        assert node_data["root_node"]["slug"] == "logical-access-control"
        assert node_data["depth"] == 2

        # Query backlinks
        resp_backlinks = client.get(
            "/api/v1/knowledge/logical-access-control/backlinks",
            headers=headers,
        )
        assert resp_backlinks.status_code == 200
        assert "backlinks" in resp_backlinks.json()

    # -------------------------------------------------------------------------
    # 12. Remediation Roadmap
    # -------------------------------------------------------------------------
    def test_workflow_12_remediation_roadmap(self, e2e_env):
        client: TestClient = e2e_env["client"]
        auditor_headers = {"X-API-Key": "e2e-auditor-secret-key"}

        resp_gap = client.post(
            "/api/v1/compliance/gap-analysis",
            headers=auditor_headers,
            json={"framework_id": "SOC2"},
        )
        assert resp_gap.status_code == 200
        roadmap = resp_gap.json()["remediation_roadmap"]
        for task in roadmap:
            assert "requirement_code" in task
            assert "severity" in task
            assert "estimated_effort_days" in task
            assert task["estimated_effort_days"] > 0
            assert task["remediation_recommendation"] != ""

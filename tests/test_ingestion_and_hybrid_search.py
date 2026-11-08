from pathlib import Path

import pymupdf
import pytest
from docx import Document

from src.indexing.hybrid_search import HybridSearchEngine
from src.indexing.ingestion_pipeline import IngestionPipeline
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore


@pytest.fixture
def env(tmp_path: Path, session_embedding_service):
    """Setup isolated DatabaseManager, FAISSVectorStore, and IngestionPipeline."""
    db_file = tmp_path / "test_verity.db"
    faiss_dir = tmp_path / "faiss_data"
    upload_dir = tmp_path / "uploads"

    db = DatabaseManager(db_file)
    vector_store = FAISSVectorStore(faiss_dir)
    embedding_service = session_embedding_service

    pipeline = IngestionPipeline(
        db_manager=db,
        vector_store=vector_store,
        embedding_service=embedding_service,
        upload_dir=upload_dir,
    )

    search_engine = HybridSearchEngine(
        db_manager=db,
        vector_store=vector_store,
        embedding_service=embedding_service,
    )

    return {
        "db": db,
        "vector_store": vector_store,
        "pipeline": pipeline,
        "search_engine": search_engine,
        "tmp_path": tmp_path,
    }


def create_synthetic_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Section 1.0: Cloud Infrastructure Access\n\n"
        "To comply with SOC 2 CC6.1, engineers must utilize hardware security keys.\n"
        "Root accounts are disabled for day-to-day operations.",
    )
    doc.save(str(path))
    doc.close()
    return path


def create_synthetic_docx(path: Path) -> Path:
    doc = Document()
    doc.add_heading("Section 2.0: Cryptographic Controls", level=1)
    doc.add_paragraph(
        "In accordance with ISO 27001 A.12.3.1, sensitive corporate records must be encrypted "
        "at rest using AES-256 GCM envelope encryption. Key rotation occurs automatically."
    )
    doc.save(str(path))
    return path


def create_synthetic_txt(path: Path) -> Path:
    path.write_text(
        "# Section 3.0: Data Retention and Disposal\n\n"
        "Customer personally identifiable information (PII) must be purged within 30 days "
        "upon contract termination to meet GDPR Article 17 requirements.",
        encoding="utf-8",
    )
    return path


def test_end_to_end_ingestion_and_deduplication(env):
    pipeline = env["pipeline"]
    vector_store = env["vector_store"]
    db = env["db"]

    pdf_file = create_synthetic_pdf(env["tmp_path"] / "policy.pdf")

    # 1. Ingest document first time
    res1 = pipeline.ingest_document(pdf_file)
    assert res1["status"] == "ingested"
    assert res1["chunks_count"] >= 1
    total_vectors = vector_store.get_total_vectors()
    assert total_vectors >= 1
    assert db.count_documents() == 1

    # 2. Ingest IDENTICAL document again -> Must detect duplicate by SHA-256
    res2 = pipeline.ingest_document(pdf_file)
    assert res2["status"] == "already_exists"
    assert res2["document"]["id"] == res1["document"]["id"]

    # Must NOT increase FAISS vectors or SQLite documents
    assert vector_store.get_total_vectors() == total_vectors
    assert db.count_documents() == 1


def test_hybrid_search_exact_regulation_code(env):
    pipeline = env["pipeline"]
    search_engine = env["search_engine"]

    pdf_path = create_synthetic_pdf(env["tmp_path"] / "access_policy.pdf")
    docx_path = create_synthetic_docx(env["tmp_path"] / "crypto_policy.docx")
    txt_path = create_synthetic_txt(env["tmp_path"] / "retention_policy.txt")

    pipeline.ingest_document(pdf_path)
    pipeline.ingest_document(docx_path)
    pipeline.ingest_document(txt_path)

    # 1. Exact Regulation Code Query: 'SOC 2 CC6.1'
    soc2_results = search_engine.search("SOC 2 CC6.1", top_k=3)
    assert len(soc2_results) > 0
    top_hit = soc2_results[0]
    assert "CC6.1" in top_hit.content
    assert top_hit.document_name == "access_policy.pdf"
    assert top_hit.page_number == 1
    assert top_hit.rrf_score > 0.0

    # 2. Exact Regulation Code Query: 'ISO 27001 A.12.3.1'
    iso_results = search_engine.search("ISO 27001 A.12.3.1", top_k=3)
    assert len(iso_results) > 0
    assert "A.12.3.1" in iso_results[0].content
    assert "AES-256" in iso_results[0].content
    assert iso_results[0].document_name == "crypto_policy.docx"

    # 3. Conceptual Query: 'purging customer personal information after contract ends'
    gdpr_results = search_engine.search("purging customer personal information", top_k=3)
    assert len(gdpr_results) > 0
    assert "GDPR" in gdpr_results[0].content or "PII" in gdpr_results[0].content


def test_citation_metadata_preservation(env):
    pipeline = env["pipeline"]
    search_engine = env["search_engine"]

    pdf_path = create_synthetic_pdf(env["tmp_path"] / "compliance_guide.pdf")
    pipeline.ingest_document(pdf_path)

    results = search_engine.search("hardware security keys", top_k=1)
    assert len(results) == 1
    citation = results[0]

    assert citation.document_name == "compliance_guide.pdf"
    assert citation.page_number == 1
    assert "Section 1.0" in citation.section_heading
    assert "Page 1" in citation.locator
    assert "hardware security keys" in citation.content


def test_document_filtering(env):
    pipeline = env["pipeline"]
    search_engine = env["search_engine"]

    pdf_path = create_synthetic_pdf(env["tmp_path"] / "doc_a.pdf")
    docx_path = create_synthetic_docx(env["tmp_path"] / "doc_b.docx")

    res_a = pipeline.ingest_document(pdf_path)
    res_b = pipeline.ingest_document(docx_path)

    doc_a_id = res_a["document"]["id"]
    doc_b_id = res_b["document"]["id"]

    # Filter to doc_a only
    results_a = search_engine.search("security", document_id=doc_a_id)
    for r in results_a:
        assert r.document_id == doc_a_id

    # Filter to doc_b only
    results_b = search_engine.search("security", document_id=doc_b_id)
    for r in results_b:
        assert r.document_id == doc_b_id


def test_deletion_and_faiss_rebuild(env):
    pipeline = env["pipeline"]
    vector_store = env["vector_store"]
    db = env["db"]

    pdf_path = create_synthetic_pdf(env["tmp_path"] / "temp_doc.pdf")
    res = pipeline.ingest_document(pdf_path)
    doc_id = res["document"]["id"]

    assert db.count_documents() == 1
    assert vector_store.get_total_vectors() >= 1

    # Delete document
    deleted = pipeline.delete_document(doc_id)
    assert deleted is True

    # Database and FAISS must both be completely cleared
    assert db.count_documents() == 0
    assert vector_store.get_total_vectors() == 0
    assert len(db.lexical_search("CC6.1")) == 0

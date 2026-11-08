import sqlite3
from pathlib import Path

import pytest

from src.schemas.document import DocumentChunk, DocumentMetadata
from src.storage.db import DatabaseManager


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_verity.db"
    return DatabaseManager(db_file)


def test_db_initialization_and_wal_mode(test_db: DatabaseManager):
    with test_db.session() as conn:
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

        cursor = conn.execute("PRAGMA foreign_keys;")
        fk = cursor.fetchone()[0]
        assert fk == 1


def test_foreign_key_enforcement(test_db: DatabaseManager):
    # Attempting to insert a chunk with non-existent document_id must fail
    orphan_chunk = DocumentChunk(
        id="chk_orphan",
        document_id="non_existent_doc_id",
        chunk_index=0,
        content="This should fail foreign key check",
        token_count=10,
    )
    with pytest.raises(sqlite3.IntegrityError):
        test_db.insert_chunks([orphan_chunk])


def test_fts5_triggers_insert_update_delete(test_db: DatabaseManager):
    # 1. Insert parent document
    doc_meta = DocumentMetadata(
        filename="soc2_policy.pdf",
        file_hash="hash_12345",
        mime_type="application/pdf",
        file_size_bytes=1000,
        page_count=1,
    )
    test_db.insert_document("doc_01", doc_meta, filepath="/tmp/soc2.pdf")

    # 2. Test Trigger on INSERT
    chunk = DocumentChunk(
        id="chk_01",
        document_id="doc_01",
        chunk_index=0,
        content="Logical access requires multi-factor authentication with TOTP.",
        token_count=12,
        section_heading="Section 2: MFA",
    )
    test_db.insert_chunks([chunk])

    # Search in FTS5
    res = test_db.lexical_search("multi-factor authentication")
    assert len(res) == 1
    assert res[0]["chunk_id"] == "chk_01"

    # 3. Test Trigger on UPDATE
    with test_db.session() as conn:
        conn.execute(
            "UPDATE document_chunks SET content = ? WHERE id = ?;",
            ("Updated clause: Biometric authentication required.", "chk_01"),
        )

    # Old term should no longer match
    old_res = test_db.lexical_search("multi-factor")
    assert len(old_res) == 0

    # New term should match
    new_res = test_db.lexical_search("Biometric authentication")
    assert len(new_res) == 1
    assert new_res[0]["chunk_id"] == "chk_01"

    # 4. Test Trigger on DELETE
    with test_db.session() as conn:
        conn.execute("DELETE FROM document_chunks WHERE id = ?;", ("chk_01",))

    del_res = test_db.lexical_search("Biometric")
    assert len(del_res) == 0


def test_framework_scoped_requirement_uniqueness(test_db: DatabaseManager):
    with test_db.session() as conn:
        # Create two distinct frameworks
        conn.execute(
            "INSERT INTO compliance_frameworks (id, name, version) VALUES (?, ?, ?);",
            ("fw_soc2", "SOC 2", "2022"),
        )
        conn.execute(
            "INSERT INTO compliance_frameworks (id, name, version) VALUES (?, ?, ?);",
            ("fw_custom", "Internal Baseline", "1.0"),
        )

        # Both frameworks can have requirement code 'CC6.1'
        conn.execute(
            "INSERT INTO compliance_requirements (id, framework_id, req_code, title, description, category) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            ("req_1", "fw_soc2", "CC6.1", "SOC2 Access Control", "Desc", "Access"),
        )
        conn.execute(
            "INSERT INTO compliance_requirements (id, framework_id, req_code, title, description, category) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            ("req_2", "fw_custom", "CC6.1", "Custom Access Control", "Desc", "Access"),
        )

        # Duplicate req_code in the SAME framework must fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO compliance_requirements (id, framework_id, req_code, title, description, category) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                ("req_3", "fw_soc2", "CC6.1", "Duplicate Code", "Desc", "Access"),
            )


def test_audit_logging(test_db: DatabaseManager):
    row_id = test_db.log_audit_event(
        session_id="sess_abc123",
        event_type="TEST_EVENT",
        step_number=1,
        tool_name="search_documents",
        input_payload={"query": "test query"},
        output_payload={"results_count": 5},
        execution_time_ms=45,
    )
    assert row_id is not None
    assert row_id > 0

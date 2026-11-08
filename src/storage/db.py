import json
import logging
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.schemas.document import DocumentChunk, DocumentMetadata

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(os.getenv("VERITY_DB_PATH") or os.getenv("SQLITE_DB_PATH", "data/sqlite/verity.db"))

SCHEMA_SQL = """
-- 1. Ingested Documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    page_count INTEGER,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- 2. Document Chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    section_heading TEXT DEFAULT 'General',
    locator TEXT DEFAULT '',
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    faiss_index_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_faiss_id ON document_chunks(faiss_index_id);
CREATE INDEX IF NOT EXISTS idx_chunks_locator ON document_chunks(locator);

-- 3. FTS5 Virtual Table for Lexical Search (BM25)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5 (
    chunk_id UNINDEXED,
    document_id UNINDEXED,
    section_heading,
    content,
    tokenize = 'porter unicode61'
);

-- 4. FTS5 Synchronization Triggers (INSERT, UPDATE, DELETE)
CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_insert AFTER INSERT ON document_chunks
BEGIN
    INSERT INTO chunks_fts(chunk_id, document_id, section_heading, content)
    VALUES (new.id, new.document_id, new.section_heading, new.content);
END;

CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_update AFTER UPDATE ON document_chunks
BEGIN
    DELETE FROM chunks_fts WHERE chunk_id = old.id;
    INSERT INTO chunks_fts(chunk_id, document_id, section_heading, content)
    VALUES (new.id, new.document_id, new.section_heading, new.content);
END;

CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_delete AFTER DELETE ON document_chunks
BEGIN
    DELETE FROM chunks_fts WHERE chunk_id = old.id;
END;

-- 5. Compliance Frameworks
CREATE TABLE IF NOT EXISTS compliance_frameworks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Compliance Requirements (UNIQUE within framework, not globally)
CREATE TABLE IF NOT EXISTS compliance_requirements (
    id TEXT PRIMARY KEY,
    framework_id TEXT NOT NULL REFERENCES compliance_frameworks(id) ON DELETE CASCADE,
    req_code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity_level INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_framework_req_code UNIQUE (framework_id, req_code)
);

CREATE INDEX IF NOT EXISTS idx_requirements_framework_code ON compliance_requirements(framework_id, req_code);
CREATE INDEX IF NOT EXISTS idx_requirements_category ON compliance_requirements(category);

-- 7. Compliance Evaluations (Evidence references valid document chunk)
CREATE TABLE IF NOT EXISTS compliance_evaluations (
    id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES compliance_requirements(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('COVERED', 'PARTIALLY_COVERED', 'MISSING')),
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    evidence_chunk_id TEXT REFERENCES document_chunks(id) ON DELETE SET NULL,
    evidence_quote TEXT,
    gap_analysis TEXT,
    recommended_action TEXT,
    human_review_required BOOLEAN NOT NULL DEFAULT 0,
    evidence_category TEXT DEFAULT 'NONE',
    assessment_rationale TEXT DEFAULT '',
    previous_status TEXT,
    status_changed BOOLEAN DEFAULT 0,
    control_objective TEXT DEFAULT '',
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evaluations_requirement ON compliance_evaluations(requirement_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_status ON compliance_evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_evidence_chunk ON compliance_evaluations(evidence_chunk_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_evaluated_at ON compliance_evaluations(evaluated_at);

-- 8. Knowledge Nodes (Obsidian-style Notes)
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN ('document', 'requirement', 'control', 'evidence', 'assessment', 'remediation')),
    content_markdown TEXT NOT NULL,
    frontmatter_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_slug ON knowledge_nodes(slug);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_type ON knowledge_nodes(node_type);

-- 9. Knowledge Links (Bi-Directional Wiki Links & Backlinks with Provenance)
CREATE TABLE IF NOT EXISTS knowledge_links (
    id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_slug TEXT NOT NULL,
    link_text TEXT,
    context_snippet TEXT,
    relation_type TEXT DEFAULT 'references',
    provenance TEXT DEFAULT 'wiki_link',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_links_source ON knowledge_links(source_node_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_links_target ON knowledge_links(target_slug);

-- 10. Audit Logs (Preserve audit history)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    step_number INTEGER NOT NULL DEFAULT 1,
    tool_name TEXT,
    input_payload TEXT,
    output_payload TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_session ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON audit_logs(event_type);
"""


class DatabaseManager:
    """Manages SQLite connections, schema initialization, and transactional operations."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Create a connection with foreign keys and WAL mode configured."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Transactional context manager that commits on exit or rolls back on error."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Database transaction rolled back due to error: %s", exc)
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Execute DDL script to create tables, indexes, and triggers, and apply migrations."""
        with self.session() as conn:
            conn.executescript(SCHEMA_SQL)
            self._run_migrations(conn)
        logger.info("Database schema initialized and migrated at %s", self.db_path)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Apply non-destructive schema migrations for Phase 2.4."""
        # 1. Check knowledge_links columns
        cursor = conn.execute("PRAGMA table_info(knowledge_links);")
        link_cols = {row["name"] for row in cursor.fetchall()}
        if "relation_type" not in link_cols:
            conn.execute("ALTER TABLE knowledge_links ADD COLUMN relation_type TEXT DEFAULT 'references';")
        if "provenance" not in link_cols:
            conn.execute("ALTER TABLE knowledge_links ADD COLUMN provenance TEXT DEFAULT 'wiki_link';")

        # 2. Check compliance_evaluations columns
        cursor = conn.execute("PRAGMA table_info(compliance_evaluations);")
        eval_cols = {row["name"] for row in cursor.fetchall()}
        if "evidence_category" not in eval_cols:
            conn.execute("ALTER TABLE compliance_evaluations ADD COLUMN evidence_category TEXT DEFAULT 'NONE';")
        if "assessment_rationale" not in eval_cols:
            conn.execute("ALTER TABLE compliance_evaluations ADD COLUMN assessment_rationale TEXT DEFAULT '';")
        if "previous_status" not in eval_cols:
            conn.execute("ALTER TABLE compliance_evaluations ADD COLUMN previous_status TEXT;")
        if "status_changed" not in eval_cols:
            conn.execute("ALTER TABLE compliance_evaluations ADD COLUMN status_changed BOOLEAN DEFAULT 0;")
        if "control_objective" not in eval_cols:
            conn.execute("ALTER TABLE compliance_evaluations ADD COLUMN control_objective TEXT DEFAULT '';")

        # Ensure index exists on relation_type
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_links_relation ON knowledge_links(relation_type);")

    # -------------------------------------------------------------------------
    # Document Operations
    # -------------------------------------------------------------------------

    def get_document_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        """Retrieve existing document record by SHA-256 digest for deduplication."""
        query = "SELECT * FROM documents WHERE file_hash = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (file_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieve a document record by its primary key ID."""
        query = "SELECT * FROM documents WHERE id = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (document_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_documents(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List documents with pagination."""
        query = "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def count_documents(self) -> int:
        """Count total ingested documents."""
        query = "SELECT COUNT(*) FROM documents;"
        with self.session() as conn:
            cursor = conn.execute(query)
            return cursor.fetchone()[0]

    def insert_document(
        self,
        doc_id: str,
        meta: DocumentMetadata,
        filepath: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert a new document record."""
        meta_json = json.dumps(extra_metadata or meta.extra)
        query = """
        INSERT INTO documents (
            id, filename, filepath, file_hash, mime_type, file_size_bytes, page_count, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.session() as conn:
            conn.execute(
                query,
                (
                    doc_id,
                    meta.filename,
                    filepath,
                    meta.file_hash,
                    meta.mime_type,
                    meta.file_size_bytes,
                    meta.page_count,
                    meta_json,
                ),
            )
        return self.get_document_by_id(doc_id)  # type: ignore

    def delete_document(self, document_id: str) -> bool:
        """
        Safely delete a document.
        Cascades to document_chunks, and FTS5 triggers automatically delete from chunks_fts.
        """
        query = "DELETE FROM documents WHERE id = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (document_id,))
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Chunk Operations
    # -------------------------------------------------------------------------

    def insert_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Bulk insert document chunks into document_chunks (triggers FTS5 insert)."""
        if not chunks:
            return

        query = """
        INSERT INTO document_chunks (
            id, document_id, chunk_index, page_number, section_heading, locator, content, token_count, faiss_index_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        records = [
            (
                c.id,
                c.document_id,
                c.chunk_index,
                c.page_number,
                c.section_heading,
                c.locator,
                c.content,
                c.token_count,
                c.faiss_index_id,
            )
            for c in chunks
        ]
        with self.session() as conn:
            conn.executemany(query, records)

    def update_chunk_faiss_id(self, chunk_id: str, faiss_index_id: int) -> None:
        """Update the FAISS index row ID for a chunk."""
        query = "UPDATE document_chunks SET faiss_index_id = ? WHERE id = ?;"
        with self.session() as conn:
            conn.execute(query, (faiss_index_id, chunk_id))

    def get_chunks_for_document(self, document_id: str) -> list[dict[str, Any]]:
        """Retrieve all chunks belonging to a document ordered by chunk_index."""
        query = """
        SELECT * FROM document_chunks 
        WHERE document_id = ? 
        ORDER BY chunk_index ASC;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (document_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        """Retrieve a specific chunk with joined document metadata."""
        query = """
        SELECT 
            c.*,
            d.filename AS document_name,
            d.file_hash AS document_hash
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id = ?;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (chunk_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_chunks_by_faiss_ids(self, faiss_ids: list[int]) -> dict[int, dict[str, Any]]:
        """Fetch chunks mapped by their FAISS index ID."""
        if not faiss_ids:
            return {}
        placeholders = ",".join("?" for _ in faiss_ids)
        query = f"""
        SELECT 
            c.*,
            d.filename AS document_name
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.faiss_index_id IN ({placeholders});
        """
        with self.session() as conn:
            cursor = conn.execute(query, faiss_ids)
            result = {}
            for row in cursor.fetchall():
                data = dict(row)
                result[data["faiss_index_id"]] = data
            return result

    def get_all_chunks_with_documents(self) -> list[dict[str, Any]]:
        """Retrieve all chunks for FAISS index rebuild."""
        query = """
        SELECT 
            c.id AS chunk_id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.faiss_index_id,
            d.filename
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY c.document_id, c.chunk_index;
        """
        with self.session() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Lexical Search (SQLite FTS5)
    # -------------------------------------------------------------------------

    def lexical_search(
        self,
        query_text: str,
        limit: int = 20,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute BM25 lexical search using SQLite FTS5.
        Returns results ranked by BM25 ascending (lower is better in SQLite FTS5).
        """
        # Clean query for FTS5 (strip punctuation, tokenize, quote each term)
        clean_text = "".join(ch if ch.isalnum() else " " for ch in query_text)
        tokens = [t.strip() for t in clean_text.split() if t.strip()]
        if not tokens:
            return []
        fts_query = " OR ".join(f'"{t}"' for t in tokens)

        if document_id:
            sql = """
            SELECT 
                f.chunk_id,
                f.document_id,
                f.section_heading,
                c.content,
                c.page_number,
                c.locator,
                c.faiss_index_id,
                d.filename AS document_name,
                bm25(chunks_fts) AS bm25_rank
            FROM chunks_fts f
            JOIN document_chunks c ON f.chunk_id = c.id
            JOIN documents d ON f.document_id = d.id
            WHERE chunks_fts MATCH ? AND f.document_id = ?
            ORDER BY bm25(chunks_fts) ASC
            LIMIT ?;
            """
            params: tuple[Any, ...] = (fts_query, document_id, limit)
        else:
            sql = """
            SELECT 
                f.chunk_id,
                f.document_id,
                f.section_heading,
                c.content,
                c.page_number,
                c.locator,
                c.faiss_index_id,
                d.filename AS document_name,
                bm25(chunks_fts) AS bm25_rank
            FROM chunks_fts f
            JOIN document_chunks c ON f.chunk_id = c.id
            JOIN documents d ON f.document_id = d.id
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts) ASC
            LIMIT ?;
            """
            params = (fts_query, limit)

        with self.session() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Compliance Framework & Requirement Operations
    # -------------------------------------------------------------------------

    def get_framework(self, framework_id_or_name: str) -> dict[str, Any] | None:
        """Retrieve a compliance framework by ID or unique name."""
        query = "SELECT * FROM compliance_frameworks WHERE id = ? OR name = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (framework_id_or_name, framework_id_or_name))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_frameworks(self) -> list[dict[str, Any]]:
        """List all registered compliance frameworks."""
        query = "SELECT * FROM compliance_frameworks ORDER BY name ASC;"
        with self.session() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def insert_framework(
        self,
        framework_id: str,
        name: str,
        version: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Insert or replace a compliance framework."""
        query = """
        INSERT INTO compliance_frameworks (id, name, version, description)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            version = excluded.version,
            description = excluded.description;
        """
        with self.session() as conn:
            conn.execute(query, (framework_id, name, version, description))
        return self.get_framework(framework_id)  # type: ignore

    def get_requirement(
        self,
        req_id_or_code: str,
        framework_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a requirement by its ID or by its req_code within a framework."""
        if framework_id:
            query = """
            SELECT * FROM compliance_requirements 
            WHERE (id = ? OR req_code = ?) AND framework_id = ?;
            """
            params = (req_id_or_code, req_id_or_code, framework_id)
        else:
            query = "SELECT * FROM compliance_requirements WHERE id = ? OR req_code = ?;"
            params = (req_id_or_code, req_id_or_code)

        with self.session() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_requirements_by_framework(self, framework_id_or_name: str) -> list[dict[str, Any]]:
        """Retrieve all requirements belonging to a framework ordered by req_code."""
        framework = self.get_framework(framework_id_or_name)
        if not framework:
            return []
        query = """
        SELECT * FROM compliance_requirements 
        WHERE framework_id = ? 
        ORDER BY req_code ASC;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (framework["id"],))
            return [dict(row) for row in cursor.fetchall()]

    def insert_requirement(
        self,
        req_id: str,
        framework_id: str,
        req_code: str,
        title: str,
        description: str,
        category: str,
        severity_level: int = 2,
    ) -> dict[str, Any]:
        """Insert or update a requirement within a framework."""
        query = """
        INSERT INTO compliance_requirements (
            id, framework_id, req_code, title, description, category, severity_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(framework_id, req_code) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            category = excluded.category,
            severity_level = excluded.severity_level;
        """
        with self.session() as conn:
            conn.execute(
                query,
                (req_id, framework_id, req_code, title, description, category, severity_level),
            )
        return self.get_requirement(req_id)  # type: ignore

    def insert_evaluation(
        self,
        eval_id: str,
        requirement_id: str,
        status: str,
        confidence_score: float,
        evidence_chunk_id: str | None = None,
        evidence_quote: str | None = None,
        gap_analysis: str | None = None,
        recommended_action: str | None = None,
        human_review_required: bool = False,
        evidence_category: str = "NONE",
        assessment_rationale: str = "",
        previous_status: str | None = None,
        status_changed: bool = False,
        control_objective: str = "",
    ) -> dict[str, Any]:
        """Record a compliance evaluation finding with chunk evidence traceability and historical change tracking."""
        # Check previous assessment if previous_status not passed
        if previous_status is None:
            prev_eval = self.get_latest_evaluation_for_requirement(requirement_id)
            if prev_eval:
                previous_status = prev_eval["status"]
                status_changed = (previous_status != status)

        query = """
        INSERT INTO compliance_evaluations (
            id, requirement_id, status, confidence_score, evidence_chunk_id,
            evidence_quote, gap_analysis, recommended_action, human_review_required,
            evidence_category, assessment_rationale, previous_status, status_changed,
            control_objective
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.session() as conn:
            conn.execute(
                query,
                (
                    eval_id,
                    requirement_id,
                    status,
                    confidence_score,
                    evidence_chunk_id,
                    evidence_quote,
                    gap_analysis,
                    recommended_action,
                    1 if human_review_required else 0,
                    evidence_category,
                    assessment_rationale,
                    previous_status,
                    1 if status_changed else 0,
                    control_objective,
                ),
            )
        return self.get_evaluation_by_id(eval_id)  # type: ignore

    def get_evaluation_by_id(self, eval_id: str) -> dict[str, Any] | None:
        """Retrieve evaluation finding by ID."""
        query = "SELECT * FROM compliance_evaluations WHERE id = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (eval_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_evaluation_for_requirement(self, requirement_id: str) -> dict[str, Any] | None:
        """Retrieve the most recent evaluation record for a requirement."""
        query = """
        SELECT * FROM compliance_evaluations
        WHERE requirement_id = ?
        ORDER BY evaluated_at DESC, rowid DESC
        LIMIT 1;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (requirement_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_historical_evaluations_for_requirement(
        self,
        requirement_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve chronological history of evaluations for a requirement."""
        query = """
        SELECT e.*, c.content AS chunk_content, d.filename AS document_name
        FROM compliance_evaluations e
        LEFT JOIN document_chunks c ON e.evidence_chunk_id = c.id
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE e.requirement_id = ?
        ORDER BY e.evaluated_at DESC, e.rowid DESC
        LIMIT ?;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (requirement_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_latest_evaluations_for_framework(
        self,
        framework_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve the latest evaluation record for every requirement in a framework."""
        query = """
        SELECT r.id AS req_id, r.req_code, r.title, r.category, r.severity_level,
               e.id AS eval_id, e.status, e.confidence_score, e.evidence_category,
               e.evidence_chunk_id, e.evidence_quote, e.gap_analysis,
               e.recommended_action, e.human_review_required, e.assessment_rationale,
               e.previous_status, e.status_changed, e.evaluated_at
        FROM compliance_requirements r
        LEFT JOIN compliance_evaluations e ON e.requirement_id = r.id
        WHERE r.framework_id = ?
        AND (e.id IS NULL OR e.id = (
            SELECT id FROM compliance_evaluations
            WHERE requirement_id = r.id
            ORDER BY evaluated_at DESC, rowid DESC
            LIMIT 1
        ))
        ORDER BY r.req_code ASC;
        """
        with self.session() as conn:
            cursor = conn.execute(query, (framework_id,))
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Knowledge Graph Operations
    # -------------------------------------------------------------------------

    def get_knowledge_node(self, node_id_or_slug: str) -> dict[str, Any] | None:
        """Retrieve knowledge node by ID or slug."""
        query = "SELECT * FROM knowledge_nodes WHERE id = ? OR slug = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (node_id_or_slug, node_id_or_slug))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_all_knowledge_nodes(self) -> list[dict[str, Any]]:
        """List all registered knowledge nodes."""
        query = "SELECT * FROM knowledge_nodes ORDER BY title ASC;"
        with self.session() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def insert_knowledge_node(
        self,
        node_id: str,
        slug: str,
        title: str,
        node_type: str,
        content_markdown: str,
        frontmatter_json: str = "{}",
    ) -> dict[str, Any]:
        """Insert or replace a knowledge node."""
        query = """
        INSERT INTO knowledge_nodes (
            id, slug, title, node_type, content_markdown, frontmatter_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            node_type = excluded.node_type,
            content_markdown = excluded.content_markdown,
            frontmatter_json = excluded.frontmatter_json,
            updated_at = CURRENT_TIMESTAMP;
        """
        with self.session() as conn:
            conn.execute(
                query,
                (node_id, slug, title, node_type, content_markdown, frontmatter_json),
            )
        return self.get_knowledge_node(node_id)  # type: ignore

    def insert_knowledge_link(
        self,
        link_id: str,
        source_node_id: str,
        target_slug: str,
        link_text: str | None = None,
        context_snippet: str | None = None,
        relation_type: str = "references",
        provenance: str = "wiki_link",
    ) -> bool:
        """
        Insert a directional knowledge link between nodes with explicit relation type and provenance.
        Prevents duplicate links with identical source, target, and relation type.
        """
        # Duplicate check
        check_query = """
        SELECT id FROM knowledge_links
        WHERE source_node_id = ? AND target_slug = ? AND relation_type = ?;
        """
        insert_query = """
        INSERT INTO knowledge_links (
            id, source_node_id, target_slug, link_text, context_snippet, relation_type, provenance
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.session() as conn:
            cursor = conn.execute(check_query, (source_node_id, target_slug, relation_type))
            if cursor.fetchone():
                return False  # Already exists, duplicate prevented

            conn.execute(
                insert_query,
                (link_id, source_node_id, target_slug, link_text, context_snippet, relation_type, provenance),
            )
            return True

    def delete_knowledge_link(self, link_id: str) -> bool:
        """Delete a knowledge link by ID."""
        query = "DELETE FROM knowledge_links WHERE id = ?;"
        with self.session() as conn:
            cursor = conn.execute(query, (link_id,))
            return cursor.rowcount > 0

    def get_outgoing_links(
        self,
        source_node_id: str,
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve outgoing links from a knowledge node, optionally filtered by relation type."""
        if relation_type:
            query = """
            SELECT l.*, n.title AS target_title, n.node_type AS target_type
            FROM knowledge_links l
            LEFT JOIN knowledge_nodes n ON l.target_slug = n.slug
            WHERE l.source_node_id = ? AND l.relation_type = ?;
            """
            params: tuple[Any, ...] = (source_node_id, relation_type)
        else:
            query = """
            SELECT l.*, n.title AS target_title, n.node_type AS target_type
            FROM knowledge_links l
            LEFT JOIN knowledge_nodes n ON l.target_slug = n.slug
            WHERE l.source_node_id = ?;
            """
            params = (source_node_id,)

        with self.session() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_backlinks(
        self,
        target_slug: str,
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve backlinks that reference target_slug, optionally filtered by relation type."""
        if relation_type:
            query = """
            SELECT l.*, n.slug AS source_slug, n.title AS source_title, n.node_type AS source_type
            FROM knowledge_links l
            JOIN knowledge_nodes n ON l.source_node_id = n.id
            WHERE l.target_slug = ? AND l.relation_type = ?;
            """
            params: tuple[Any, ...] = (target_slug, relation_type)
        else:
            query = """
            SELECT l.*, n.slug AS source_slug, n.title AS source_title, n.node_type AS source_type
            FROM knowledge_links l
            JOIN knowledge_nodes n ON l.source_node_id = n.id
            WHERE l.target_slug = ?;
            """
            params = (target_slug,)

        with self.session() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_orphan_knowledge_nodes(self) -> list[dict[str, Any]]:
        """Retrieve knowledge nodes that have 0 outgoing links and 0 incoming backlinks."""
        query = """
        SELECT n.*
        FROM knowledge_nodes n
        WHERE n.id NOT IN (SELECT DISTINCT source_node_id FROM knowledge_links)
        AND n.slug NOT IN (SELECT DISTINCT target_slug FROM knowledge_links)
        ORDER BY n.title ASC;
        """
        with self.session() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Audit Operations
    # -------------------------------------------------------------------------

    def log_audit_event(
        self,
        session_id: str,
        event_type: str,
        step_number: int = 1,
        tool_name: str | None = None,
        input_payload: dict[str, Any] | None = None,
        output_payload: dict[str, Any] | None = None,
        execution_time_ms: int | None = None,
    ) -> int:
        """Insert an audit log entry for complete traceability."""
        query = """
        INSERT INTO audit_logs (
            session_id, event_type, step_number, tool_name, input_payload, output_payload, execution_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        in_json = json.dumps(input_payload) if input_payload else None
        out_json = json.dumps(output_payload) if output_payload else None
        with self.session() as conn:
            cursor = conn.execute(
                query,
                (
                    session_id,
                    event_type,
                    step_number,
                    tool_name,
                    in_json,
                    out_json,
                    execution_time_ms,
                ),
            )
            return cursor.lastrowid

# VERITY: Requirements Specification

**Project:** VERITY – Enterprise Document Intelligence & Compliance Agent  
**Document:** System Requirements & Constraints Specification  
**Classification:** Technical Assessment Blueprint (Confidential)  
**Author:** Principal AI Architect & Senior Python Engineer  
**Date:** November 2026  

---

## 1. System Vision & Objective

VERITY is an autonomous, bounded Enterprise Document Intelligence & Compliance Agent designed to ingest enterprise policy and regulatory documents, construct a local hybrid vector-lexical knowledge graph, execute compliance evaluations through genuine Model Context Protocol (MCP) tool sessions, and present traceable, citation-backed findings without commercial cloud API dependencies.

---

## 2. Functional Requirements (FR)

### FR-1: Document Ingestion & Parsing
- **FR-1.1:** Support ingestion of PDF (`.pdf`), Microsoft Word (`.docx`), and Plain Text (`.txt`) documents.
- **FR-1.2:** Extract text, document layout hierarchy, page numbers, and structural section headers using PyMuPDF (`pymupdf`) and `python-docx`.
- **FR-1.3:** Perform cryptographic deduplication using SHA-256 hash calculation prior to disk storage and indexing.
- **FR-1.4:** Enforce file size limits (default $\le 25\text{ MB}$) and file type validation via MIME sniff and header checks.
- **FR-1.5:** Generate chunked representations with bounded token length ($300 - 500$ tokens with 50-token overlap) preserving document ID, chunk index, page number, and section title metadata.

### FR-2: Hybrid Retrieval Engine
- **FR-2.1:** **Dense Retrieval:** Compute 384-dimensional dense semantic embeddings using the local `all-MiniLM-L6-v2` Sentence-Transformers model running locally on CPU.
- **FR-2.2:** Index dense vectors in a persistent FAISS CPU `IndexFlatL2` or `IndexIVFFlat` index stored in `data/faiss/index.faiss`.
- **FR-2.3:** **Lexical Retrieval:** Maintain an SQLite FTS5 (Full-Text Search 5) virtual table with BM25 ranking for exact keyword, acronym, and regulation code matching (e.g., "SOC 2 Type II CC6.1", "ISO 27001 A.12.1").
- **FR-2.4:** **Hybrid Fusion:** Implement Reciprocal Rank Fusion (RRF) with constant $k=60$ to merge dense vector rankings and lexical BM25 rankings:
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{lexical}\}} \frac{1}{k + r_m(d)}$$
- **FR-2.5:** Return retrieved chunks with normalized relevance scores, chunk text, document title, page number, and section path.

### FR-3: Genuine Model Context Protocol (MCP) Integration
- **FR-3.1:** Implement a standalone MCP Server process using `FastMCP` from the official MCP Python SDK.
- **FR-3.2:** Execute MCP communication strictly through the official MCP protocol using standard input/output (`stdio`) transport sessions. Direct Python function invocation from the agent layer is forbidden.
- **FR-3.3:** Expose exactly 7 standardized enterprise compliance tools:
  1. `list_documents`
  2. `search_documents`
  3. `get_document_metadata`
  4. `get_citation`
  5. `evaluate_compliance`
  6. `gap_analysis`
  7. `get_related_knowledge`
- **FR-3.4:** All tool parameters and return values must conform strictly to Pydantic JSON Schemas with exhaustive validation and error responses.

### FR-4: Bounded Agent Orchestrator
- **FR-4.1:** Receive user natural language queries, identify task category (Retrieval, Compliance Audit, Gap Identification, Knowledge Exploration).
- **FR-4.2:** **Bounded Execution Budget:** Impose a strict ceiling of maximum 5 MCP tool invocations per user turn to prevent recursion, infinite reasoning loops, or token waste.
- **FR-4.3:** Enforce an explicit tool allowlist; reject any tool request outside the approved set.
- **FR-4.4:** Validate all tool arguments prior to dispatch.
- **FR-4.5:** Implement strict tool execution timeouts (default: 8.0 seconds per tool call).
- **FR-4.6:** **Deterministic Fallback Mode:** In the event the local Ollama LLM is unavailable or unresponsive, the orchestrator must transition automatically to deterministic retrieval mode, synthesizing structured responses directly from MCP tool returns and labeling the output clearly as `[Deterministic Output - LLM Offline]`.

### FR-5: Enterprise Compliance Engine
- **FR-5.1:** Evaluate documents against structured regulatory and policy frameworks (e.g., ISO 27001, SOC 2, HIPAA, GDPR).
- **FR-5.2:** Classify every evaluation item into one of three strict states:
  - `COVERED`: Requirement is demonstrably satisfied by retrieved evidence.
  - `PARTIALLY_COVERED`: Requirement is addressed but lacks specific controls, audit trails, or operational details.
  - `MISSING`: Requirement is absent, unaddressed, or contradicted by the documentation.
- **FR-5.3:** **Mandatory Evidence Rule:** A requirement shall never be marked as `COVERED` without direct, verbatim evidence linked to a verified source document and page/section number.
- **FR-5.4:** Every finding must output: Requirement Code/Title, Compliance Status, Evidence Excerpt, Source Document, Page Number / Section, Identified Gap, Recommended Remediation, and Confidence Score / Human Review Flag.

### FR-6: Obsidian-Inspired Knowledge Management
- **FR-6.1:** Structure ingested enterprise intelligence into linked conceptual notes:
  - *Document Notes:* Summary, hash, author, ingestion metadata.
  - *Requirement Notes:* Individual regulatory mandates and control statements.
  - *Control Notes:* Operational controls implemented by the organization.
  - *Evidence Notes:* Chunks and verification records validating controls.
- **FR-6.2:** Support bi-directional Wiki-style linking using `[[Target Note]]` syntax.
- **FR-6.3:** Parse, persist, and index relationships and backlinks in SQLite without requiring external graph database dependencies like Neo4j.
- **FR-6.4:** Provide relationship graph querying for interactive exploration.

### FR-7: Frontend User Interface
- **FR-7.1:** React 19 + Vite + TypeScript single-page application with responsive Tailwind CSS design.
- **FR-7.2:** Interactive Compliance Audit Dashboard displaying framework coverage bars (Recharts), gap lists, and status chips.
- **FR-7.3:** Document Repository & Upload view with file ingestion progress and SHA-256 verification.
- **FR-7.4:** Interactive Agent Chat view with streaming thoughts, tool invocation traces, and citation preview drawer.
- **FR-7.5:** Knowledge Graph Explorer displaying document backlinks and related requirements.

---

## 3. Non-Functional Requirements (NFR)

### NFR-1: Hardware & Resource Optimization
- **NFR-1.1:** Total memory consumption under maximum active load must remain within **7.84 GB available physical RAM**.
- **NFR-1.2:** CPU utilization must be optimized for the 6-core / 12-thread Intel i5-11400F with AVX2 vectorized operations.
- **NFR-1.3:** Local LLM model parameter footprint must $\le 2\text{ GB}$ (standardizing on `qwen2.5:1.5b` at 986 MB Q4_K_M).
- **NFR-1.4:** Model weights, raw datasets, and temporary blobs must reside on Drive `D:` (`D:\ollama\models`), strictly protecting the remaining 13.55 GB on Drive `C:`.

### NFR-2: Zero-Cost Operational Model
- **NFR-2.1:** The entire runtime must operate 100% locally with zero paid API keys, zero cloud egress subscriptions, and zero pay-per-token operational costs.

### NFR-3: Security & Data Privacy
- **NFR-3.1:** **Prompt-Injection Defense:** Ingested document content injected into prompts must be enclosed in structural containment tags (`<document_chunk id="...">...</document_chunk>`) with active instruction-stripping sanitizers.
- **NFR-3.2:** **Safe Parser Isolation:** Document parsing must be passive text extraction. Script execution, macro evaluation, and dynamic link dereferencing inside PDF/DOCX are prohibited.
- **NFR-3.3:** **Strict Local Boundary:** Uploaded documents, vector indices, SQLite databases, and LLM prompts shall never leave `127.0.0.1`.
- **NFR-3.4:** Synthetic demonstration documents only; real PII or confidential company data must not be ingested during testing.

### NFR-4: Traceability & Zero Hallucination
- **NFR-4.1:** All generated claims must include a verified citation pointer resolving to a specific document chunk and page.
- **NFR-4.2:** Claims without verifiable source chunks must be explicitly flagged with `[Unverified / Unsupported Claim]`.


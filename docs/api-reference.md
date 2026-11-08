# VERITY: REST API Reference Specification

**Project:** VERITY – Enterprise Document Intelligence & Compliance Agent  
**Document:** Production REST API Reference  
**Version:** 1.0.0  
**Classification:** Technical Assessment Blueprint (Confidential)  
**Author:** Principal AI Architect & Senior Python Engineer  
**Date:** November 2026 (Phase 2.5)  

---

## 1. Overview & Authentication

VERITY provides an enterprise-grade REST API built on FastAPI. It provides document ingestion, hybrid search, evidence-grounded agent chat, zero-trust compliance auditing, and Obsidian-style knowledge graph discovery.

### Base URL:
```
http://127.0.0.1:8000
```

### Authentication & RBAC Headers:
Supply an assigned API key using either the `X-API-Key` header or an HTTP Bearer token:
```http
X-API-Key: verity-admin-secret-key
```
or
```http
Authorization: Bearer verity-admin-secret-key
```

### Role-Based Access Control (RBAC):
| Role | Default Key | Permissions |
| :--- | :--- | :--- |
| **`admin`** | `verity-admin-secret-key` | Full access: Upload, delete documents, evaluate compliance, search, chat, knowledge |
| **`auditor`** | `verity-auditor-secret-key` | Read documents, search, chat, evaluate compliance, gap analysis, history, knowledge |
| **`user`** | `verity-user-secret-key` | Read documents, search, chat, knowledge queries |

---

## 2. Health & Diagnostic Endpoints

### 2.1 Liveness Probe
- **Endpoint:** `GET /health`
- **Auth:** Public (None required)
- **Description:** Fast non-blocking healthcheck confirming the HTTP server is alive.
- **Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "VERITY Enterprise Intelligence & Compliance API",
  "version": "1.0.0",
  "timestamp": "2026-11-07T20:15:00.000000Z"
}
```

### 2.2 Readiness Probe
- **Endpoint:** `GET /ready`
- **Auth:** Public (None required)
- **Description:** Deep diagnostic probe checking SQLite connectivity, FAISS vector index, and Ollama reachability.
- **Response (200 OK):**
```json
{
  "status": "ready",
  "components": {
    "sqlite": {
      "status": "healthy",
      "latency_ms": 0.35,
      "details": { "path": "verity.db" }
    },
    "faiss": {
      "status": "healthy",
      "latency_ms": 0.08,
      "details": { "indexed_vectors": 142 }
    },
    "ollama": {
      "status": "healthy",
      "latency_ms": 12.4,
      "details": { "reachability": "connected" }
    }
  },
  "timestamp": "2026-11-07T20:15:00.000000Z"
}
```

---

## 3. Document Intelligence Endpoints

### 3.1 Upload & Ingest Document
- **Endpoint:** `POST /api/v1/documents/upload`
- **Auth:** Requires `admin`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: Binary file (PDF, DOCX, TXT; max 25 MB).
- **Validation Rules:**
  - Enforces magic byte verification (`%PDF-`, `PK\x03\x04`, UTF-8).
  - Filename sanitization against path traversal (`..`, control characters).
  - Antivirus scanning (ClamAV / Windows Defender / EICAR isolation).
  - SHA-256 deduplication.
- **Example Request (cURL):**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents/upload" \
  -H "X-API-Key: verity-admin-secret-key" \
  -F "file=@Corporate_Security_Policy.pdf"
```
- **Response (201 Created):**
```json
{
  "document_id": "doc_e3b0c442a8b9",
  "filename": "Corporate_Security_Policy.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "file_size_bytes": 1048576,
  "mime_type": "application/pdf",
  "chunks_count": 24,
  "status": "ingested",
  "message": "Successfully indexed 24 chunks.",
  "malware_scan": {
    "scanned": false,
    "engine": "Static Signature & Heuristic Scanner",
    "is_clean": true,
    "details": "Local Antivirus CLI unavailable offline; static magic bytes & heuristic checks verified."
  }
}
```

### 3.2 List Documents
- **Endpoint:** `GET /api/v1/documents`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Query Parameters:**
  - `limit` (integer, default: 20, 1-100)
  - `offset` (integer, default: 0)
- **Response (200 OK):**
```json
{
  "total_count": 1,
  "documents": [
    {
      "id": "doc_e3b0c442a8b9",
      "filename": "Corporate_Security_Policy.pdf",
      "file_hash": "e3b0c442...",
      "mime_type": "application/pdf",
      "file_size_bytes": 1048576,
      "page_count": 12,
      "created_at": "2026-11-07T20:00:00Z"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### 3.3 Get Document Details
- **Endpoint:** `GET /api/v1/documents/{document_id}`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Response (200 OK):**
```json
{
  "id": "doc_e3b0c442a8b9",
  "filename": "Corporate_Security_Policy.pdf",
  "file_hash": "e3b0c442...",
  "mime_type": "application/pdf",
  "file_size_bytes": 1048576,
  "page_count": 12,
  "total_chunks": 24,
  "sections": ["Section 1.0 General", "Section 2.1 MFA", "Section 4.3 Encryption"],
  "created_at": "2026-11-07T20:00:00Z",
  "metadata_json": { "uploaded_by": "admin-user" }
}
```

### 3.4 Delete Document
- **Endpoint:** `DELETE /api/v1/documents/{document_id}`
- **Auth:** Requires `admin`
- **Response (200 OK):**
```json
{
  "status": "deleted",
  "document_id": "doc_e3b0c442a8b9",
  "message": "Document, chunks, and vector index entries successfully removed."
}
```

---

## 4. Hybrid Search Endpoint

### 4.1 Execute Hybrid Retrieval
- **Endpoint:** `POST /api/v1/search`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Request Body:**
```json
{
  "query": "What are the requirements for multi-factor authentication?",
  "top_k": 3,
  "document_ids": null
}
```
- **Response (200 OK):**
```json
{
  "query": "What are the requirements for multi-factor authentication?",
  "total_results": 1,
  "results": [
    {
      "chunk_id": "chk_doc_e3b0_0001",
      "document_id": "doc_e3b0c442a8b9",
      "document_name": "Corporate_Security_Policy.pdf",
      "page_number": 2,
      "section_heading": "Section 2.1 Multi-Factor Authentication",
      "locator": "Page 2 ¶1",
      "content": "All corporate access mandates multi-factor authentication (MFA) with FIDO2 hardware tokens.",
      "rrf_score": 0.0328
    }
  ]
}
```

---

## 5. Agent Chat & Streaming Endpoints

### 5.1 Standard Agent Interaction
- **Endpoint:** `POST /api/v1/chat`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Request Body:**
```json
{
  "query": "Explain our password and MFA requirements.",
  "session_id": "sess_user_123"
}
```
- **Response (200 OK):**
```json
{
  "session_id": "sess_user_123",
  "query": "Explain our password and MFA requirements.",
  "intent": "document_qa",
  "answer": "According to the Corporate Security Policy, all corporate and production access mandates multi-factor authentication (MFA) using FIDO2 hardware tokens or TOTP authenticator applications. Passwords must be at least 16 characters and rotated annually [Corporate_Security_Policy.pdf, Page 2].",
  "citations": [
    {
      "chunk_id": "chk_doc_e3b0_0001",
      "document_name": "Corporate_Security_Policy.pdf",
      "page_number": 2,
      "section_heading": "Section 2.1 Multi-Factor Authentication",
      "locator": "Page 2 ¶1",
      "exact_quote": "All corporate access mandates multi-factor authentication (MFA) with FIDO2 hardware tokens.",
      "verified": true
    }
  ],
  "compliance_status": null,
  "confidence_score": 0.94,
  "human_review_required": false,
  "execution_time_ms": 1120,
  "tools_executed": ["search_documents", "get_citation"]
}
```

### 5.2 Server-Sent Events (SSE) Stream
- **Endpoint:** `POST /api/v1/chat/stream`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Headers:** `Accept: text/event-stream`
- **Stream Format:**
```
event: status
data: {"stage": "planning", "message": "Sanitizing query and formulating plan..."}

event: status
data: {"stage": "execution", "message": "Executing MCP tools and verifying evidence..."}

event: token
data: {"token": "According to the Corporate "}

event: token
data: {"token": "Security Policy, all access "}

event: citation
data: {"chunk_id": "chk_doc_e3b0_0001", "document_name": "Corporate_Security_Policy.pdf", "page_number": 2, ...}

event: done
data: {"session_id": "sess_user_123", "intent": "document_qa", "confidence_score": 0.94, ...}
```

---

## 6. Compliance Intelligence Endpoints

### 6.1 Evaluate Compliance Framework
- **Endpoint:** `POST /api/v1/compliance/evaluate`
- **Auth:** Requires `auditor` or `admin`
- **Request Body:**
```json
{
  "framework_id": "SOC2",
  "requirement_id": "CC6.1",
  "evidence_document_ids": null
}
```
- **Response (200 OK):**
```json
{
  "framework_id": "fw_soc2",
  "framework_name": "SOC2",
  "total_requirements": 1,
  "coverage_summary": {
    "covered": 1,
    "partially_covered": 0,
    "missing": 0,
    "total": 1,
    "compliance_percentage": 100.0
  },
  "findings": [
    {
      "requirement_code": "CC6.1",
      "title": "Logical Access Controls",
      "category": "Access Control",
      "status": "COVERED",
      "confidence_score": 0.94,
      "evidence": {
        "chunk_id": "chk_doc_e3b0_0001",
        "document_id": "doc_e3b0c442a8b9",
        "document_name": "Corporate_Security_Policy.pdf",
        "page_number": 2,
        "section_heading": "Section 2.1 Multi-Factor Authentication",
        "locator": "Page 2 ¶1",
        "quote": "All corporate access mandates multi-factor authentication (MFA) with FIDO2 hardware tokens."
      },
      "gap": null,
      "recommendation": "Maintain continuous operational logging and periodic compliance reviews for CC6.1.",
      "human_review_required": false,
      "assurance_level": "Operating Evidence"
    }
  ]
}
```

### 6.2 Gap Analysis
- **Endpoint:** `POST /api/v1/compliance/gap-analysis`
- **Auth:** Requires `auditor` or `admin`
- **Request Body:**
```json
{
  "framework_id": "SOC2",
  "severity_filter": "All"
}
```
- **Response (200 OK):**
```json
{
  "framework_id": "fw_soc2",
  "framework_name": "SOC2",
  "total_gaps": 1,
  "covered_count": 2,
  "partially_covered_count": 0,
  "missing_count": 1,
  "human_review_count": 0,
  "remediation_roadmap": [
    {
      "priority_rank": 1,
      "requirement_code": "CC7.1",
      "title": "Vulnerability Management",
      "category": "Vulnerability Management",
      "current_status": "MISSING",
      "severity": "High",
      "identified_gap": "No documentation or technical evidence found addressing CC7.1.",
      "remediation_recommendation": "Configure automated vulnerability scanning.",
      "human_review_required": false,
      "estimated_effort_days": 7
    }
  ]
}
```

### 6.3 Compliance History & Diffs
- **Endpoint:** `GET /api/v1/compliance/history?framework_id=SOC2`
- **Auth:** Requires `auditor` or `admin`
- **Response (200 OK):**
```json
{
  "framework_id": "fw_soc2",
  "total_requirements": 1,
  "diffs": [
    {
      "requirement_id": "req_soc2_cc61",
      "requirement_code": "CC6.1",
      "current_status": "COVERED",
      "previous_status": "PARTIALLY_COVERED",
      "status_changed": true,
      "current_confidence": 0.94,
      "previous_confidence": 0.65,
      "new_evidence_found": true,
      "summary": "Status shifted from PARTIALLY_COVERED to COVERED (Confidence: 0.65 -> 0.94)."
    }
  ]
}
```

---

## 7. Knowledge Graph Endpoints

### 7.1 Get Knowledge Node & Traversal
- **Endpoint:** `GET /api/v1/knowledge/{node_slug}?depth=1`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Response (200 OK):**
```json
{
  "root_node": {
    "id": "node_mfa_123",
    "slug": "mfa-policy",
    "title": "MFA Security Policy",
    "node_type": "control",
    "content_markdown": "# MFA Policy\nMandatory FIDO2 tokens per [[soc2-cc6-1]]."
  },
  "outgoing_links": [
    {
      "target_slug": "soc2-cc6-1",
      "target_title": "SOC 2 CC6.1",
      "link_text": "soc2-cc6-1",
      "context_snippet": "Mandatory FIDO2 tokens per [[soc2-cc6-1]]."
    }
  ],
  "backlinks": [
    {
      "source_slug": "iam-policy-v2",
      "source_title": "IAM Policy",
      "source_type": "document",
      "context_snippet": "Enforces [[mfa-policy]]."
    }
  ],
  "related_requirements": ["soc2-cc6-1"],
  "depth": 1
}
```

### 7.2 Get Backlinks
- **Endpoint:** `GET /api/v1/knowledge/{node_slug}/backlinks`
- **Auth:** Requires `user`, `auditor`, or `admin`
- **Response (200 OK):**
```json
{
  "target_slug": "mfa-policy",
  "total_backlinks": 1,
  "backlinks": [
    {
      "source_slug": "iam-policy-v2",
      "source_title": "IAM Policy",
      "source_type": "document",
      "context_snippet": "Enforces [[mfa-policy]]."
    }
  ]
}
```

---

## 8. Error Format

Every error response returns a structured, sanitized JSON payload without internal stack traces:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed: String should have at least 1 characters",
    "field": "body -> query"
  },
  "request_id": "req_8f69af5203eb",
  "timestamp": "2026-11-07T20:15:00.000000Z"
}
```


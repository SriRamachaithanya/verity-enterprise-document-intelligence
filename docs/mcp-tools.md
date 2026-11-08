# VERITY: Model Context Protocol (MCP) Tools Specification

**Project:** VERITY – Enterprise Document Intelligence & Compliance Agent  
**Document:** MCP Tool Definitions & Schemas  
**Classification:** Technical Assessment Blueprint (Confidential)  
**Author:** Principal AI Architect & Senior Python Engineer  
**Date:** November 2026  

---

## 1. Overview & Protocol Standard

VERITY implements the official Model Context Protocol (MCP) standard using `FastMCP` (v4.1.6) and the official Python MCP SDK (`mcp` v2.3.0). The tools below are registered on a standalone MCP Server process (`src.mcp_server.server`) and invoked strictly via JSON-RPC 2.0 messages across `stdio` communication channels.

### Subprocess Execution Command
```powershell
.\.venv\Scripts\python.exe -m src.mcp_server.server
```

### Communication Contract
- **stdout:** Exclusively reserved for JSON-RPC 2.0 protocol frames. No logs, prints, or debug statements are emitted to stdout.
- **stderr:** Used for operational logs, FastMCP startup diagnostics, and error reporting.
- **Environment Overrides:**
  - `VERITY_DB_PATH`: Path to SQLite database (default: `data/sqlite/verity.db`).
  - `VERITY_FAISS_DIR`: Path to FAISS vector index directory (default: `data/faiss`).
  - `PYTHONUNBUFFERED`: `1` (ensures unbuffered stdio streaming).

Every tool operates under:
- **Strict Pydantic Input/Output Schema Enforcement** (`src/schemas/mcp.py`).
- **Bounded execution timeouts (default: 8.0s).**
- **Graceful error envelope format** (returns structured errors with `is_error=True`, never crashes the subprocess).
- **Deterministic state reporting and verbatim citation ground truth.**

---

## 2. Tool 1: `list_documents`

### Purpose
Lists all ingested documents currently available in the system repository, returning high-level metadata (ID, filename, size, pages, ingestion timestamp, and cryptographic hash).

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "description": "Maximum number of documents to return (1-100).",
      "default": 20,
      "minimum": 1,
      "maximum": 100
    },
    "offset": {
      "type": "integer",
      "description": "Pagination offset.",
      "default": 0,
      "minimum": 0
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["total_count", "documents"],
  "properties": {
    "total_count": { "type": "integer" },
    "documents": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "filename", "file_hash", "mime_type", "file_size_bytes", "page_count", "created_at"],
        "properties": {
          "id": { "type": "string" },
          "filename": { "type": "string" },
          "file_hash": { "type": "string" },
          "mime_type": { "type": "string" },
          "file_size_bytes": { "type": "integer" },
          "page_count": { "type": "integer" },
          "created_at": { "type": "string" }
        }
      }
    }
  }
}
```

### Validation Rules & Error Handling
- Rejects negative limit/offset values.
- If no documents are ingested, returns `{"total_count": 0, "documents": []}` with HTTP/RPC success status.

### Example Invocation
```json
{
  "name": "list_documents",
  "arguments": {
    "limit": 2,
    "offset": 0
  }
}
```

### Expected Response
```json
{
  "total_count": 2,
  "documents": [
    {
      "id": "doc_e3b0c442",
      "filename": "Enterprise_Information_Security_Policy_v4.2.pdf",
      "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "mime_type": "application/pdf",
      "file_size_bytes": 1048576,
      "page_count": 28,
      "created_at": "2026-11-06T12:00:00Z"
    },
    {
      "id": "doc_8f12a9b3",
      "filename": "Access_Control_and_Key_Management_Procedure.docx",
      "file_hash": "8f12a9b33a01a91e5c2b3e89f81a7199c0812d8a43d941e7f32991b7852b1234",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "file_size_bytes": 458210,
      "page_count": 14,
      "created_at": "2026-11-06T12:05:00Z"
    }
  ]
}
```

---

## 3. Tool 2: `search_documents`

### Purpose
Executes a hybrid search combining FAISS dense vector similarity and SQLite FTS5 lexical BM25 retrieval merged via Reciprocal Rank Fusion (RRF).

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language or keyword search query.",
      "minLength": 2,
      "maxLength": 500
    },
    "top_k": {
      "type": "integer",
      "description": "Number of top ranked chunks to return.",
      "default": 5,
      "minimum": 1,
      "maximum": 20
    },
    "document_id": {
      "type": "string",
      "description": "Optional document filter to isolate search to a specific file.",
      "nullable": true
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["query", "results"],
  "properties": {
    "query": { "type": "string" },
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["chunk_id", "document_id", "document_name", "page_number", "section_heading", "content", "rrf_score"],
        "properties": {
          "chunk_id": { "type": "string" },
          "document_id": { "type": "string" },
          "document_name": { "type": "string" },
          "page_number": { "type": "integer" },
          "section_heading": { "type": "string" },
          "content": { "type": "string" },
          "rrf_score": { "type": "number" },
          "dense_rank": { "type": "integer", "nullable": true },
          "lexical_rank": { "type": "integer", "nullable": true }
        }
      }
    }
  }
}
```

### Validation Rules & Error Handling
- Strips leading/trailing whitespace; rejects empty or single-character queries.
- If `document_id` is supplied but does not exist in SQLite, returns an explicit error: `"Document ID 'xyz' not found."`

### Example Invocation
```json
{
  "name": "search_documents",
  "arguments": {
    "query": "cryptographic controls for data at rest AES-256",
    "top_k": 1
  }
}
```

### Expected Response
```json
{
  "query": "cryptographic controls for data at rest AES-256",
  "results": [
    {
      "chunk_id": "chk_9a12c8e4",
      "document_id": "doc_e3b0c442",
      "document_name": "Enterprise_Information_Security_Policy_v4.2.pdf",
      "page_number": 12,
      "section_heading": "Section 4.3: Data Storage Encryption Standards",
      "content": "All customer sensitive and confidential records residing on production relational databases and storage buckets must be encrypted at rest using NIST-approved AES-256 GCM or ChaCha20-Poly1305. Cryptographic keys must rotate automatically every 90 days via AWS KMS or HashiCorp Vault.",
      "rrf_score": 0.0328,
      "dense_rank": 1,
      "lexical_rank": 1
    }
  ]
}
```

---

## 4. Tool 3: `get_document_metadata`

### Purpose
Retrieves complete structural and cryptographic metadata for a specific document, including SHA-256 hash, section breakdown, total chunk count, and ingestion properties.

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["document_id"],
  "properties": {
    "document_id": {
      "type": "string",
      "description": "Unique identifier of the target document."
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["id", "filename", "file_hash", "mime_type", "file_size_bytes", "page_count", "total_chunks", "sections", "created_at"],
  "properties": {
    "id": { "type": "string" },
    "filename": { "type": "string" },
    "file_hash": { "type": "string" },
    "mime_type": { "type": "string" },
    "file_size_bytes": { "type": "integer" },
    "page_count": { "type": "integer" },
    "total_chunks": { "type": "integer" },
    "sections": {
      "type": "array",
      "items": { "type": "string" }
    },
    "created_at": { "type": "string" }
  }
}
```

### Validation Rules & Error Handling
- Validates existence of `document_id`. If not found, raises `DocumentNotFoundError` formatted as JSON-RPC error code `-32004`.

### Example Invocation
```json
{
  "name": "get_document_metadata",
  "arguments": {
    "document_id": "doc_e3b0c442"
  }
}
```

### Expected Response
```json
{
  "id": "doc_e3b0c442",
  "filename": "Enterprise_Information_Security_Policy_v4.2.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "mime_type": "application/pdf",
  "file_size_bytes": 1048576,
  "page_count": 28,
  "total_chunks": 54,
  "sections": [
    "1.0 Purpose and Scope",
    "2.0 Access Management",
    "3.0 Network Segmentation",
    "4.0 Cryptographic Controls",
    "5.0 Incident Response"
  ],
  "created_at": "2026-11-06T12:00:00Z"
}
```

---

## 5. Tool 4: `get_citation`

### Purpose
Resolves a specific chunk ID or quotation reference into a verified, ground-truth citation object complete with surrounding context and document coordinates.

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["chunk_id"],
  "properties": {
    "chunk_id": {
      "type": "string",
      "description": "Unique chunk identifier to verify and cite."
    },
    "include_surrounding_context": {
      "type": "boolean",
      "description": "Whether to return previous and subsequent chunks for surrounding context.",
      "default": false
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["chunk_id", "document_id", "document_name", "page_number", "section_heading", "exact_text", "sha256_verification"],
  "properties": {
    "chunk_id": { "type": "string" },
    "document_id": { "type": "string" },
    "document_name": { "type": "string" },
    "page_number": { "type": "integer" },
    "section_heading": { "type": "string" },
    "exact_text": { "type": "string" },
    "sha256_verification": { "type": "string" },
    "previous_context": { "type": "string", "nullable": true },
    "next_context": { "type": "string", "nullable": true }
  }
}
```

### Validation Rules & Error Handling
- Checks that `chunk_id` exists in `document_chunks`.
- Computes SHA-256 of `exact_text` to guarantee text integrity and anti-tampering.

### Example Invocation
```json
{
  "name": "get_citation",
  "arguments": {
    "chunk_id": "chk_9a12c8e4",
    "include_surrounding_context": false
  }
}
```

### Expected Response
```json
{
  "chunk_id": "chk_9a12c8e4",
  "document_id": "doc_e3b0c442",
  "document_name": "Enterprise_Information_Security_Policy_v4.2.pdf",
  "page_number": 12,
  "section_heading": "Section 4.3: Data Storage Encryption Standards",
  "exact_text": "All customer sensitive and confidential records residing on production relational databases and storage buckets must be encrypted at rest using NIST-approved AES-256 GCM or ChaCha20-Poly1305.",
  "sha256_verification": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  "previous_context": null,
  "next_context": null
}
```

---

## 6. Tool 5: `evaluate_compliance`

### Purpose
Audits one or more compliance framework requirements against the ingested document repository, categorizing each mandate into `COVERED`, `PARTIALLY_COVERED`, or `MISSING` backed by strict evidence.

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["framework_name"],
  "properties": {
    "framework_name": {
      "type": "string",
      "description": "Target framework name (e.g., 'SOC2', 'ISO27001', 'HIPAA')."
    },
    "requirement_code": {
      "type": "string",
      "description": "Optional specific requirement code to audit (e.g., 'CC6.1'). If omitted, audits all framework requirements.",
      "nullable": true
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["framework_name", "total_requirements", "coverage_summary", "findings"],
  "properties": {
    "framework_name": { "type": "string" },
    "total_requirements": { "type": "integer" },
    "coverage_summary": {
      "type": "object",
      "required": ["covered", "partially_covered", "missing", "compliance_percentage"],
      "properties": {
        "covered": { "type": "integer" },
        "partially_covered": { "type": "integer" },
        "missing": { "type": "integer" },
        "compliance_percentage": { "type": "number" }
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["requirement_code", "title", "status", "confidence_score", "evidence", "gap", "recommendation", "human_review_required"],
        "properties": {
          "requirement_code": { "type": "string" },
          "title": { "type": "string" },
          "status": { "type": "string", "enum": ["COVERED", "PARTIALLY_COVERED", "MISSING"] },
          "confidence_score": { "type": "number" },
          "evidence": {
            "type": "object",
            "nullable": true,
            "properties": {
              "document_id": { "type": "string" },
              "document_name": { "type": "string" },
              "page_number": { "type": "integer" },
              "section_heading": { "type": "string" },
              "quote": { "type": "string" }
            }
          },
          "gap": { "type": "string", "nullable": true },
          "recommendation": { "type": "string", "nullable": true },
          "human_review_required": { "type": "boolean" }
        }
      }
    }
  }
}
```

### Validation Rules & Zero-Trust Assurance Enforcement
- **Zero-Trust Assurance Rule (Phase 2.4):** If candidate evidence consists strictly of `Policy Documentation` (statements of intent, mandates, "shall", "must"), the requirement CANNOT be evaluated as `COVERED`. It is evaluated as `PARTIALLY_COVERED` with `human_review_required=True`. Full `COVERED` status mandates `Implementation Evidence` or `Operating Evidence`.
- **Mandatory Evidence Rule:** If `evidence` is null or empty, `status` CANNOT be `COVERED`.
- **Confidence Score Meaning:** The `confidence_score` is a qualitative heuristic metric (0.0 to 1.0) derived from hybrid retrieval density and assurance tier completeness, NOT a statistically calibrated probability.
- If the framework does not exist, returns `FrameworkNotFoundError`.

### Example Invocation
```json
{
  "name": "evaluate_compliance",
  "arguments": {
    "framework_name": "SOC2",
    "requirement_code": "CC6.1"
  }
}
```

### Expected Response
```json
{
  "framework_name": "SOC2",
  "total_requirements": 1,
  "coverage_summary": {
    "covered": 1,
    "partially_covered": 0,
    "missing": 0,
    "compliance_percentage": 100.0
  },
  "findings": [
    {
      "requirement_code": "CC6.1",
      "title": "Logical Access Controls",
      "status": "COVERED",
      "confidence_score": 0.94,
      "evidence": {
        "document_id": "doc_e3b0c442",
        "document_name": "Enterprise_Information_Security_Policy_v4.2.pdf",
        "page_number": 8,
        "section_heading": "Section 2.1: Multi-Factor Authentication",
        "quote": "All corporate and production system access mandates multi-factor authentication (MFA) with FIDO2 hardware tokens or TOTP authenticator applications. Passwords must be at least 16 characters and rotated annually."
      },
      "gap": null,
      "recommendation": "Maintain annual access review logs for SOC 2 Type II audit evidence.",
      "human_review_required": false
    }
  ]
}
```

---

## 7. Tool 6: `gap_analysis`

### Purpose
Performs deep-dive discrepancy analysis across identified `PARTIALLY_COVERED` and `MISSING` requirements, generating prioritized remediation playbooks with severity classifications.

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["framework_name"],
  "properties": {
    "framework_name": {
      "type": "string",
      "description": "Target framework name."
    },
    "severity_filter": {
      "type": "string",
      "description": "Optional filter ('All', 'Critical', 'High', 'Medium', 'Low').",
      "default": "All"
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["framework_name", "total_gaps", "remediation_roadmap"],
  "properties": {
    "framework_name": { "type": "string" },
    "total_gaps": { "type": "integer" },
    "remediation_roadmap": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["priority_rank", "requirement_code", "title", "current_status", "severity", "identified_gap", "required_controls", "estimated_effort_days"],
        "properties": {
          "priority_rank": { "type": "integer" },
          "requirement_code": { "type": "string" },
          "title": { "type": "string" },
          "current_status": { "type": "string", "enum": ["PARTIALLY_COVERED", "MISSING"] },
          "severity": { "type": "string", "enum": ["Critical", "High", "Medium", "Low"] },
          "identified_gap": { "type": "string" },
          "required_controls": { "type": "array", "items": { "type": "string" } },
          "estimated_effort_days": { "type": "integer" }
        }
      }
    }
  }
}
```

### Validation Rules & Effort Estimation Disclaimers
- **Engineering Planning Estimates:** The `estimated_effort_days` metric represents an indicative engineering planning estimate based on typical industry implementation complexity, NOT a factual commitment or binding timeline.
- **Severity Ranking:** Gaps are strictly sorted with Critical first, then High, Medium, Low; MISSING gaps are prioritized ahead of PARTIALLY_COVERED gaps within the same tier.

### Example Invocation
```json
{
  "name": "gap_analysis",
  "arguments": {
    "framework_name": "ISO27001",
    "severity_filter": "High"
  }
}
```

### Expected Response
```json
{
  "framework_name": "ISO27001",
  "total_gaps": 1,
  "remediation_roadmap": [
    {
      "priority_rank": 1,
      "requirement_code": "A.12.1.2",
      "title": "Change Management Procedure",
      "current_status": "PARTIALLY_COVERED",
      "severity": "High",
      "identified_gap": "The policy mandates pull request approvals but lacks documented emergency rollback procedures and post-incident review timelines.",
      "required_controls": [
        "Document formal Emergency Change Procedure (ECP)",
        "Establish 48-hour post-incident review SLA"
      ],
      "estimated_effort_days": 5
    }
  ]
}
```

---

## 8. Tool 7: `get_related_knowledge`

### Purpose
Explores the Obsidian-inspired knowledge graph, retrieving linked concept notes, forward `[[Wiki Links]]`, backlinks, and related controls stored in SQLite.

### Input Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["node_slug"],
  "properties": {
    "node_slug": {
      "type": "string",
      "description": "Slug of the root knowledge node (e.g., 'mfa-policy', 'soc2-cc6-1')."
    },
    "depth": {
      "type": "integer",
      "description": "Graph traversal depth (1 or 2).",
      "default": 1,
      "minimum": 1,
      "maximum": 2
    }
  },
  "additionalProperties": false
}
```

### Output Schema (JSON Schema)
```json
{
  "type": "object",
  "required": ["root_node", "outgoing_links", "backlinks", "related_requirements"],
  "properties": {
    "root_node": {
      "type": "object",
      "required": ["slug", "title", "node_type", "content_markdown"],
      "properties": {
        "slug": { "type": "string" },
        "title": { "type": "string" },
        "node_type": { "type": "string" },
        "content_markdown": { "type": "string" }
      }
    },
    "outgoing_links": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "target_slug": { "type": "string" },
          "link_text": { "type": "string" },
          "context_snippet": { "type": "string" }
        }
      }
    },
    "backlinks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source_slug": { "type": "string" },
          "source_title": { "type": "string" },
          "context_snippet": { "type": "string" }
        }
      }
    },
    "related_requirements": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

### Example Invocation
```json
{
  "name": "get_related_knowledge",
  "arguments": {
    "node_slug": "encryption-at-rest",
    "depth": 1
  }
}
```

### Expected Response
```json
{
  "root_node": {
    "slug": "encryption-at-rest",
    "title": "Data Storage Encryption Standard",
    "node_type": "control",
    "content_markdown": "# Data Storage Encryption Standard\nEnforces [[aes-256-standard]] across databases. Referenced by [[soc2-cc6-1]] and [[iso27001-a12-3]]."
  },
  "outgoing_links": [
    { "target_slug": "aes-256-standard", "link_text": "AES-256 Standard", "context_snippet": "Enforces [[aes-256-standard]] across databases." },
    { "target_slug": "soc2-cc6-1", "link_text": "SOC 2 CC6.1", "context_snippet": "Referenced by [[soc2-cc6-1]]." }
  ],
  "backlinks": [
    { "source_slug": "cloud-infrastructure-policy", "source_title": "Cloud Infrastructure Policy", "context_snippet": "RDS clusters comply with [[encryption-at-rest]]." }
  ],
  "related_requirements": ["SOC2:CC6.1", "ISO27001:A.12.3.1"]
}
```


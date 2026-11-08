# VERITY: Architecture Specification

**Project:** VERITY – Enterprise Document Intelligence & Compliance Agent  
**Document:** System Architecture Blueprint  
**Classification:** Technical Assessment Blueprint (Confidential)  
**Author:** Principal AI Architect & Senior Python Engineer  
**Date:** November 2026  

---

## 1. High-Level Architecture Overview

VERITY is structured around a decoupled, layered micro-architecture emphasizing strict process boundaries, genuine protocol mediation via the Model Context Protocol (MCP), and bounded agent orchestration.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Browser)"]
        UI["React 19 SPA (Vite + TypeScript)"]
        Tailwind["Tailwind CSS + Lucide Icons"]
        Charts["Recharts Compliance Visualizer"]
    end

    subgraph APILayer ["Application & API Gateway (FastAPI)"]
        API["FastAPI REST Endpoints (/api/v1)"]
        SSE["Server-Sent Events Stream (/api/v1/chat/stream)"]
        DocRouter["Document Ingestion API (/api/v1/documents)"]
        CompRouter["Compliance Audit API (/api/v1/compliance)"]
    end

    subgraph AgentLayer ["Bounded Orchestration Engine"]
        Orchestrator["Agent Orchestrator"]
        IntentParser["Task & Intent Classifier"]
        BudgetController["Bounded Step Counter (Max 5 Tools)"]
        CitationValidator["Citation Grounding Verifier"]
        FallbackEngine["Deterministic Fallback Engine"]
    end

    subgraph MCPLayer ["Protocol Boundary (MCP stdio Transport)"]
        MCPClient["Official MCP Python SDK Client"]
        Pipe[("stdio Subprocess IPC")]
        MCPServer["FastMCP Compliance Server (Separate Subprocess)"]
    end

    subgraph ToolRegistry ["Enterprise MCP Tools"]
        T1["list_documents"]
        T2["search_documents (Hybrid RRF)"]
        T3["get_document_metadata"]
        T4["get_citation"]
        T5["evaluate_compliance"]
        T6["gap_analysis"]
        T7["get_related_knowledge"]
    end

    subgraph StorageLayer ["Persistence & Vector Store (Zero Cloud)"]
        SQLite[("SQLite 3 (Data + FTS5 BM25 + Wiki Graph)")]
        FAISS[("FAISS CPU (384d Dense Vector Index)")]
        DocStore[("Local Disk (data/uploads - SHA-256 Verified)")]
    end

    subgraph AIEngine ["Local Inference & Embedding Engine"]
        STEmbed["sentence-transformers (all-MiniLM-L6-v2 on CPU)"]
        OllamaLocal["Ollama Local Daemon (qwen2.5:1.5b on AVX2 CPU)"]
    end

    UI -->|HTTP / REST & SSE| API
    API --> DocRouter
    API --> CompRouter
    API --> Orchestrator
    Orchestrator --> IntentParser
    IntentParser --> BudgetController
    BudgetController --> MCPClient
    BudgetController -.->|LLM Offline| FallbackEngine
    FallbackEngine --> MCPClient
    
    MCPClient <==>|MCP JSON-RPC over stdio| Pipe <==> MCPServer
    MCPServer --> ToolRegistry
    
    T1 & T3 --> SQLite
    T2 --> SQLite
    T2 --> FAISS
    T2 --> STEmbed
    T4 --> SQLite
    T5 & T6 --> OllamaLocal
    T5 & T6 --> T2
    T7 --> SQLite
    
    DocRouter --> DocStore
    DocRouter --> STEmbed
    STEmbed --> FAISS
    DocRouter --> SQLite
    
    Orchestrator --> CitationValidator
    CitationValidator --> T4
    CitationValidator --> OllamaLocal
```

---

## 2. Process Boundaries & IPC Architecture

A critical architectural mandate of VERITY is **genuine MCP protocol isolation**. The application explicitly separates the Agent/API gateway runtime from the MCP Tool execution runtime.

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent Orchestrator (FastAPI Process)
    participant Client as MCP Client (mcp.client.stdio)
    participant Pipe as stdin / stdout Subprocess Pipe
    participant Server as FastMCP Server (fastmcp Process)
    participant Engine as Storage & Retrieval Engine

    Note over Agent,Server: Phase A: MCP Protocol Handshake
    Agent->>Client: Initialize MCP Session
    Client->>Pipe: Spawn `python -m src.mcp_server.server`
    Pipe->>Server: Process Spawned (stdio attached)
    Client->>Pipe: JSON-RPC "initialize" (capabilities, version)
    Pipe->>Server: Protocol Handshake
    Server-->>Pipe: Initialized (tools list, server info)
    Pipe-->>Client: Connection Ready

    Note over Agent,Server: Phase B: Bounded Tool Execution
    Agent->>Client: call_tool("search_documents", {"query": "encryption at rest"})
    Client->>Pipe: JSON-RPC "tools/call" (id: 1, name: "search_documents", args)
    Pipe->>Server: Parse & Validate Pydantic Schema
    Server->>Engine: Hybrid Search (FAISS + SQLite FTS5)
    Engine-->>Server: Ranked Chunks & Relevance Scores
    Server-->>Pipe: JSON-RPC Response (result: [{chunk_id, text, score}])
    Pipe-->>Client: Validated Tool Result
    Client-->>Agent: Evidence Bundle (Step 1 of 5 budget consumed)
```

---

## 3. Ingestion & Hybrid Indexing Pipeline

```mermaid
flowchart TD
    RawFile["Uploaded Document (PDF / DOCX / TXT)"] --> Validation{"MIME & Size Check (<=25MB)"}
    Validation -- Invalid --> Reject["HTTP 400: Unsupported or Oversized"]
    Validation -- Valid --> Hash["Compute SHA-256 Hash"]
    Hash --> DupCheck{"Exists in SQLite?"}
    DupCheck -- Yes --> Skip["Return Existing Document Record"]
    DupCheck -- No --> Store["Write to data/uploads/{hash}.{ext}"]
    
    Store --> Parser["PyMuPDF / docx Parser"]
    Parser --> Clean["Sanitize & Strip Instruction Scripts"]
    Clean --> Chunking["Sliding Window Chunker (400 tokens / 50 overlap)"]
    
    Chunking --> Metadata["Attach Page No, Section Heading, Chunk Index"]
    Metadata --> DBInsert["Insert into SQLite `documents` & `document_chunks`"]
    DBInsert --> FTSInsert["Index into SQLite `chunks_fts` (FTS5 BM25)"]
    
    Metadata --> EmbedModel["sentence-transformers (all-MiniLM-L6-v2)"]
    EmbedModel --> Vectors["384-Dimensional Dense Vectors"]
    Vectors --> FAISSAdd["faiss.IndexFlatL2.add(vectors)"]
    FAISSAdd --> FAISSSave["Persist to data/faiss/index.faiss"]
    
    DBInsert --> KnowledgeGen["Extract Entities & Links -> `knowledge_nodes`"]
```

---

## 4. Hybrid Retrieval Architecture (FAISS + SQLite FTS5)

To achieve maximum retrieval precision for technical compliance, VERITY employs **hybrid reciprocal rank fusion (RRF)**:

1. **Dense Vector Search (Semantic Match):**
   - Query is embedded with `all-MiniLM-L6-v2` into vector $q \in \mathbb{R}^{384}$.
   - FAISS searches the top-$K_d$ nearest neighbors using Euclidean L2 distance.
   - Captures contextual similarity and conceptual rephrasing (e.g., "protecting data" $\leftrightarrow$ "cryptographic controls").

2. **Lexical BM25 Search (Exact Keyword Match):**
   - Query terms are tokenized and queried against the SQLite `chunks_fts` virtual table.
   - BM25 scoring isolates exact clause numbers, control codes (e.g., "A.12.3.1", "CC6.1"), and exact domain acronyms.

3. **Reciprocal Rank Fusion (RRF):**
   - The two ranked candidate lists are merged using rank positions:
     $$\text{Score}_{\text{RRF}}(d) = \frac{1}{60 + \text{rank}_{\text{dense}}(d)} + \frac{1}{60 + \text{rank}_{\text{lexical}}(d)}$$
   - Chunks appearing in both candidate lists are elevated to top rank.

---

## 5. Bounded Agent Orchestration & Deterministic Fallback

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> IngestingQuery: User Query Received
    IngestingQuery --> ClassifyIntent: Parse Query Intent
    
    ClassifyIntent --> CheckLLMAvailability: Verify Ollama Health
    
    state "Active LLM Workflow" as LLMMode {
        SelectTools --> ValidateBudget: Check Tool Budget (< 5)
        ValidateBudget --> CallMCPTool: Tool in Allowlist
        CallMCPTool --> ParseToolResult: stdio IPC Response
        ParseToolResult --> DecideNextStep: Check if sufficient evidence
        DecideNextStep --> ValidateBudget: Needs additional evidence
        DecideNextStep --> VerifyCitations: Evidence complete
        VerifyCitations --> SynthesizeResponse: Generate Grounded Answer
    }
    
    state "Deterministic Fallback Workflow" as FallbackMode {
        DirectToolDispatch --> ExecuteDeterministicSearch: Call search_documents directly
        ExecuteDeterministicSearch --> ExtractDirectCitations: Rank & extract top excerpts
        ExtractDirectCitations --> FormatTemplate: Assemble structured deterministic card
    }

    CheckLLMAvailability --> SelectTools: Ollama Online
    CheckLLMAvailability --> DirectToolDispatch: Ollama Offline / Timeout
    
    SynthesizeResponse --> RenderResult: Return Grounded Result
    FormatTemplate --> RenderResult: Return `[Deterministic Output]`
    RenderResult --> Idle
```

---

## 6. Technology Stack Rationale

| Layer | Component | Choice | Justification |
| :--- | :--- | :--- | :--- |
| **Frontend** | Framework | React 19 + TypeScript + Vite | Optimal build performance, type safety, modular component lifecycle. |
| **Frontend** | Styling & UI | Tailwind CSS v4 + Lucide Icons | Utility-first responsive design, zero runtime CSS overhead, accessible UI. |
| **Frontend** | Charts | Recharts | Declarative SVG rendering for framework coverage and gap distributions. |
| **Backend** | API Framework | FastAPI + Pydantic v2 | High-throughput asynchronous endpoints, automatic OpenAPI schema generation. |
| **Agent / Protocol** | Tool Protocol | Official MCP Python SDK + FastMCP | Open standard for LLM tool invocation, strict isolation, stdio process pipes. |
| **Embeddings** | Dense Vector Model | `sentence-transformers` (`all-MiniLM-L6-v2`) | Compact (80 MB), ultra-fast CPU inference, top MTEB retrieval score for 384d. |
| **Vector Store** | Vector Index | FAISS CPU (`faiss-cpu`) | Native C++ implementation, minimal memory overhead, zero cloud dependency. |
| **Lexical Search** | Full-Text Search | SQLite FTS5 | Zero-config embedded BM25 search, ACID compliant, co-located with relational data. |
| **Local LLM** | Inference Engine | Ollama (`qwen2.5:1.5b` Q4_K_M) | 986 MB footprint, fast CPU token generation, outstanding structured JSON compliance. |
| **Doc Processing** | Document Parsers | PyMuPDF (`pymupdf`) + `python-docx` | High-fidelity layout and text extraction without heavy OCR or headless browsers. |


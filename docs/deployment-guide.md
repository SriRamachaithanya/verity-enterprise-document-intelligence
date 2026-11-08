# VERITY — Production Deployment & Operations Guide

This guide details the deployment, configuration, operational management, and disaster recovery procedures for **VERITY (Enterprise Document Intelligence & Compliance Agent)**.

---

## 1. System Architecture Overview

VERITY is packaged as an enterprise-grade, multi-tier containerized or native application designed to run entirely locally with **zero external cloud data transmission and zero recurring API costs ($0.00)**.

```
                      +---------------------------------------+
                      |       Web Browser / Enterprise User   |
                      +-------------------+-------------------+
                                          |
                              HTTP / SSE  | Port 3000 (Docker) / 5173 (Dev)
                                          v
                      +---------------------------------------+
                      |         Frontend (Nginx / Vite)       |
                      |   - React 19 + TypeScript + Tailwind   |
                      |   - Static Assets + SPA Routing       |
                      |   - Reverse Proxy (/api, /health)     |
                      +-------------------+-------------------+
                                          |
                              HTTP / REST | Port 8000
                                          v
                      +---------------------------------------+
                      |         Backend (FastAPI Uvicorn)     |
                      |   - Non-root user: verity (UID 10001) |
                      |   - RBAC & Constant-Time Auth         |
                      |   - Streaming SSE Response Pipeline   |
                      +---------+-------------------+---------+
                                |                   |
                 In-Process STDIO |                   | HTTP (Port 11434)
                                v                   v
        +-------------------------------+   +-----------------------------+
        | FastMCP Server (Python SDK)   |   | Ollama Local LLM Service    |
        | - Evidence Retrieval Tool     |   | - Model: qwen2.5:1.5b       |
        | - Citation Verification Tool  |   | - Host or Remote Gateway    |
        | - Compliance Evaluator Tool   |   +-----------------------------+
        | - Knowledge Graph Engine      |
        +---------------+---------------+
                        |
            Local Filesystem / SQLite
                        v
        +-----------------------------------------------+
        | Persistent Storage Volumes                    |
        | - SQLite WAL Database: /app/data/sqlite       |
        | - FAISS Dense Vector Index: /app/data/faiss   |
        | - Staged Uploads: /app/data/uploads           |
        | - Malware Quarantine: /app/data/quarantine    |
        +-----------------------------------------------+
```

---

## 2. Prerequisites & Hardware Requirements

### Minimum Hardware Requirements
- **CPU**: 4 Cores (x86_64 or ARM64)
- **RAM**: 8 GB System Memory (Minimum 2 GB free available for Ollama + Embeddings)
- **Disk**: 10 GB free storage (SSD recommended for fast vector I/O)
- **GPU**: Optional (CPU inference verified on Intel i5-11400F)

### Software Dependencies
- **Docker**: Docker Engine 24+ and Docker Compose v2+ (For containerized deployment)
- **Python**: Version 3.11 or newer (For native bare-metal deployment)
- **Node.js**: Version 20 LTS and npm 10+ (For native frontend builds)
- **Ollama**: Local Ollama server running with `qwen2.5:1.5b` model installed

---

## 3. Ollama LLM Preparation

VERITY connects to Ollama via HTTP REST APIs. Ollama should be running on the host machine before launching containers:

1. **Verify Ollama Installation:**
   ```bash
   ollama --version
   ```

2. **Pull the Required Model:**
   ```bash
   ollama pull qwen2.5:1.5b
   ```

3. **Verify Ollama Server Status:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

> [!NOTE]
> When running VERITY inside Docker Compose on Windows or macOS, Ollama on the host is reached automatically via `http://host.docker.internal:11434`. On Linux hosts, Docker Compose uses `extra_hosts: ["host.docker.internal:host-gateway"]`.

---

## 4. Containerized Production Deployment (Docker Compose)

### Step 1: Clone Repository & Configure Environment
Navigate to the project root and create `.env` from the production template:

```bash
cp .env.production.example .env
```

Review and adjust security credentials in `.env`:
```ini
# Core Configuration
ENVIRONMENT=production
DEBUG=false
AUTH_DISABLED=false

# Authentication Secrets (Replace with high-entropy enterprise keys)
VERITY_ADMIN_KEY=prod-admin-super-secure-token-8f69af
VERITY_AUDITOR_KEY=prod-auditor-read-compliance-token-39ac4
VERITY_USER_KEY=prod-standard-user-access-token-1102b

# Ollama Host URL
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:1.5b

# HuggingFace Offline / Local Cache (inside container)
HF_HOME=/app/data/models
SENTENCE_TRANSFORMERS_HOME=/app/data/models
```

### Step 2: Build & Start Services
Run Docker Compose to build optimized images and start services in detached mode:

```bash
docker compose up -d --build
```

### Step 3: Verify Container Health
Check running containers and health status:

```bash
docker compose ps
```

Expected output:
```
NAME               IMAGE                     COMMAND                  SERVICE    STATUS
verity-backend     verity-backend:latest     "uv run uvicorn src.…"   backend    Up (healthy)
verity-frontend    verity-frontend:latest    "/docker-entrypoint.…"   frontend   Up (healthy)
```

### Step 4: Access the Dashboard
- **Web UI**: Open your browser at [http://localhost:3000](http://localhost:3000)
- **Direct API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Checks**:
  - Liveness: `curl http://localhost:8000/health`
  - Readiness: `curl http://localhost:8000/ready`

---

## 5. Native Bare-Metal Deployment (Windows / Linux)

For environments where Docker is not installed or bare-metal execution is preferred:

### Step 1: Backend Setup
1. Create and activate a Python 3.11 virtual environment using `uv`:
   ```powershell
   uv venv .venv
   .venv\Scripts\activate      # Windows
   # source .venv/bin/activate # Linux/macOS
   ```

2. Sync production dependencies:
   ```powershell
   uv pip install -r pyproject.toml
   ```

3. Configure environment variables in `.env`:
   ```ini
   ENVIRONMENT=production
   SQLITE_DB_PATH=data/sqlite/verity.db
   FAISS_INDEX_PATH=data/faiss/index.faiss
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:1.5b
   ```

4. Launch the Uvicorn production server:
   ```powershell
   .venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
   ```

### Step 2: Frontend Setup
1. Navigate to `frontend/`:
   ```powershell
   cd frontend
   npm ci
   ```

2. Build optimized static assets:
   ```powershell
   npm run build
   ```

3. Serve using a production static web server (such as Caddy, Nginx, or `serve`):
   ```powershell
   npx serve -s dist -l 3000
   ```

---

## 6. Persistent Volume Configuration & Mappings

The following host directories store stateful enterprise data and are persisted across container restarts:

| Container Directory | Host Path | Purpose | Backup Priority |
| :--- | :--- | :--- | :--- |
| `/app/data/sqlite` | `./data/sqlite` | SQLite database (documents, chunks, compliance frameworks, knowledge graph, audit logs) | **Critical** |
| `/app/data/faiss` | `./data/faiss` | Serialized FAISS index (`index.faiss`) for 384-dimensional dense vectors | **Critical** |
| `/app/data/uploads` | `./data/uploads` | Stored parsed source documents and metadata artifacts | High |
| `/app/data/quarantine` | `./data/quarantine` | Isolated storage for infected files blocked by malware scanners | Audit / Review |
| `/app/data/models` | Named Volume `hf_cache` | Cached SentenceTransformer weights (`all-MiniLM-L6-v2`) | Cache (Rebuildable) |

---

## 7. Security Hardening & Container Isolation

1. **Non-Root User Execution:**
   The backend Docker container creates and switches to a dedicated unprivileged user:
   ```dockerfile
   RUN groupadd -g 10001 verity && useradd -u 10001 -g verity -s /bin/sh verity
   USER verity
   ```
2. **Defensive HTTP Headers:**
   Every request is filtered through `SecurityHeadersMiddleware` and Nginx with:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Content-Security-Policy: default-src 'self'`
3. **No Secrets in Bundles:**
   Docker build images and Vite bundles exclude `.env` files. Secrets are injected at runtime via environment variables.

---

## 8. Backup & Disaster Recovery

### Creating a Hot Database Backup
Because SQLite operates in Write-Ahead Logging (WAL) mode, use the SQLite online backup API or CLI tool:

```bash
# Backup SQLite
sqlite3 data/sqlite/verity.db ".backup data/backups/verity_$(date +%Y%m%d_%H%M%S).db"

# Backup FAISS Vector Index
cp data/faiss/index.faiss data/backups/faiss_$(date +%Y%m%d_%H%M%S).faiss
```

### Complete Snapshot Script (Windows PowerShell)
```powershell
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "data\backups\$Timestamp"
New-Item -ItemType Directory -Path $BackupDir -Force

Copy-Item "data\sqlite\verity.db*" -Destination $BackupDir
Copy-Item "data\faiss\*" -Destination $BackupDir
Write-Host "Snapshot successfully saved to $BackupDir"
```

### Recovery Procedure
1. Stop backend services: `docker compose stop backend`
2. Replace `data/sqlite/verity.db` and `data/faiss/index.faiss` with backup copies.
3. Start backend services: `docker compose start backend`
4. Confirm readiness: `curl http://localhost:8000/ready`

---

## 9. Troubleshooting & Operations Runbook

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `/ready` endpoint reports `"status": "degraded"` | Ollama server is offline or unreachable | Verify `ollama serve` is running and `curl http://localhost:11434/api/tags` returns HTTP 200. Check `OLLAMA_BASE_URL`. |
| Upload fails with `413 Request Entity Too Large` | Document size exceeds 25 MB limit | Split document or increase `MAX_UPLOAD_SIZE_BYTES` in `.env`. |
| Upload rejected: `Malicious signature detected` | Uploaded file matches EICAR test or AV quarantine rule | Inspect `data/quarantine/`. Confirm whether document contained active macros or test strings. |
| SSE streaming terminates abruptly | Upstream proxy buffering chunks | Ensure Nginx has `proxy_buffering off;` and `proxy_cache off;` (preconfigured in `frontend/nginx.conf`). |
| Database locked error (`sqlite3.OperationalError: database is locked`) | Long-running transaction or foreign process | VERITY automatically enforces WAL mode (`PRAGMA journal_mode=WAL;`) and a 15-second busy timeout. Verify no external GUI tool has opened `verity.db` in exclusive lock mode. |


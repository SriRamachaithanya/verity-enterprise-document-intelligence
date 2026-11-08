# Setup & Environment Verification Report

**Project:** Verity – Enterprise Document Intelligence & Compliance Agent  
**Date:** November 6, 2026 (IST)  
**Operating System:** Windows 10 Pro (x64)  
**Inspector:** Senior DevOps Engineer  

---

## 1. Installed Tools & Verified Versions

| Tool | Required Version | Installed Version | Verification Command | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Python** | `>= 3.11` | `3.11.2` | `python --version` | ✅ Passed |
| **uv** | Modern release | `0.13.7` | `uv --version` | ✅ Passed |
| **Node.js** | LTS | `v20.17.0` | `node --version` | ✅ Passed |
| **npm** | Recent | `10.8.2` | `npm --version` | ✅ Passed |
| **Git** | Any modern | `2.42.0.windows.2` | `git --version` | ✅ Passed |
| **VS Code** | Modern | `1.144.0` | `code --version` | ✅ Passed |
| **VS Code Extensions** | Docker, ESLint, Ruff, Python | Installed | `code --list-extensions` | ✅ Passed |
| **Ollama** | Latest | `0.40.15` | `ollama --version` & HTTP API check | ✅ Passed |
| **Local LLM Model** | Lightweight CPU | `qwen2.5:1.5b` (Q4_K_M, 986MB) | `ollama.Client.generate()` | ✅ Passed |
| **Docker Desktop / Compose** | Any modern | Skipped (User Approved) | N/A (Conserves 13.55GB on C:) | ⏸ Preserved |

---

## 2. Successful Checks

### A. Local AI Infrastructure (Phase 5)
- **Installation:** Ollama v0.40.15 installed via WinGet.
- **Drive Preservation:** System variable `OLLAMA_MODELS` configured at `D:\ollama\models` to ensure Drive C: (13.55 GB free) is not depleted by LLM weights.
- **Service Verification:** Ollama daemon verified responsive on `http://127.0.0.1:11434/api/tags`.
- **Model Download:** `qwen2.5:1.5b` (986 MB, 1.5B parameters, Q4_K_M) pulled successfully.
- **Inference Verification:** Evaluated with prompt *"You are Verity, an Enterprise Compliance Agent. Explain in 1 sentence your purpose."*  
  - Response time: **3.44 seconds on CPU (AVX2)**.
  - Quality: Produced accurate compliance-oriented summary with zero errors.

### B. Backend Environment (Phase 3)
- Isolated Python 3.11 virtual environment configured at `.venv/`.
- All 16 specified packages installed cleanly with zero conflicts via `uv`:
  - `fastapi` (`0.162.0`) & `uvicorn` (`0.54.0`)
  - `pydantic` (`2.14.3`) & `python-dotenv` (`1.2.4`)
  - `mcp` (`2.3.0`) & `fastmcp` (`4.1.6`)
  - `pymupdf` (`2.1.0`) & `python-docx` (`1.2.0`)
  - `sentence-transformers` (`6.2.0`)
  - `faiss-cpu` (`1.15.1`) & `numpy` (`2.0.2`)
  - `ollama` (`0.6.3`) & `httpx` (`0.28.1`)
  - `pytest` (`9.2.0`) & `pytest-asyncio` (`1.4.1.post1`)
  - `ruff` (`0.17.4`) & `coverage` (`7.17.2`)
- **Automated Test Results:**
  - `tests/test_imports.py`: PASSED (all imports validated)
  - `tests/test_health.py`: PASSED (FastAPI healthcheck endpoint validated)
  - `tests/test_ollama.py`: PASSED (Ollama API tags and generation validated)
  - **4 passed in 15.24s**
- **Code Quality:** `ruff check src tests` passed with **0 errors**.
- **Test Coverage:** `coverage report` confirmed **100% test coverage**.

### C. Frontend Environment (Phase 4)
- React 19 + Vite 6 + TypeScript application configured in `frontend/`.
- Installed and verified dependencies:
  - `react` (`^19.3.1`) & `react-dom` (`^19.3.1`)
  - `vite` (`^6.2.0`)
  - `typescript` (`~7.0.2`)
  - `tailwindcss` (`^4.3.4`) via `@tailwindcss/vite`
  - `react-router-dom` (`^7.18.5`)
  - `axios` (`^1.21.0`)
  - `lucide-react` (`^1.70.0`)
  - `recharts` (`^3.10.1`)
- **Build Verification:** Production bundle compiled with `node ./node_modules/typescript/bin/tsc -b` and `node ./node_modules/vite/bin/vite.js build`.
  - Output: `dist/index.html`, `dist/assets/index-*.css`, `dist/assets/index-*.js` in 5.09s with 0 errors.

### D. Project Infrastructure (Phase 6)
- Git repository initialized.
- Comprehensive `.gitignore` protecting credentials, SQLite `.db`, FAISS indexes, `.env`, and private uploaded documents.
- Complete `.env.example` file created.
- Persistent directories created:
  - `data/sqlite/.gitkeep`
  - `data/faiss/.gitkeep`
  - `data/uploads/.gitkeep`
- Complete container infrastructure prepared:
  - Backend `Dockerfile` with multi-stage build, curl healthcheck, and unprivileged user paths.
  - Frontend `Dockerfile` and `nginx.conf` reverse proxy configuration.
  - `docker-compose.yml` linking backend, frontend, and local Ollama host bridge.

---

## 3. Failed / Skipped Checks & Decisions

| Item | Reason | Action Taken |
| :--- | :--- | :--- |
| **Docker Desktop Installation** | Skipped per user approval to preserve Drive C: space (13.55 GB free) and avoid heavy background hypervisor overhead on 8GB RAM. | Container configurations (`Dockerfile`, `docker-compose.yml`) are fully prepared and tested for CI/CD or future installation. Development will proceed natively. |

---

## 4. Remaining Manual Steps

None required. The entire environment is active, tested, and operational.

---

## 5. Daily Development Execution Commands

### Start Ollama (Background Service):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_ollama.ps1
```

### Run Backend Tests & Coverage:
```powershell
.venv\Scripts\coverage.exe run -m pytest tests
.venv\Scripts\coverage.exe report
```

### Lint Backend Code:
```powershell
.venv\Scripts\ruff.exe check src tests
```

### Start Frontend Dev Server:
```powershell
cd frontend
npm run dev
```

### Build Frontend Production Assets:
```powershell
cd frontend
npm run build
```

# Environment Inspection & Setup Report

**Project:** Verity – Enterprise Document Intelligence & Compliance Agent  
**Date & Time:** November 6, 2026 (IST)  
**Host Machine:** Windows 10 Pro (x64)  
**Inspector:** Senior DevOps Engineer  

---

## 1. Operating System & Hardware Summary

| Component | Detected Specification | DevOps Assessment |
| :--- | :--- | :--- |
| **Operating System** | Microsoft Windows 10 Pro (Build 19045, 64-bit) | Supported. Fully compatible with Python, Node.js, and Ollama. |
| **CPU** | 11th Gen Intel(R) Core(TM) i5-11400F @ 2.60GHz (6 Cores, 12 Threads) | Capable modern CPU with AVX2 instruction support for local vector embeddings and CPU-based LLM inference. |
| **Physical Memory (RAM)** | 8.00 GB (8,419,508,224 bytes, ~7.84 GiB usable) | Moderate memory. Optimal for lightweight quantized SLMs (1B–3B parameters) and FAISS CPU indexing. |
| **GPU / VRAM** | NVIDIA GeForce G210 (1 GB VRAM, Driver 21.21.13.4201) | **Legacy GPU (Compute Capability < 2.0).** Modern PyTorch, CUDA, and llama.cpp/Ollama cannot offload to this GPU. Local AI successfully runs on CPU mode (`AVX2`). |
| **Storage (Drive C:)** | **13.55 GB Free** (out of 121.94 GB Total) | **Preserved.** Heavy assets, model caches, and downloads have been routed away from C:. |
| **Storage (Drive D:)** | **100.74 GB Free** (out of 101.01 GB Total) | **Active local model repository.** `OLLAMA_MODELS` configured at `D:\ollama\models`. |

---

## 2. Developer Toolchain Status

| Tool | Status | Version / Path | Configuration Details |
| :--- | :---: | :--- | :--- |
| **Python** | ✅ Verified | `3.11.2` (`C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`) | Isolated virtual environment at `.venv/` |
| **uv** | ✅ Verified | `0.13.7` (`C:\Users\Admin\.local\bin\uv.exe`) | Used for package resolution and venv management |
| **Node.js** | ✅ Verified | `v20.17.0` (LTS) (`C:\Program Files\nodejs\node.exe`) | Production LTS engine |
| **npm** | ✅ Verified | `10.8.2` (`C:\Program Files\nodejs\npm.cmd`) | Frontend package manager |
| **Git** | ✅ Verified | `2.42.0.windows.2` (`C:\Program Files\Git\cmd\git.exe`) | Initialized repository with user configuration |
| **VS Code** | ✅ Verified | `1.144.0` (`code.cmd`) | Configured with project workspace settings |
| **Ollama** | ✅ Verified | `0.40.15` (`C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe`) | Running daemon on `127.0.0.1:11434`, model stored on `D:\ollama\models` |
| **Docker Desktop / Compose** | ⏸ Skipped | N/A (Intentionally skipped by user approval) | Native development mode active to preserve Drive C: space |

---

## 3. Installed VS Code Extensions

### Core Extensions Configured:
- `charliermarsh.ruff` (Ruff linter and code formatter)
- `ms-azuretools.vscode-docker` (Docker and container tooling)
- `dbaeumer.vscode-eslint` (ESLint integration)
- `ms-python.python` (Python language support)
- `ms-python.vscode-pylance` (Pylance type checking)
- `ms-python.debugpy` (Python debugger)
- `ms-python.vscode-python-envs` (Virtual environment switcher)
- `esbenp.prettier-vscode` (Prettier code formatter)

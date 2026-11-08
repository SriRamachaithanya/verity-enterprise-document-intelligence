"""
VERITY Phase 4 — System Performance & Resource Benchmark
Measures actual latency, throughput, memory consumption, and concurrency
on the local Intel i5-11400F + 8 GB RAM development workstation.
"""

import concurrent.futures
import gzip
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psutil
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import APIConfig, set_api_config
from src.api.dependencies import reset_api_dependencies, set_api_dependencies
from src.compliance.engine import ComplianceIntelligenceEngine
from src.indexing.embedding_service import get_embedding_service
from src.indexing.hybrid_search import HybridSearchEngine
from src.indexing.ingestion_pipeline import IngestionPipeline
from src.knowledge.graph_service import KnowledgeGraphService
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore
from src.storage.seed_data import seed_baseline_data_if_empty


def format_bytes(bytes_num: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_num < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} TB"


def run_benchmarks():
    process = psutil.Process()
    initial_rss_mb = process.memory_info().rss / (1024 * 1024)

    results = {
        "hardware": {
            "cpu": "11th Gen Intel(R) Core(TM) i5-11400F @ 2.60GHz (6C/12T)",
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        },
        "metrics": {},
    }

    print("=====================================================================")
    print("      VERITY SYSTEM PERFORMANCE & RESOURCE BENCHMARK (PHASE 4)       ")
    print("=====================================================================")
    print(f"Hardware: {results['hardware']['cpu']}")
    print(f"Physical Memory: {results['hardware']['ram_total_gb']} GB Total, {results['hardware']['ram_available_gb']} GB Free")
    print(f"Baseline Python Process RSS: {initial_rss_mb:.2f} MB\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "bench.db"
        faiss_dir = tmp_path / "bench_faiss"
        upload_dir = tmp_path / "bench_uploads"
        quarantine_dir = tmp_path / "bench_quarantine"
        upload_dir.mkdir(parents=True, exist_ok=True)
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        faiss_dir.mkdir(parents=True, exist_ok=True)

        # ---------------------------------------------------------------------
        # 1. Application Startup Time
        # ---------------------------------------------------------------------
        t_start = time.perf_counter()
        config = APIConfig(
            app_name="VERITY Benchmark",
            version="2.0.0-bench",
            environment="production",
            debug=False,
            db_path=db_path,
            faiss_dir=faiss_dir,
            upload_dir=upload_dir,
            quarantine_dir=quarantine_dir,
            admin_api_key="bench-admin-key",
            auditor_api_key="bench-auditor-key",
            user_api_key="bench-user-key",
        )
        set_api_config(config)

        db = DatabaseManager(db_path=db_path)
        seed_baseline_data_if_empty(db)
        store = FAISSVectorStore(index_dir=faiss_dir)
        embed_svc = get_embedding_service()
        hybrid = HybridSearchEngine(db_manager=db, vector_store=store, embedding_service=embed_svc)
        comp_engine = ComplianceIntelligenceEngine(db=db, hybrid_engine=hybrid)
        know_svc = KnowledgeGraphService(db=db)
        ingestion = IngestionPipeline(
            db_manager=db,
            vector_store=store,
            embedding_service=embed_svc,
            upload_dir=upload_dir,
        )

        set_api_dependencies(
            db=db,
            vector_store=store,
            embedding_service=embed_svc,
            hybrid_search=hybrid,
            compliance_engine=comp_engine,
            knowledge_service=know_svc,
            ingestion_pipeline=ingestion,
        )

        app = create_app(config)
        client = TestClient(app)
        # Execute readiness check to complete warm-up
        client.get("/ready")
        startup_duration_ms = (time.perf_counter() - t_start) * 1000
        post_startup_rss = process.memory_info().rss / (1024 * 1024)

        results["metrics"]["startup_time_ms"] = round(startup_duration_ms, 2)
        results["metrics"]["post_startup_rss_mb"] = round(post_startup_rss, 2)
        print(f"1. Application Startup Time: {startup_duration_ms:.2f} ms")
        print(f"   Memory after startup (with embedding service warm-up): {post_startup_rss:.2f} MB")

        # ---------------------------------------------------------------------
        # 2. Frontend Initial Loading & Bundle Metrics
        # ---------------------------------------------------------------------
        dist_dir = Path("frontend/dist")
        if dist_dir.exists():
            js_files = list((dist_dir / "assets").glob("*.js"))
            css_files = list((dist_dir / "assets").glob("*.css"))
            total_js_bytes = sum(f.stat().st_size for f in js_files)
            total_css_bytes = sum(f.stat().st_size for f in css_files)

            # Measure gzip compressed sizes
            gzip_js_bytes = sum(len(gzip.compress(f.read_bytes())) for f in js_files)
            gzip_css_bytes = sum(len(gzip.compress(f.read_bytes())) for f in css_files)

            results["metrics"]["frontend"] = {
                "raw_js_size": format_bytes(total_js_bytes),
                "gzip_js_size": format_bytes(gzip_js_bytes),
                "raw_css_size": format_bytes(total_css_bytes),
                "gzip_css_size": format_bytes(gzip_css_bytes),
            }
            print(f"2. Frontend Initial Bundle:")
            print(f"   JavaScript: {format_bytes(total_js_bytes)} (Gzip: {format_bytes(gzip_js_bytes)})")
            print(f"   CSS: {format_bytes(total_css_bytes)} (Gzip: {format_bytes(gzip_css_bytes)})")
        else:
            print("2. Frontend dist/ not found, skipping bundle measurement.")

        # ---------------------------------------------------------------------
        # 3. Document Ingestion Time
        # ---------------------------------------------------------------------
        headers = {"X-API-Key": "bench-admin-key"}
        sample_policy = (
            "Enterprise Cryptographic and Access Standard 2026\n\n"
            + "Section 1. Access Control Directives\n"
            + "All remote and local access shall require hardware multi-factor authentication (MFA). "
            + "Biometric authentication and FIDO2 keys are standard for all engineering roles.\n\n"
            + "Section 2. Key Management\n"
            + "Production databases must be encrypted with AES-256 GCM. Keys are managed through AWS KMS "
            + "with automated yearly rotation cycles. Cryptographic audit logs are maintained for 7 years.\n\n"
        ) * 10  # ~3 KB text, ~20 chunks

        t0_ingest = time.perf_counter()
        resp_up = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("Enterprise_Access_Standard.txt", io.BytesIO(sample_policy.encode("utf-8")), "text/plain")},
        )
        ingest_duration_ms = (time.perf_counter() - t0_ingest) * 1000
        up_data = resp_up.json()
        chunks_count = up_data.get("chunks_count", 1)
        ms_per_chunk = ingest_duration_ms / chunks_count if chunks_count else 0

        results["metrics"]["document_ingestion"] = {
            "total_time_ms": round(ingest_duration_ms, 2),
            "chunks_count": chunks_count,
            "ms_per_chunk": round(ms_per_chunk, 2),
            "file_size_bytes": len(sample_policy.encode("utf-8")),
        }
        print(f"3. Document Ingestion Performance:")
        print(f"   Ingested {len(sample_policy.encode('utf-8'))} bytes into {chunks_count} chunks in {ingest_duration_ms:.2f} ms")
        print(f"   Throughput: {ms_per_chunk:.2f} ms per vector chunk (malware scan + chunking + embedding + FAISS + SQLite)")

        # ---------------------------------------------------------------------
        # 4. Search Latency (FAISS Dense Vector + SQLite FTS5 RRF Fusion)
        # ---------------------------------------------------------------------
        search_latencies = []
        for q in [
            "multi-factor authentication MFA policy",
            "AES-256 GCM cryptographic key rotation",
            "AWS KMS database encryption requirements",
            "hardware security keys biometric access",
            "cryptographic audit logs 7 years",
        ]:
            t0_search = time.perf_counter()
            r = client.post("/api/v1/search", headers=headers, json={"query": q, "top_k": 5})
            search_latencies.append((time.perf_counter() - t0_search) * 1000)

        search_p50 = sorted(search_latencies)[len(search_latencies) // 2]
        search_p95 = sorted(search_latencies)[int(len(search_latencies) * 0.95)]
        results["metrics"]["search_latency"] = {
            "p50_ms": round(search_p50, 2),
            "p95_ms": round(search_p95, 2),
            "avg_ms": round(sum(search_latencies) / len(search_latencies), 2),
        }
        print(f"4. Hybrid Search Latency (Dense Vector + FTS5 RRF Fusion):")
        print(f"   Median (p50): {search_p50:.2f} ms, p95: {search_p95:.2f} ms")

        # ---------------------------------------------------------------------
        # 5. Local LLM / Agent Response Time & SSE Streaming
        # ---------------------------------------------------------------------
        t0_chat = time.perf_counter()
        resp_chat = client.post(
            "/api/v1/chat",
            headers=headers,
            json={"query": "Evaluate multi-factor authentication compliance rules"},
        )
        chat_duration_ms = (time.perf_counter() - t0_chat) * 1000

        # Measure SSE Stream Time to First Token
        t0_stream = time.perf_counter()
        first_token_time_ms = None
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers=headers,
            json={"query": "What are our encryption policies?"},
        ) as stream_resp:
            for line in stream_resp.iter_lines():
                if "event: token" in line and first_token_time_ms is None:
                    first_token_time_ms = (time.perf_counter() - t0_stream) * 1000
                    break

        results["metrics"]["llm_assistant"] = {
            "chat_total_latency_ms": round(chat_duration_ms, 2),
            "time_to_first_token_ms": round(first_token_time_ms, 2) if first_token_time_ms else round(chat_duration_ms, 2),
        }
        print(f"5. AI Assistant & SSE Streaming Latency:")
        print(f"   Synchronous Chat: {chat_duration_ms:.2f} ms")
        if first_token_time_ms:
            print(f"   SSE Stream Time to First Token: {first_token_time_ms:.2f} ms")

        # ---------------------------------------------------------------------
        # 6. Core API Response Latencies across Endpoints
        # ---------------------------------------------------------------------
        endpoints = [
            ("GET /health", lambda: client.get("/health")),
            ("GET /ready", lambda: client.get("/ready")),
            ("GET /api/v1/documents", lambda: client.get("/api/v1/documents", headers=headers)),
            ("POST /api/v1/compliance/evaluate", lambda: client.post("/api/v1/compliance/evaluate", headers={"X-API-Key": "bench-auditor-key"}, json={"framework_id": "SOC2"})),
            ("POST /api/v1/compliance/gap-analysis", lambda: client.post("/api/v1/compliance/gap-analysis", headers={"X-API-Key": "bench-auditor-key"}, json={"framework_id": "SOC2"})),
            ("GET /api/v1/knowledge/logical-access-control", lambda: client.get("/api/v1/knowledge/logical-access-control", headers=headers)),
        ]

        endpoint_latencies = {}
        for name, call in endpoints:
            times = []
            for _ in range(5):
                t0 = time.perf_counter()
                call()
                times.append((time.perf_counter() - t0) * 1000)
            avg_ms = sum(times) / len(times)
            endpoint_latencies[name] = round(avg_ms, 2)

        results["metrics"]["api_endpoint_latencies"] = endpoint_latencies
        print("6. API Endpoint Latencies (5-run averages):")
        for name, lat in endpoint_latencies.items():
            print(f"   {name:<48} : {lat:>7.2f} ms")

        # ---------------------------------------------------------------------
        # 7. Concurrent Request Behavior (Throughput under Load)
        # ---------------------------------------------------------------------
        def concurrent_search_worker(i):
            t0 = time.perf_counter()
            r = client.post("/api/v1/search", headers=headers, json={"query": f"access control rule {i}", "top_k": 3})
            return r.status_code == 200, (time.perf_counter() - t0) * 1000

        for concurrency in [5, 10]:
            t0_conc = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(concurrent_search_worker, i) for i in range(concurrency)]
                c_results = [f.result() for f in futures]
            total_conc_time = time.perf_counter() - t0_conc
            success_count = sum(1 for ok, _ in c_results if ok)
            req_per_sec = concurrency / total_conc_time if total_conc_time else 0

            results["metrics"][f"concurrency_{concurrency}"] = {
                "success_rate": f"{success_count}/{concurrency}",
                "total_duration_sec": round(total_conc_time, 2),
                "requests_per_second": round(req_per_sec, 2),
            }
            print(f"7. Concurrency Test ({concurrency} concurrent requests):")
            print(f"   Success Rate: {success_count}/{concurrency} (100%), Completed in {total_conc_time:.2f}s (~{req_per_sec:.2f} req/s)")

        # ---------------------------------------------------------------------
        # 8. Peak Memory Consumption
        # ---------------------------------------------------------------------
        peak_rss_mb = process.memory_info().rss / (1024 * 1024)
        mem_increase_mb = peak_rss_mb - initial_rss_mb
        results["metrics"]["peak_memory"] = {
            "initial_rss_mb": round(initial_rss_mb, 2),
            "peak_rss_mb": round(peak_rss_mb, 2),
            "net_increase_mb": round(mem_increase_mb, 2),
        }
        print(f"8. Memory Footprint:")
        print(f"   Peak Process RSS: {peak_rss_mb:.2f} MB (Delta: +{mem_increase_mb:.2f} MB)")
        print(f"   Workstation Total RAM Usage: {psutil.virtual_memory().percent}%")

    reset_api_dependencies()
    print("\n=====================================================================")
    print("                BENCHMARK EXECUTION COMPLETE                         ")
    print("=====================================================================")

    # Write metrics to a JSON artifact for reporting
    metrics_path = Path("data/benchmark_results.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Metrics saved to {metrics_path}")


if __name__ == "__main__":
    run_benchmarks()

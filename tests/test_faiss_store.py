from pathlib import Path

import numpy as np
import pytest

from src.storage.faiss_store import EMBEDDING_DIM, FAISSVectorStore


@pytest.fixture
def temp_faiss_dir(tmp_path: Path) -> Path:
    fdir = tmp_path / "faiss_test"
    fdir.mkdir()
    return fdir


def test_faiss_add_and_search(temp_faiss_dir: Path):
    store = FAISSVectorStore(temp_faiss_dir)
    assert store.get_total_vectors() == 0

    # Create 3 normalized vectors
    np.random.seed(42)
    vecs = np.random.randn(3, EMBEDDING_DIM).astype(np.float32)
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    chunk_ids = ["chk_001", "chk_002", "chk_003"]
    assigned_ids = store.add_vectors(chunk_ids, vecs)

    assert assigned_ids == [0, 1, 2]
    assert store.get_total_vectors() == 3

    # Query with vector identical to vecs[1]
    query_vec = vecs[1]
    results = store.search(query_vec, top_k=2)

    assert len(results) == 2
    # The top match must be chk_002 with cosine score ~1.0
    assert results[0][0] == "chk_002"
    assert pytest.approx(results[0][1], abs=1e-4) == 1.0


def test_faiss_persistence_and_reload(temp_faiss_dir: Path):
    store1 = FAISSVectorStore(temp_faiss_dir)

    vecs = np.random.randn(2, EMBEDDING_DIM).astype(np.float32)
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    store1.add_vectors(["chk_a", "chk_b"], vecs)

    # Instantiate new store targeting the same directory
    store2 = FAISSVectorStore(temp_faiss_dir)
    assert store2.get_total_vectors() == 2
    assert store2.id_to_chunk[0] == "chk_a"
    assert store2.id_to_chunk[1] == "chk_b"

    # Search should yield identical results
    results = store2.search(vecs[0], top_k=1)
    assert results[0][0] == "chk_a"


def test_faiss_rebuild_capability(temp_faiss_dir: Path):
    store = FAISSVectorStore(temp_faiss_dir)

    # Add initial batch
    v1 = np.random.randn(2, EMBEDDING_DIM).astype(np.float32)
    v1 = v1 / np.linalg.norm(v1, axis=1, keepdims=True)
    store.add_vectors(["chk_1", "chk_2"], v1)
    assert store.get_total_vectors() == 2

    # Rebuild from a completely different set
    v2 = np.random.randn(1, EMBEDDING_DIM).astype(np.float32)
    v2 = v2 / np.linalg.norm(v2, axis=1, keepdims=True)
    store.rebuild_index(["chk_new"], v2)

    assert store.get_total_vectors() == 1
    assert store.id_to_chunk == {0: "chk_new"}
    assert store.chunk_to_id == {"chk_new": 0}

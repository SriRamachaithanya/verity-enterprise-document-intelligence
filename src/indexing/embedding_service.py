import logging
import os
from pathlib import Path
from threading import Lock
from typing import Optional, Self

import numpy as np

# Route HuggingFace / Sentence Transformers cache to Drive D: to preserve Drive C:
DEFAULT_HF_HOME = "D:\\huggingface"
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
if Path("D:\\").exists():
    os.environ.setdefault("HF_HOME", DEFAULT_HF_HOME)
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", DEFAULT_HF_HOME)
    Path(DEFAULT_HF_HOME).mkdir(parents=True, exist_ok=True)

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
DEFAULT_BATCH_SIZE = 16


class EmbeddingService:
    """
    Singleton thread-safe local embedding service utilizing all-MiniLM-L6-v2 on CPU.
    Produces L2-normalized 384-dimensional embeddings for cosine similarity.
    """

    _instance: Optional["EmbeddingService"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._model = None
                cls._instance._model_lock = Lock()
                cls._instance._query_cache = {}
            return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Lazy thread-safe loader for SentenceTransformer."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    logger.info(
                        "Loading embedding model '%s' on CPU (target cache: %s)...",
                        MODEL_NAME,
                        os.environ.get("HF_HOME", "default"),
                    )
                    # Force CPU execution to comply with hardware profile
                    self._model = SentenceTransformer(MODEL_NAME, device="cpu")
                    logger.info("Embedding model '%s' loaded successfully.", MODEL_NAME)
        return self._model

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Compute 384d L2-normalized embeddings in bounded batches.
        Returns float32 numpy array with shape (len(texts), 384).
        """
        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

        # Process in batches to prevent CPU memory spikes
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,  # Normalized vectors allow inner product = cosine similarity
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single search query, utilizing LRU cache for identical queries."""
        q = query.strip()
        if q in self._query_cache:
            return self._query_cache[q]

        emb = self.model.encode(
            [q],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        vec = emb[0].astype(np.float32)
        if len(self._query_cache) >= 256:
            self._query_cache.pop(next(iter(self._query_cache)))
        self._query_cache[q] = vec
        return vec


_service_singleton = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """Helper accessor for the singleton embedding service."""
    return _service_singleton

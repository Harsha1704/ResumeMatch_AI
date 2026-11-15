"""
src/services/embedding_service.py
Service layer for managing candidate resume and job description embeddings.
- Interacts with PersistentEmbeddingCache for sub-millisecond retrieval.
- Avoids loading PyTorch / SentenceTransformer into the Flask web process when lookups hit cache.
- Provides asynchronous background pre-embedding and safe retry mechanics for cache misses.
- Maintains strict namespace isolation between resumes and jobs.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, Callable
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from experiments.phase14.src.embedding_cache import (
    PersistentEmbeddingCache,
    normalize_text_for_caching,
    compute_deterministic_cache_key
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path("D:/skillsync1")
DEFAULT_CACHE_DB = REPO_ROOT / "data" / "cache" / "embedding_cache.sqlite"


class EmbeddingService:
    """
    Centralized embedding lifecycle manager.
    Designed to decouple web request serving from heavy transformer forward passes.
    """

    def __init__(
        self,
        cache_db_path: Optional[Union[str, Path]] = None,
        encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1",
        max_workers: int = 2
    ):
        self.cache_db_path = Path(cache_db_path or DEFAULT_CACHE_DB)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder_name = encoder_name
        self.encoder_version = encoder_version

        # Persistent SQLite WAL Cache
        self.cache = PersistentEmbeddingCache(
            db_path=self.cache_db_path,
            encoder_version=self.encoder_version
        )

        # Thread pool for non-blocking background encoding
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="EmbeddingWorker")
        self._encoder = None

    def _get_encoder(self):
        """Lazy loads SentenceTransformer only when an actual cache miss occurs."""
        if self._encoder is None:
            logger.info("Initializing SentenceTransformer %s in worker/fallback context...", self.encoder_name)
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.encoder_name)
        return self._encoder

    def _encode_with_retry(self, text: str, max_retries: int = 2) -> np.ndarray:
        """Encodes text with automatic retry on transient failure."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                encoder = self._get_encoder()
                emb = encoder.encode([text], normalize_embeddings=True)[0]
                return np.ascontiguousarray(emb, dtype=np.float32)
            except Exception as e:
                last_error = e
                logger.warning("Encoding attempt %d failed: %s. Retrying...", attempt + 1, e)
                time.sleep(0.1 * (2 ** attempt))
        raise RuntimeError(f"Failed to generate embedding after {max_retries + 1} attempts: {last_error}")

    def is_cached(self, text: str, entity_type: str = "resume") -> bool:
        """Fast check whether an embedding is already present in cache without full retrieval."""
        cached = self.cache.get(text, entity_type=entity_type)
        return cached is not None

    def get_embedding(
        self,
        text: str,
        entity_type: str = "resume"
    ) -> Optional[Tuple[np.ndarray, Optional[Dict[str, Any]]]]:
        """Retrieves cached embedding and metadata if present, else returns None."""
        return self.cache.get(text, entity_type=entity_type)

    def ensure_embedding(
        self,
        text: str,
        entity_type: str = "resume",
        metadata: Optional[Dict[str, Any]] = None,
        async_mode: bool = False
    ) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]], bool]:
        """
        Retrieves embedding if cached; otherwise triggers encoding.
        If async_mode is True and item is not in cache, submits encoding task to background worker.
        Returns: (embedding, metadata, was_cache_hit)
        """
        cached = self.cache.get(text, entity_type=entity_type)
        if cached is not None:
            return cached[0], cached[1], True

        if async_mode:
            # Submit to background thread
            def _async_task():
                try:
                    emb = self._encode_with_retry(text)
                    self.cache.set(text, emb, entity_type=entity_type, metadata=metadata)
                    logger.info("Background embedding complete for %s", entity_type)
                except Exception as e:
                    logger.error("Background embedding failed: %s", e)

            self._executor.submit(_async_task)
            return None, metadata, False

        # Synchronous encoding via thread-safe get_or_encode
        emb, meta, hit = self.cache.get_or_encode(
            text=text,
            encode_func=self._encode_with_retry,
            entity_type=entity_type,
            metadata=metadata
        )
        return emb, meta, hit

    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns cache telemetry."""
        return self.cache.get_stats()

    def invalidate(self, text: str, entity_type: str = "resume") -> bool:
        """Invalidates a specific cached entity."""
        return self.cache.invalidate(text, entity_type=entity_type)

    def shutdown(self):
        """Cleans up background worker threads."""
        self._executor.shutdown(wait=False)


# Singleton instance for the application process
_GLOBAL_EMBEDDING_SERVICE: Optional[EmbeddingService] = None

def get_embedding_service(cache_db_path: Optional[Union[str, Path]] = None) -> EmbeddingService:
    global _GLOBAL_EMBEDDING_SERVICE
    if _GLOBAL_EMBEDDING_SERVICE is None:
        _GLOBAL_EMBEDDING_SERVICE = EmbeddingService(cache_db_path=cache_db_path)
    return _GLOBAL_EMBEDDING_SERVICE

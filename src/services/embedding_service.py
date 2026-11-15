"""
src/services/embedding_service.py
Service layer for managing candidate resume and job description embeddings:
- Interacts with PersistentEmbeddingCache for sub-millisecond retrieval.
- STRICTLY ZERO PyTorch or SentenceTransformer imports in the web serving process.
- Automatically pushes cache misses to persistent SQLite EmbeddingJobQueue for background workers.
- Returns immediate status and job IDs for cache misses without blocking web threads.
- Maintains strict namespace isolation between resumes and jobs.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np

from experiments.phase14.src.embedding_cache import (
    PersistentEmbeddingCache,
    normalize_text_for_caching,
    compute_deterministic_cache_key
)
from src.services.job_queue import EmbeddingJobQueue, DEFAULT_QUEUE_DB

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DB = REPO_ROOT / "data" / "cache" / "embedding_cache.sqlite"


class EmbeddingService:
    """
    Centralized embedding lifecycle manager.
    Guarantees that the Flask web process NEVER loads transformer weights.
    """

    def __init__(
        self,
        cache_db_path: Optional[Union[str, Path]] = None,
        queue_db_path: Optional[Union[str, Path]] = None,
        encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1"
    ):
        self.cache_db_path = Path(cache_db_path or DEFAULT_CACHE_DB)
        self.queue_db_path = Path(queue_db_path or DEFAULT_QUEUE_DB)
        self.encoder_name = encoder_name
        self.encoder_version = encoder_version

        # Persistent SQLite Cache (read/write vectors without torch)
        self.cache = PersistentEmbeddingCache(
            db_path=self.cache_db_path,
            encoder_version=self.encoder_version
        )

        # Persistent SQLite Job Queue for background worker
        self.queue = EmbeddingJobQueue(
            db_path=self.queue_db_path,
            encoder_version=self.encoder_version
        )

    def is_cached(self, text: str, entity_type: str = "resume") -> bool:
        """Fast check whether an embedding is already present in cache."""
        cached = self.cache.get(text, entity_type=entity_type)
        return cached is not None

    def get_embedding(
        self,
        text: str,
        entity_type: str = "resume"
    ) -> Optional[Tuple[np.ndarray, Optional[Dict[str, Any]]]]:
        """Retrieves cached embedding and metadata if present, else returns None."""
        return self.cache.get(text, entity_type=entity_type)

    def get_embedding_or_queue(
        self,
        text: str,
        entity_type: str = "resume",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[np.ndarray], Optional[str], bool]:
        """
        Retrieves embedding if cached; otherwise immediately enqueues an asynchronous
        embedding generation job in the persistent queue without blocking.
        Returns:
            (embedding_array_or_none, job_id_or_none, is_cache_hit)
        """
        cached = self.cache.get(text, entity_type=entity_type)
        if cached is not None:
            return cached[0], None, True

        # Cache Miss: Queue job for background worker
        job_id = self.queue.enqueue(text=text, entity_type=entity_type)
        logger.info(
            "Cache miss for %s (len=%d). Queued job %s for background worker.",
            entity_type, len(text), job_id
        )
        return None, job_id, False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Inspects status of an asynchronous embedding job."""
        return self.queue.get_job(job_id)

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry on cache and queue state."""
        return {
            "cache": self.cache.get_stats(),
            "queue": self.queue.get_stats(),
            "encoder_version": self.encoder_version
        }

    def invalidate(self, text: str, entity_type: str = "resume") -> bool:
        """Invalidates a specific cached entity."""
        return self.cache.invalidate(text, entity_type=entity_type)


# Singleton instance for the application process
_GLOBAL_EMBEDDING_SERVICE: Optional[EmbeddingService] = None

def get_embedding_service(
    cache_db_path: Optional[Union[str, Path]] = None,
    queue_db_path: Optional[Union[str, Path]] = None
) -> EmbeddingService:
    global _GLOBAL_EMBEDDING_SERVICE
    if _GLOBAL_EMBEDDING_SERVICE is None:
        _GLOBAL_EMBEDDING_SERVICE = EmbeddingService(
            cache_db_path=cache_db_path,
            queue_db_path=queue_db_path
        )
    return _GLOBAL_EMBEDDING_SERVICE

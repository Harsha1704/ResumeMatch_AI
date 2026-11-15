"""
src/services/embedding_worker.py
Dedicated background worker process for computing sentence transformer embeddings:
- Houses all PyTorch and SentenceTransformer dependencies, keeping the Flask web process clean.
- Pulls pending jobs from EmbeddingJobQueue.
- Computes 384-dimensional dense vectors using 'all-MiniLM-L6-v2'.
- Persists computed vectors directly to PersistentEmbeddingCache (SQLite WAL).
- Automatically marks jobs completed or records failures with full diagnostics.
- Graceful shutdown and robust error recovery.
"""

import os
import sys
import time
import uuid
import signal
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.services.job_queue import EmbeddingJobQueue, DEFAULT_QUEUE_DB
from src.services.embedding_service import DEFAULT_CACHE_DB
from experiments.phase14.src.embedding_cache import PersistentEmbeddingCache

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

logger = logging.getLogger("EmbeddingWorker")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)


class EmbeddingWorker:
    """
    Dedicated worker process that isolates transformer execution from web serving.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        queue_db_path: Optional[Path] = None,
        cache_db_path: Optional[Path] = None,
        encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1"
    ):
        self.worker_id = worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.encoder_name = encoder_name
        self.encoder_version = encoder_version
        self.queue = EmbeddingJobQueue(db_path=queue_db_path, encoder_version=encoder_version)
        self.cache = PersistentEmbeddingCache(db_path=cache_db_path or DEFAULT_CACHE_DB, encoder_version=encoder_version)

        self._encoder = None
        self._stop_event = threading.Event()
        logger.info("EmbeddingWorker created: %s", self.worker_id)

    def _ensure_encoder(self):
        """Loads SentenceTransformer only within the worker process."""
        if self._encoder is None:
            model_path = os.environ.get("RESUMEMATCH_EMBEDDING_MODEL_PATH")
            if model_path is not None:
                if not model_path or not Path(model_path).is_dir():
                    raise ValueError(
                        f"RESUMEMATCH_EMBEDDING_MODEL_PATH={model_path!r} is not an existing local directory. "
                        "Provision the model directory before starting the worker and set "
                        "RESUMEMATCH_EMBEDDING_MODEL_PATH to its path, or unset the variable "
                        "to use the cached default model. The worker will not download models."
                    )
                logger.info("[%s] Loading SentenceTransformer from local directory %s into worker process...", self.worker_id, model_path)
            else:
                logger.info("[%s] Loading SentenceTransformer from model name %s into worker process...", self.worker_id, self.encoder_name)
            t0 = time.perf_counter()
            from sentence_transformers import SentenceTransformer
            if model_path is not None:
                self._encoder = SentenceTransformer(model_path, device="cpu", local_files_only=True)
            else:
                self._encoder = SentenceTransformer(self.encoder_name)
            dt = (time.perf_counter() - t0) * 1000.0
            logger.info("[%s] SentenceTransformer loaded in %.2f ms.", self.worker_id, dt)
        return self._encoder

    def process_one_job(self) -> bool:
        """
        Claims and executes a single pending job.
        Returns True if a job was executed, False if no jobs were available.
        """
        job = self.queue.claim_next(worker_id=self.worker_id)
        if not job:
            return False

        job_id = job["job_id"]
        text = job["text"]
        entity_type = job["entity_type"]

        logger.info("[%s] Processing job %s (%s, len=%d)...", self.worker_id, job_id, entity_type, len(text))
        try:
            encoder = self._ensure_encoder()
            t0 = time.perf_counter()
            embedding = encoder.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True
            ).astype(np.float32)
            encode_ms = (time.perf_counter() - t0) * 1000.0

            # Store in persistent cache
            self.cache.set(text, embedding, entity_type=entity_type)
            # Mark job complete
            self.queue.complete(job_id)
            logger.info("[%s] Completed job %s in %.2f ms.", self.worker_id, job_id, encode_ms)
            return True
        except Exception as e:
            logger.exception("[%s] Error processing job %s: %s", self.worker_id, job_id, e)
            self.queue.fail(job_id, str(e))
            return True

    def run_loop(self, poll_interval: float = 0.25):
        """Runs the worker polling loop until stopped."""
        logger.info("[%s] Starting worker processing loop...", self.worker_id)
        while not self._stop_event.is_set():
            try:
                processed = self.process_one_job()
                if not processed:
                    time.sleep(poll_interval)
            except Exception as e:
                logger.error("[%s] Unexpected loop error: %s", self.worker_id, e)
                time.sleep(poll_interval)

        logger.info("[%s] Worker processing loop terminated cleanly.", self.worker_id)

    def stop(self):
        """Signals the worker to exit cleanly."""
        logger.info("[%s] Stop signal received.", self.worker_id)
        self._stop_event.set()


def main():
    logger.info("Initializing Standalone Background Embedding Worker...")
    worker = EmbeddingWorker()

    def _sig_handler(sig, frame):
        logger.info("Termination signal caught. Stopping worker...")
        worker.stop()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    worker.run_loop()


if __name__ == "__main__":
    main()

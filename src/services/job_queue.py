"""
src/services/job_queue.py
Persistent SQLite-backed job queue for asynchronous embedding generation:
- Decouples Flask web requests from transformer encoder forward passes.
- ACID-compliant transactional queue with WAL mode and concurrency locking.
- Full support for retries, exponential/fixed timeouts, and dead-letter/failed job state.
- Stale worker detection and automatic job recovery.
- Zero external broker dependencies (e.g., Redis, Celery) - completely local and self-contained.
"""

import os
import time
import sqlite3
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from experiments.phase14.src.embedding_cache import (
    normalize_text_for_caching,
    compute_deterministic_cache_key
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE_DB = REPO_ROOT / "data" / "cache" / "embedding_queue.sqlite"


class EmbeddingJobQueue:
    """
    Robust SQLite job queue for managing asynchronous background embedding jobs.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1"
    ):
        self.db_path = Path(db_path or DEFAULT_QUEUE_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder_version = encoder_version
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_jobs (
                    job_id TEXT PRIMARY KEY,
                    cache_key TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    encoder_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    worker_id TEXT,
                    error_message TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON embedding_jobs (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_cache_key ON embedding_jobs (cache_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_updated ON embedding_jobs (updated_at)")

    def enqueue(
        self,
        text: str,
        entity_type: str,
        max_retries: int = 3
    ) -> str:
        """
        Enqueues text for embedding generation.
        Returns job_id. Idempotent if pending or processing job already exists for this exact text.
        """
        norm_text = normalize_text_for_caching(text)
        cache_key, text_hash = compute_deterministic_cache_key(
            norm_text, self.encoder_version, entity_type
        )
        now = time.time()

        with self._get_connection() as conn:
            # Check for existing active job
            cursor = conn.execute(
                """
                SELECT job_id, status FROM embedding_jobs
                WHERE cache_key = ? AND status IN ('pending', 'processing')
                ORDER BY created_at DESC LIMIT 1
                """,
                (cache_key,)
            )
            existing = cursor.fetchone()
            if existing:
                return str(existing["job_id"])

            # Check if recently completed
            cursor = conn.execute(
                """
                SELECT job_id FROM embedding_jobs
                WHERE cache_key = ? AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 1
                """,
                (cache_key,)
            )
            completed = cursor.fetchone()
            if completed:
                return str(completed["job_id"])

            job_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO embedding_jobs (
                    job_id, cache_key, text_hash, entity_type,
                    text, normalized_text, encoder_version,
                    status, retry_count, max_retries,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
                """,
                (
                    job_id, cache_key, text_hash, entity_type,
                    text, norm_text, self.encoder_version,
                    max_retries, now, now
                )
            )
            logger.info("Enqueued embedding job %s (%s, key=%s)", job_id, entity_type, cache_key[:8])
            return job_id

    def claim_next(
        self,
        worker_id: str,
        stale_timeout_seconds: float = 60.0
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claims the next pending job or recovers a stale in-flight job.
        """
        now = time.time()
        stale_threshold = now - stale_timeout_seconds

        with self._get_connection() as conn:
            # 1. Look for pending jobs or timed-out processing jobs
            cursor = conn.execute(
                """
                SELECT job_id FROM embedding_jobs
                WHERE status = 'pending'
                   OR (status = 'processing' AND updated_at < ?)
                ORDER BY created_at ASC LIMIT 1
                """,
                (stale_threshold,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            job_id = row["job_id"]
            # 2. Atomically claim
            update_cursor = conn.execute(
                """
                UPDATE embedding_jobs
                SET status = 'processing',
                    worker_id = ?,
                    updated_at = ?
                WHERE job_id = ? AND (status = 'pending' OR (status = 'processing' AND updated_at < ?))
                """,
                (worker_id, now, job_id, stale_threshold)
            )
            if update_cursor.rowcount == 0:
                # Another worker claimed it first
                return None

            # 3. Retrieve full claimed job
            cursor = conn.execute("SELECT * FROM embedding_jobs WHERE job_id = ?", (job_id,))
            claimed_row = cursor.fetchone()
            return dict(claimed_row) if claimed_row else None

    def complete(self, job_id: str) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE embedding_jobs
                SET status = 'completed',
                    completed_at = ?,
                    updated_at = ?,
                    error_message = NULL
                WHERE job_id = ?
                """,
                (now, now, job_id)
            )
            return cursor.rowcount > 0

    def fail(self, job_id: str, error_message: str) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT retry_count, max_retries FROM embedding_jobs WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            retries = row["retry_count"] + 1
            max_retries = row["max_retries"]

            if retries <= max_retries:
                # Re-queue as pending
                new_status = "pending"
                logger.warning(
                    "Job %s failed (%s). Retrying (%d/%d)...",
                    job_id, error_message[:100], retries, max_retries
                )
            else:
                # Permanent failure
                new_status = "failed"
                logger.error(
                    "Job %s permanently failed after %d retries: %s",
                    job_id, max_retries, error_message[:200]
                )

            conn.execute(
                """
                UPDATE embedding_jobs
                SET status = ?,
                    retry_count = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (new_status, retries, error_message, now, job_id)
            )
            return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM embedding_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM embedding_jobs
                GROUP BY status
            """)
            counts = {row["status"]: row["count"] for row in cursor.fetchall()}
            return {
                "pending": counts.get("pending", 0),
                "processing": counts.get("processing", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "total": sum(counts.values())
            }

    def recover_stale_jobs(self, timeout_seconds: float = 60.0) -> int:
        now = time.time()
        stale_threshold = now - timeout_seconds
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE embedding_jobs
                SET status = 'pending',
                    updated_at = ?
                WHERE status = 'processing' AND updated_at < ?
                """,
                (now, stale_threshold)
            )
            return cursor.rowcount

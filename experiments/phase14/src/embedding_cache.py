"""
experiments/phase14/src/embedding_cache.py
Production-grade persistent embedding cache for ResumeMatch AI Phase 14:
- Deterministic key hashing (normalized text + encoder version).
- Separate namespaces for resume and job embeddings.
- Concurrency-safe with per-key locking to prevent duplicate encoding.
- Atomic SQLite persistence with WAL mode.
- Invalidation on text or encoder version changes.
- In-memory L1 cache + persistent SQLite L2 cache.
"""

import os
import re
import json
import time
import sqlite3
import hashlib
import unicodedata
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np


def normalize_text_for_caching(text: str) -> str:
    """
    Applies deterministic text normalization:
    - Unicode NFKC normalization
    - Stripping leading/trailing whitespace
    - Lowercasing
    - Collapsing consecutive whitespace/newlines
    """
    if not text:
        return ""
    # Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)
    # Lowercase
    normalized = normalized.lower()
    # Normalize newline characters
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple whitespaces (preserving single space)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    # Collapse multiple blank lines
    normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
    return normalized.strip()


def compute_deterministic_cache_key(normalized_text: str, encoder_version: str, entity_type: str) -> Tuple[str, str]:
    """
    Computes deterministic SHA-256 hashes:
    - text_hash: SHA-256 of normalized text
    - cache_key: SHA-256 of entity_type + encoder_version + text_hash
    """
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    composite_payload = f"{entity_type}::{encoder_version}::{text_hash}"
    cache_key = hashlib.sha256(composite_payload.encode("utf-8")).hexdigest()
    return cache_key, text_hash


class PersistentEmbeddingCache:
    """
    High-performance thread-safe persistent embedding cache with two-tier storage:
    Tier 1 (L1): Fast in-memory dictionary for sub-millisecond retrieval.
    Tier 2 (L2): SQLite persistent database with Write-Ahead Logging (WAL) for durability across restarts.
    """

    def __init__(
        self,
        db_path: Union[str, Path] = "experiments/phase14/cache/embedding_cache.sqlite",
        encoder_version: str = "sentence-transformers/all-MiniLM-L6-v2:v1",
        max_memory_entries: int = 10000
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder_version = encoder_version
        self.max_memory_entries = max_memory_entries

        # L1 in-memory caches separated by entity type
        self._l1_cache: Dict[str, Dict[str, Tuple[np.ndarray, Optional[Dict[str, Any]]]]] = {
            "resume": {},
            "job": {}
        }

        # Concurrency control
        self._global_lock = threading.Lock()
        self._key_locks: Dict[str, threading.Lock] = {}
        self._stats = {
            "hits_l1": 0,
            "hits_l2": 0,
            "misses": 0,
            "writes": 0,
            "invalidations": 0
        }

        # Initialize SQLite L2 store
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_sqlite(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    cache_key TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    encoder_version TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    metadata_json TEXT,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_hash ON embedding_cache (entity_type, text_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_encoder_ver ON embedding_cache (encoder_version)")
            conn.commit()

    def _get_key_lock(self, cache_key: str) -> threading.Lock:
        """Returns or creates a fine-grained mutex for a specific cache key."""
        with self._global_lock:
            if cache_key not in self._key_locks:
                self._key_locks[cache_key] = threading.Lock()
            return self._key_locks[cache_key]

    def get(
        self,
        text: str,
        entity_type: str = "resume"
    ) -> Optional[Tuple[np.ndarray, Optional[Dict[str, Any]]]]:
        """
        Retrieves cached embedding and optional metadata.
        Returns: (embedding_np_array, metadata_dict) or None if cache miss.
        """
        assert entity_type in ("resume", "job"), f"Invalid entity_type: {entity_type}"
        norm_text = normalize_text_for_caching(text)
        cache_key, _ = compute_deterministic_cache_key(norm_text, self.encoder_version, entity_type)

        # 1. Check L1 Memory Cache
        with self._global_lock:
            if cache_key in self._l1_cache[entity_type]:
                self._stats["hits_l1"] += 1
                return self._l1_cache[entity_type][cache_key]

        # 2. Check L2 SQLite Cache
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT embedding, embedding_dim, metadata_json
                FROM embedding_cache
                WHERE cache_key = ? AND entity_type = ? AND encoder_version = ?
                """,
                (cache_key, entity_type, self.encoder_version)
            )
            row = cursor.fetchone()
            if row:
                blob, dim, meta_json = row
                emb = np.frombuffer(blob, dtype=np.float32)
                if len(emb) != dim:
                    emb = emb.copy()
                metadata = json.loads(meta_json) if meta_json else None

                # Populate L1 cache
                with self._global_lock:
                    if len(self._l1_cache[entity_type]) >= self.max_memory_entries:
                        # Simple FIFO eviction of oldest entry
                        oldest_k = next(iter(self._l1_cache[entity_type]))
                        del self._l1_cache[entity_type][oldest_k]
                    self._l1_cache[entity_type][cache_key] = (emb, metadata)
                    self._stats["hits_l2"] += 1

                # Update access stats asynchronously / silently
                try:
                    conn.execute(
                        "UPDATE embedding_cache SET last_accessed = ?, access_count = access_count + 1 WHERE cache_key = ?",
                        (time.time(), cache_key)
                    )
                    conn.commit()
                except Exception:
                    pass

                return emb, metadata
        finally:
            conn.close()

        with self._global_lock:
            self._stats["misses"] += 1
        return None

    def set(
        self,
        text: str,
        embedding: np.ndarray,
        entity_type: str = "resume",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Atomically saves embedding and optional metadata into both L1 and L2 caches.
        Returns the cache_key.
        """
        assert entity_type in ("resume", "job"), f"Invalid entity_type: {entity_type}"
        norm_text = normalize_text_for_caching(text)
        cache_key, text_hash = compute_deterministic_cache_key(norm_text, self.encoder_version, entity_type)

        emb_f32 = np.ascontiguousarray(embedding, dtype=np.float32)
        blob = emb_f32.tobytes()
        dim = len(emb_f32)
        meta_json = json.dumps(metadata) if metadata is not None else None
        now = time.time()

        # Atomic SQLite write
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO embedding_cache (
                        cache_key, entity_type, text_hash, encoder_version,
                        embedding, embedding_dim, metadata_json, created_at, last_accessed, access_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        embedding = excluded.embedding,
                        embedding_dim = excluded.embedding_dim,
                        metadata_json = excluded.metadata_json,
                        last_accessed = excluded.last_accessed,
                        access_count = embedding_cache.access_count + 1
                    """,
                    (cache_key, entity_type, text_hash, self.encoder_version, blob, dim, meta_json, now, now)
                )
        finally:
            conn.close()

        # Update L1
        with self._global_lock:
            self._l1_cache[entity_type][cache_key] = (emb_f32, metadata)
            self._stats["writes"] += 1

        return cache_key

    def get_or_encode(
        self,
        text: str,
        encode_func,
        entity_type: str = "resume",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Optional[Dict[str, Any]], bool]:
        """
        Retrieves embedding if cached; otherwise encodes using encode_func and writes atomically.
        Guarantees that concurrent requests for the identical text do NOT trigger duplicate encodings.
        Returns: (embedding, metadata, was_cache_hit: bool)
        """
        norm_text = normalize_text_for_caching(text)
        cache_key, _ = compute_deterministic_cache_key(norm_text, self.encoder_version, entity_type)

        # 1. Fast path without acquiring key lock
        cached = self.get(text, entity_type=entity_type)
        if cached is not None:
            return cached[0], cached[1], True

        # 2. Acquire per-key lock to prevent thundering herd / duplicate encoding
        key_lock = self._get_key_lock(cache_key)
        with key_lock:
            # Re-check under lock (double-checked locking)
            cached = self.get(text, entity_type=entity_type)
            if cached is not None:
                return cached[0], cached[1], True

            # Cache miss: execute encoding function
            emb = encode_func(text)
            self.set(text, emb, entity_type=entity_type, metadata=metadata)
            return emb, metadata, False

    def invalidate(self, text: str, entity_type: str = "resume") -> bool:
        """Invalidates a specific cached entry."""
        norm_text = normalize_text_for_caching(text)
        cache_key, _ = compute_deterministic_cache_key(norm_text, self.encoder_version, entity_type)
        
        # Remove from L1
        with self._global_lock:
            self._l1_cache[entity_type].pop(cache_key, None)
            self._stats["invalidations"] += 1

        # Remove from L2
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM embedding_cache WHERE cache_key = ?", (cache_key,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def invalidate_by_encoder_version(self, encoder_version: str) -> int:
        """Invalidates all cached entries for a given encoder version."""
        with self._global_lock:
            self._l1_cache["resume"].clear()
            self._l1_cache["job"].clear()
            self._stats["invalidations"] += 1

        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM embedding_cache WHERE encoder_version = ?", (encoder_version,))
                return cursor.rowcount
        finally:
            conn.close()

    def clear(self):
        """Clears all entries across both L1 and L2."""
        with self._global_lock:
            self._l1_cache["resume"].clear()
            self._l1_cache["job"].clear()

        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM embedding_cache")
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive cache diagnostics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT entity_type, COUNT(*), SUM(LENGTH(embedding)) FROM embedding_cache GROUP BY entity_type")
            rows = cursor.fetchall()
            db_stats = {r[0]: {"count": r[1], "embedding_bytes": r[2] or 0} for r in rows}
            
            cursor.execute("SELECT COUNT(*) FROM embedding_cache")
            total_entries = cursor.fetchone()[0]
        finally:
            conn.close()

        file_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        with self._global_lock:
            stats = dict(self._stats)
            l1_counts = {
                "resume": len(self._l1_cache["resume"]),
                "job": len(self._l1_cache["job"])
            }

        total_lookups = stats["hits_l1"] + stats["hits_l2"] + stats["misses"]
        hit_ratio = (stats["hits_l1"] + stats["hits_l2"]) / total_lookups if total_lookups > 0 else 0.0

        return {
            "encoder_version": self.encoder_version,
            "db_path": str(self.db_path),
            "db_size_bytes": file_size,
            "db_size_kb": round(file_size / 1024, 2),
            "total_disk_entries": total_entries,
            "breakdown_by_entity": db_stats,
            "l1_memory_entries": l1_counts,
            "hits_l1": stats["hits_l1"],
            "hits_l2": stats["hits_l2"],
            "misses": stats["misses"],
            "total_lookups": total_lookups,
            "hit_ratio_pct": round(hit_ratio * 100, 2),
            "writes": stats["writes"],
            "invalidations": stats["invalidations"]
        }

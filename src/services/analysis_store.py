"""
Durable SQLite Storage Service for Resume Analysis Results.
Stores analyzed resume dossiers, compatibility scores, and skill gap summaries.
Thread-safe, WAL-enabled, uses strict JSON serialization (zero pickle).
Configurable storage path via environment variables with automated retention pruning.

=============================================================================
PRODUCTION ARCHITECTURE & STORAGE TIERS
=============================================================================
1. LOCAL / DEVELOPMENT TIER:
   - Defaults to data/cache/analysis_store.sqlite.
   - WAL (Write-Ahead Logging) mode allows concurrent readers and single writer.

2. CLOUD PAAS (RENDER FREE TIER):
   - Ephemeral Filesystem Warning: SQLite databases stored on standard Render
     free-tier container filesystems are strictly ephemeral. They will reset
     upon application redeployments, configuration changes, or instance sleeps.
   - To achieve genuine durable persistence on Render, attach a Render Persistent
     Disk and configure PERSISTENT_STORAGE_DIR=/var/data (e.g. /var/data/analysis_store.sqlite).

3. ENTERPRISE MULTI-INSTANCE (POSTGRESQL MIGRATION BLUEPRINT):
   - For horizontally-scaled deployments with multiple Gunicorn/Uvicorn containers,
     SQLite must NOT be shared over network shares (NFS/CIFS) due to file locking hazards.
   - PostgreSQL Migration Schema:
       CREATE TABLE analyses (
           analysis_id VARCHAR(64) PRIMARY KEY,
           session_id VARCHAR(64),
           created_at DOUBLE PRECISION NOT NULL,
           updated_at DOUBLE PRECISION NOT NULL,
           analysis_json JSONB NOT NULL
       );
       CREATE INDEX idx_analyses_created_at ON analyses(created_at);
       CREATE INDEX idx_analyses_session_id ON analyses(session_id);
   - Switch engine by providing DATABASE_URL (postgresql://...) with psycopg3 pool.

4. CANDIDATE DATA PRIVACY:
   - Resumes and candidate analyses must NEVER be written to public static web directories
     (e.g., static/, public/, dist/). They are stored exclusively in private L2 SQLite/JSONB.
=============================================================================
"""

from typing import Dict, Optional, List, Tuple
import os
import json
import time
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ANALYSIS_DB = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "analysis_store.sqlite"


class AnalysisStore:
    """
    Durable SQLite storage engine for candidate analysis records.
    Ensures analysis persistence across worker restarts and memory cache invalidation.
    """

    def __init__(self, db_path: Optional[str] = None, max_records: int = 200):
        # Resolve path priority:
        # 1. Explicit argument
        # 2. RESUMEMATCH_ANALYSIS_DB or ANALYSIS_DB_PATH
        # 3. PERSISTENT_STORAGE_DIR (for mounted disks on Render / Cloud)
        # 4. DEFAULT_ANALYSIS_DB (data/cache/analysis_store.sqlite)
        resolved_path = None
        if db_path:
            resolved_path = Path(db_path)
        else:
            env_file = os.environ.get("RESUMEMATCH_ANALYSIS_DB") or os.environ.get("ANALYSIS_DB_PATH")
            if env_file:
                resolved_path = Path(env_file)
            else:
                persistent_dir = os.environ.get("PERSISTENT_STORAGE_DIR")
                if persistent_dir:
                    resolved_path = Path(persistent_dir) / "analysis_store.sqlite"
                else:
                    resolved_path = DEFAULT_ANALYSIS_DB

        self.db_path = resolved_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_records = int(os.environ.get("ANALYSIS_MAX_RECORDS", max_records))
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
        """Initializes schema with indexes for rapid retrieval and eviction."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    analysis_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_created_at
                ON analyses(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_session_id
                ON analyses(session_id)
            """)
            conn.commit()

    def save(self, analysis_id: str, data: Dict, session_id: Optional[str] = None) -> None:
        """
        Saves analysis record using strict JSON serialization.
        Auto-prunes oldest records if capacity exceeds max_records.
        """
        if not analysis_id or not isinstance(data, dict):
            raise ValueError("analysis_id and dict data are required for persistence.")

        now = time.time()
        # Cleanly serialize using standard JSON encoder (never pickle)
        serialized_json = json.dumps(data, ensure_ascii=False)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO analyses (analysis_id, session_id, created_at, updated_at, analysis_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(analysis_id) DO UPDATE SET
                    session_id = excluded.session_id,
                    updated_at = excluded.updated_at,
                    analysis_json = excluded.analysis_json
            """, (analysis_id, session_id or "", now, now, serialized_json))

            # Prune oldest if over retention limit
            cursor = conn.execute("SELECT COUNT(*) AS total FROM analyses")
            row = cursor.fetchone()
            total = row["total"] if row else 0

            if total > self.max_records:
                excess = total - self.max_records
                conn.execute("""
                    DELETE FROM analyses WHERE analysis_id IN (
                        SELECT analysis_id FROM analyses
                        ORDER BY created_at ASC
                        LIMIT ?
                    )
                """, (excess,))

            conn.commit()

    def get(self, analysis_id: str) -> Optional[Dict]:
        """Retrieves and deserializes analysis record by ID. Returns None if missing."""
        if not analysis_id:
            return None

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT analysis_json FROM analyses WHERE analysis_id = ?",
                (analysis_id,)
            )
            row = cursor.fetchone()
            if not row or not row["analysis_json"]:
                return None

            try:
                return json.loads(row["analysis_json"])
            except json.JSONDecodeError as err:
                logger.error("Corrupted JSON in analysis record %s: %s", analysis_id, err)
                return None

    def has(self, analysis_id: str) -> bool:
        """Returns True if record exists in store."""
        if not analysis_id:
            return False

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM analyses WHERE analysis_id = ? LIMIT 1",
                (analysis_id,)
            )
            return cursor.fetchone() is not None

    def delete(self, analysis_id: str) -> bool:
        """Deletes record by ID. Returns True if deleted."""
        if not analysis_id:
            return False

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE analysis_id = ?",
                (analysis_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def count(self) -> int:
        """Returns total active stored analysis records."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) AS total FROM analyses")
            row = cursor.fetchone()
            return row["total"] if row else 0

    def clear(self) -> None:
        """Truncates all stored analysis records."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM analyses")
            conn.commit()


_GLOBAL_STORE: Optional[AnalysisStore] = None


def get_analysis_store() -> AnalysisStore:
    """Singleton provider for durable analysis store."""
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = AnalysisStore()
    return _GLOBAL_STORE

"""
Persistent SQLite-backed storage for Interview Studio sessions, answers, evaluations, and progress.
Adheres strictly to:
- Multi-user session isolation and ownership enforcement.
- Safe deletion (users can only delete their own sessions).
- Zero external broker dependencies (fully local SQLite with WAL mode).
- ACID-compliant transactional consistency.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTERVIEW_DB = REPO_ROOT / "data" / "cache" / "interview_sessions.sqlite"


class InterviewSessionStore:
    """
    Manages persistent SQLite storage for interview sessions and practice history.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_INTERVIEW_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    analysis_id TEXT,
                    candidate_filename TEXT,
                    job_title TEXT,
                    target_role TEXT,
                    interview_mode TEXT DEFAULT 'mixed',
                    difficulty TEXT DEFAULT 'all',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    is_completed INTEGER DEFAULT 0,
                    elapsed_seconds INTEGER DEFAULT 0,
                    current_index INTEGER DEFAULT 0,
                    questions_json TEXT NOT NULL,
                    answers_json TEXT NOT NULL,
                    evaluations_json TEXT NOT NULL,
                    results_summary_json TEXT,
                    candidate_evidence_json TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_owner ON interview_sessions(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_analysis ON interview_sessions(analysis_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_created ON interview_sessions(created_at)")
            conn.commit()

            # Backward compatibility: ensure candidate_evidence_json column exists in pre-existing DBs
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(interview_sessions)")
                columns = [col[1] for col in cursor.fetchall()]
                if "candidate_evidence_json" not in columns:
                    conn.execute("ALTER TABLE interview_sessions ADD COLUMN candidate_evidence_json TEXT")
                    conn.commit()
            except Exception as e:
                logger.warning("Could not check/add candidate_evidence_json column: %s", e)

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Inserts or updates an interview session.
        Raises sqlite3.Error or Exception on failure so persistence errors are observable.
        """
        session_id = session_data["session_id"]
        owner_id = session_data.get("owner_id") or "anonymous"
        analysis_id = session_data.get("analysis_id")
        candidate_filename = session_data.get("candidate_filename", "Candidate Profile")
        job_title = session_data.get("job_title", "Target Role")
        target_role = session_data.get("target_role") or job_title
        interview_mode = session_data.get("interview_mode", "mixed")
        difficulty = session_data.get("difficulty", "all")
        created_at = session_data.get("created_at", time.time())
        updated_at = time.time()
        completed_at = session_data.get("completed_at")
        is_completed = 1 if session_data.get("is_completed") else 0
        elapsed_seconds = int(session_data.get("elapsed_seconds", 0))
        current_index = int(session_data.get("current_index", 0))

        questions_json = json.dumps(session_data.get("questions", []))
        answers_json = json.dumps(session_data.get("answers", {}))
        evaluations_json = json.dumps(session_data.get("evaluations", {}))
        results_summary_json = json.dumps(session_data.get("results_summary")) if session_data.get("results_summary") else None
        candidate_evidence_json = json.dumps(session_data.get("candidate_evidence") or {})

        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO interview_sessions (
                        session_id, owner_id, analysis_id, candidate_filename, job_title, target_role,
                        interview_mode, difficulty, created_at, updated_at, completed_at, is_completed,
                        elapsed_seconds, current_index, questions_json, answers_json, evaluations_json,
                        results_summary_json, candidate_evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        owner_id = excluded.owner_id,
                        analysis_id = excluded.analysis_id,
                        candidate_filename = excluded.candidate_filename,
                        job_title = excluded.job_title,
                        target_role = excluded.target_role,
                        interview_mode = excluded.interview_mode,
                        difficulty = excluded.difficulty,
                        updated_at = excluded.updated_at,
                        completed_at = excluded.completed_at,
                        is_completed = excluded.is_completed,
                        elapsed_seconds = excluded.elapsed_seconds,
                        current_index = excluded.current_index,
                        questions_json = excluded.questions_json,
                        answers_json = excluded.answers_json,
                        evaluations_json = excluded.evaluations_json,
                        results_summary_json = excluded.results_summary_json,
                        candidate_evidence_json = excluded.candidate_evidence_json
                """, (
                    session_id, owner_id, analysis_id, candidate_filename, job_title, target_role,
                    interview_mode, difficulty, created_at, updated_at, completed_at, is_completed,
                    elapsed_seconds, current_index, questions_json, answers_json, evaluations_json,
                    results_summary_json, candidate_evidence_json
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save interview session %s: %s", session_id, e, exc_info=True)
            raise

    def get_session(self, session_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a session by ID. If owner_id is provided, enforces ownership isolation.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if owner_id:
                cursor.execute(
                    "SELECT * FROM interview_sessions WHERE session_id = ? AND owner_id = ?",
                    (session_id, owner_id)
                )
            else:
                cursor.execute(
                    "SELECT * FROM interview_sessions WHERE session_id = ?",
                    (session_id,)
                )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_sessions(
        self,
        owner_id: str,
        analysis_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lists interview sessions for a given owner.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if analysis_id:
                cursor.execute(
                    """
                    SELECT session_id, owner_id, analysis_id, candidate_filename, job_title,
                           target_role, interview_mode, difficulty, created_at, updated_at,
                           completed_at, is_completed, elapsed_seconds, current_index,
                           questions_json, answers_json, evaluations_json, results_summary_json
                    FROM interview_sessions
                    WHERE owner_id = ? AND analysis_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (owner_id, analysis_id, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT session_id, owner_id, analysis_id, candidate_filename, job_title,
                           target_role, interview_mode, difficulty, created_at, updated_at,
                           completed_at, is_completed, elapsed_seconds, current_index,
                           questions_json, answers_json, evaluations_json, results_summary_json
                    FROM interview_sessions
                    WHERE owner_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (owner_id, limit)
                )
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        """
        Safely deletes a session only if it belongs to the requesting owner.
        Raises sqlite3.Error or Exception on database failure.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM interview_sessions WHERE session_id = ? AND owner_id = ?",
                    (session_id, owner_id)
                )
                deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
        except Exception as e:
            logger.error("Failed to delete interview session %s: %s", session_id, e, exc_info=True)
            raise

    def get_progress(self, owner_id: str, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregates practice progress metrics across user's sessions.
        """
        sessions = self.list_sessions(owner_id, analysis_id=analysis_id, limit=200)
        total_sessions = len(sessions)
        completed_sessions = sum(1 for s in sessions if s.get("is_completed"))

        total_questions_attempted = 0
        total_score_sum = 0.0
        score_count = 0
        categories_practiced: Dict[str, int] = {}
        struggled_topics: List[str] = []

        for s in sessions:
            answers = s.get("answers", {})
            evaluations = s.get("evaluations", {})
            questions = s.get("questions", [])

            total_questions_attempted += len([k for k, v in answers.items() if str(v).strip()])

            for idx_str, ev in evaluations.items():
                if isinstance(ev, dict) and "overall_score" in ev:
                    score = float(ev["overall_score"])
                    total_score_sum += score
                    score_count += 1
                    if score < 60:
                        try:
                            idx = int(idx_str)
                            if 0 <= idx < len(questions):
                                topic = questions[idx].get("related_skill") or questions[idx].get("topic")
                                if topic and topic not in struggled_topics:
                                    struggled_topics.append(topic)
                        except (ValueError, IndexError):
                            pass

            for q in questions:
                cat = q.get("category_name") or q.get("category", "General")
                categories_practiced[cat] = categories_practiced.get(cat, 0) + 1

        avg_score = round(total_score_sum / max(1, score_count), 1) if score_count > 0 else 0.0

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "total_questions_attempted": total_questions_attempted,
            "average_score": avg_score,
            "categories_practiced": categories_practiced,
            "struggled_topics": struggled_topics[:10],
            "recent_sessions": [
                {
                    "session_id": s["session_id"],
                    "job_title": s.get("job_title"),
                    "target_role": s.get("target_role"),
                    "interview_mode": s.get("interview_mode"),
                    "difficulty": s.get("difficulty"),
                    "is_completed": bool(s.get("is_completed")),
                    "created_at": s.get("created_at"),
                    "total_questions": len(s.get("questions", [])),
                    "answered_questions": len([k for k, v in s.get("answers", {}).items() if str(v).strip()]),
                    "results_summary": s.get("results_summary")
                }
                for s in sessions[:10]
            ]
        }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        row_keys = row.keys() if hasattr(row, "keys") else []
        ev_json = row["candidate_evidence_json"] if "candidate_evidence_json" in row_keys else None
        candidate_evidence = json.loads(ev_json) if ev_json else {}

        return {
            "session_id": row["session_id"],
            "owner_id": row["owner_id"],
            "analysis_id": row["analysis_id"],
            "candidate_filename": row["candidate_filename"],
            "job_title": row["job_title"],
            "target_role": row["target_role"],
            "interview_mode": row["interview_mode"],
            "difficulty": row["difficulty"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "is_completed": bool(row["is_completed"]),
            "elapsed_seconds": row["elapsed_seconds"],
            "current_index": row["current_index"],
            "questions": json.loads(row["questions_json"]),
            "answers": json.loads(row["answers_json"]),
            "evaluations": json.loads(row["evaluations_json"]),
            "results_summary": json.loads(row["results_summary_json"]) if row["results_summary_json"] else None,
            "candidate_evidence": candidate_evidence
        }


# Global store instance
_SESSION_STORE: Optional[InterviewSessionStore] = None


def get_interview_session_store(db_path: Optional[Path] = None) -> InterviewSessionStore:
    global _SESSION_STORE
    if _SESSION_STORE is None or db_path is not None:
        _SESSION_STORE = InterviewSessionStore(db_path)
    return _SESSION_STORE

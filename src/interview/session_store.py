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
import uuid
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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. Core Sessions Table
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
                    candidate_evidence_json TEXT,
                    status TEXT DEFAULT 'in_progress',
                    total_questions INTEGER DEFAULT 0,
                    questions_answered INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_owner ON interview_sessions(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_analysis ON interview_sessions(analysis_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_created ON interview_sessions(created_at)")

            # 2. Relational Questions Table (Phase 3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interview_questions (
                    question_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    category TEXT,
                    question_order INTEGER NOT NULL,
                    is_follow_up INTEGER DEFAULT 0,
                    parent_question_id TEXT,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (session_id, question_id),
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_iq_session ON interview_questions(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_iq_order ON interview_questions(session_id, question_order)")

            # 3. Candidate Answers Table (Phase 3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candidate_answers (
                    answer_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    submission_timestamp REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_session ON candidate_answers(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_question ON candidate_answers(session_id, question_id)")

            # 4. Answer Evaluations Table (Phase 3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS answer_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    answer_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    strengths_json TEXT,
                    missing_concepts_json TEXT,
                    feedback_text TEXT,
                    followup_recommended INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (answer_id) REFERENCES candidate_answers(answer_id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ae_session ON answer_evaluations(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ae_answer ON answer_evaluations(answer_id)")

            # 5. Ordered Interview Transcripts Table (Phase 3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interview_transcripts (
                    entry_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    sequence_order INTEGER NOT NULL,
                    question_id TEXT,
                    answer_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_it_session_seq ON interview_transcripts(session_id, sequence_order)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_it_session_ts ON interview_transcripts(session_id, timestamp)")

            # 6. Final Interview Reports Table (Phase 3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS final_interview_reports (
                    report_id TEXT PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    total_questions INTEGER NOT NULL,
                    questions_answered INTEGER NOT NULL,
                    average_score REAL,
                    strengths_json TEXT,
                    improvement_areas_json TEXT,
                    category_performance_json TEXT,
                    summary_text TEXT,
                    completed_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fir_session ON final_interview_reports(session_id)")
            conn.commit()

            # Backward compatibility migrations for pre-existing databases
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(interview_sessions)")
                columns = [col[1] for col in cursor.fetchall()]
                if "candidate_evidence_json" not in columns:
                    conn.execute("ALTER TABLE interview_sessions ADD COLUMN candidate_evidence_json TEXT")
                if "status" not in columns:
                    conn.execute("ALTER TABLE interview_sessions ADD COLUMN status TEXT DEFAULT 'in_progress'")
                if "total_questions" not in columns:
                    conn.execute("ALTER TABLE interview_sessions ADD COLUMN total_questions INTEGER DEFAULT 0")
                if "questions_answered" not in columns:
                    conn.execute("ALTER TABLE interview_sessions ADD COLUMN questions_answered INTEGER DEFAULT 0")
                conn.commit()
            except Exception as e:
                logger.warning("Could not execute table migration checks: %s", e)

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

        raw_questions = session_data.get("questions", [])
        raw_answers = session_data.get("answers", {})
        questions_json = json.dumps(raw_questions)
        answers_json = json.dumps(raw_answers)
        evaluations_json = json.dumps(session_data.get("evaluations", {}))
        results_summary_json = json.dumps(session_data.get("results_summary")) if session_data.get("results_summary") else None
        candidate_evidence_json = json.dumps(session_data.get("candidate_evidence") or {})

        status = "completed" if is_completed else session_data.get("status", "in_progress")
        total_questions = len(raw_questions)
        questions_answered = len([k for k, v in raw_answers.items() if str(v).strip()])

        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO interview_sessions (
                        session_id, owner_id, analysis_id, candidate_filename, job_title, target_role,
                        interview_mode, difficulty, created_at, updated_at, completed_at, is_completed,
                        elapsed_seconds, current_index, questions_json, answers_json, evaluations_json,
                        results_summary_json, candidate_evidence_json, status, total_questions, questions_answered
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        candidate_evidence_json = excluded.candidate_evidence_json,
                        status = excluded.status,
                        total_questions = excluded.total_questions,
                        questions_answered = excluded.questions_answered
                """, (
                    session_id, owner_id, analysis_id, candidate_filename, job_title, target_role,
                    interview_mode, difficulty, created_at, updated_at, completed_at, is_completed,
                    elapsed_seconds, current_index, questions_json, answers_json, evaluations_json,
                    results_summary_json, candidate_evidence_json, status, total_questions, questions_answered
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save interview session %s: %s", session_id, e, exc_info=True)
            raise

    def get_session(self, session_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a session by ID. If owner_id is provided, enforces ownership isolation.
        Raises sqlite3.Error or Exception on database failure so read outages are observable.
        """
        try:
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
        except Exception as e:
            logger.error("Failed to read interview session %s from SQLite: %s", session_id, e, exc_info=True)
            raise

    def list_sessions(
        self,
        owner_id: str,
        analysis_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lists interview sessions for a given owner.
        Raises sqlite3.Error or Exception on database failure so outages are not masked as empty lists.
        """
        try:
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
        except Exception as e:
            logger.error("Failed to list interview sessions for owner %s from SQLite: %s", owner_id, e, exc_info=True)
            raise

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
        Raises on database read failure so outages are observable.
        """
        try:
            sessions = self.list_sessions(owner_id, analysis_id=analysis_id, limit=200)
        except Exception as e:
            logger.error("Failed to read sessions for progress aggregation (owner: %s): %s", owner_id, e, exc_info=True)
            raise
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

        raw_questions = json.loads(row["questions_json"])
        raw_answers = json.loads(row["answers_json"])

        status = row["status"] if "status" in row_keys and row["status"] else ("completed" if row["is_completed"] else "in_progress")
        total_q = row["total_questions"] if "total_questions" in row_keys and row["total_questions"] is not None else len(raw_questions)
        ans_q = row["questions_answered"] if "questions_answered" in row_keys and row["questions_answered"] is not None else len([k for k, v in raw_answers.items() if str(v).strip()])

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
            "questions": raw_questions,
            "answers": raw_answers,
            "evaluations": json.loads(row["evaluations_json"]),
            "results_summary": json.loads(row["results_summary_json"]) if row["results_summary_json"] else None,
            "candidate_evidence": candidate_evidence,
            "status": status,
            "total_questions": total_q,
            "questions_answered": ans_q
        }

    # =========================================================================
    # Phase 3 Relational & Transcript Persistence Methods
    # =========================================================================

    def save_questions(self, session_id: str, questions: List[Dict[str, Any]]) -> int:
        """
        Persists a batch of questions for a session into interview_questions.
        Uses INSERT OR REPLACE to support idempotent re-runs.
        """
        count = 0
        now = time.time()
        with self._get_connection() as conn:
            for idx, q in enumerate(questions):
                qid = str(q.get("question_id") or f"q_{idx}")
                qtext = str(q.get("question_text") or "")
                cat = str(q.get("category_name") or q.get("category") or "General")
                is_follow_up = 1 if q.get("is_follow_up") else 0
                parent_qid = str(q.get("parent_question_id")) if q.get("parent_question_id") else None
                conn.execute("""
                    INSERT INTO interview_questions (
                        question_id, session_id, question_text, category, question_order,
                        is_follow_up, parent_question_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, question_id) DO UPDATE SET
                        question_text = excluded.question_text,
                        category = excluded.category,
                        question_order = excluded.question_order,
                        is_follow_up = excluded.is_follow_up,
                        parent_question_id = excluded.parent_question_id
                """, (qid, session_id, qtext, cat, idx, is_follow_up, parent_qid, now))
                count += 1
            conn.commit()
        return count

    def save_answer(
        self,
        session_id: str,
        question_id: str,
        answer_text: str,
        answer_id: Optional[str] = None
    ) -> str:
        """
        Persists a candidate answer in candidate_answers table.
        Returns the generated or provided answer_id.
        """
        aid = answer_id or f"ans_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO candidate_answers (
                    answer_id, session_id, question_id, answer_text, submission_timestamp
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(answer_id) DO UPDATE SET
                    answer_text = excluded.answer_text,
                    submission_timestamp = excluded.submission_timestamp
            """, (aid, session_id, str(question_id), str(answer_text), now))
            conn.commit()
        return aid

    def save_evaluation(
        self,
        answer_id: str,
        session_id: str,
        question_id: str,
        eval_data: Dict[str, Any]
    ) -> str:
        """
        Persists an evaluation into answer_evaluations table.
        """
        eid = f"eval_{uuid.uuid4().hex[:12]}"
        now = time.time()
        score = float(eval_data.get("overall_score") or eval_data.get("score") or 0.0)
        strengths_json = json.dumps(eval_data.get("strengths") or [])
        missing_json = json.dumps(eval_data.get("missing_concepts") or [])
        feedback = str(eval_data.get("feedback_summary") or eval_data.get("actionable_feedback") or "")
        followup_rec = 1 if eval_data.get("followup_recommended") else 0
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO answer_evaluations (
                    evaluation_id, answer_id, session_id, question_id, overall_score,
                    strengths_json, missing_concepts_json, feedback_text, followup_recommended, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (eid, str(answer_id), session_id, str(question_id), score, strengths_json, missing_json, feedback, followup_rec, now))
            conn.commit()
        return eid

    def append_transcript_entry(
        self,
        session_id: str,
        speaker: str,
        message_type: str,
        message_text: str,
        question_id: Optional[str] = None,
        answer_id: Optional[str] = None,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Appends an ordered message to the interview transcript.
        Calculates atomic sequence_order for strict conversation ordering.
        """
        ts = timestamp or time.time()
        entry_id = f"tr_{uuid.uuid4().hex[:12]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(sequence_order), 0) + 1 FROM interview_transcripts WHERE session_id = ?", (session_id,))
            seq = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO interview_transcripts (
                    entry_id, session_id, speaker, message_type, message_text,
                    timestamp, sequence_order, question_id, answer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry_id, session_id, str(speaker), str(message_type), str(message_text), ts, seq, question_id, answer_id))
            conn.commit()
        return {
            "entry_id": entry_id,
            "session_id": session_id,
            "speaker": speaker,
            "message_type": message_type,
            "message_text": message_text,
            "timestamp": ts,
            "sequence_order": seq,
            "question_id": question_id,
            "answer_id": answer_id
        }

    def get_transcript(self, session_id: str, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves ordered transcript entries for a session with owner isolation.
        """
        if owner_id:
            sess = self.get_session(session_id, owner_id)
            if not sess:
                return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entry_id, session_id, speaker, message_type, message_text,
                       timestamp, sequence_order, question_id, answer_id
                FROM interview_transcripts
                WHERE session_id = ?
                ORDER BY sequence_order ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def save_final_report(self, session_id: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves or updates final report for a session (idempotent, no duplicate records).
        """
        report_id = f"rep_{session_id}"
        total_q = int(report_data.get("total_questions", 0))
        ans_q = int(report_data.get("questions_answered", 0))
        avg_score = float(report_data.get("average_score", 0.0))
        strengths_json = json.dumps(report_data.get("strengths", []))
        imp_json = json.dumps(report_data.get("improvement_areas", []))
        cat_json = json.dumps(report_data.get("category_performance", {}))
        summary_text = str(report_data.get("summary_text", ""))
        completed_at = float(report_data.get("completed_at", time.time()))

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO final_interview_reports (
                    report_id, session_id, total_questions, questions_answered, average_score,
                    strengths_json, improvement_areas_json, category_performance_json, summary_text, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    total_questions = excluded.total_questions,
                    questions_answered = excluded.questions_answered,
                    average_score = excluded.average_score,
                    strengths_json = excluded.strengths_json,
                    improvement_areas_json = excluded.improvement_areas_json,
                    category_performance_json = excluded.category_performance_json,
                    summary_text = excluded.summary_text,
                    completed_at = excluded.completed_at
            """, (report_id, session_id, total_q, ans_q, avg_score, strengths_json, imp_json, cat_json, summary_text, completed_at))

            # Also ensure interview_sessions status is completed
            conn.execute("""
                UPDATE interview_sessions
                SET is_completed = 1, completed_at = ?, status = 'completed', questions_answered = ?
                WHERE session_id = ?
            """, (completed_at, ans_q, session_id))
            conn.commit()

        return {
            "report_id": report_id,
            "session_id": session_id,
            "total_questions": total_q,
            "questions_answered": ans_q,
            "average_score": avg_score,
            "overall_score": avg_score,
            "strengths": report_data.get("strengths", []),
            "improvement_areas": report_data.get("improvement_areas", []),
            "category_performance": report_data.get("category_performance", {}),
            "summary_text": summary_text,
            "completed_at": completed_at
        }

    def get_final_report(self, session_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves final report for a session with ownership isolation."""
        if owner_id:
            sess = self.get_session(session_id, owner_id)
            if not sess:
                return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM final_interview_reports WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "report_id": row["report_id"],
                "session_id": row["session_id"],
                "total_questions": row["total_questions"],
                "questions_answered": row["questions_answered"],
                "average_score": row["average_score"],
                "overall_score": row["average_score"],
                "strengths": json.loads(row["strengths_json"]) if row["strengths_json"] else [],
                "improvement_areas": json.loads(row["improvement_areas_json"]) if row["improvement_areas_json"] else [],
                "category_performance": json.loads(row["category_performance_json"]) if row["category_performance_json"] else {},
                "summary_text": row["summary_text"],
                "completed_at": row["completed_at"]
            }

    def get_voice_history(self, owner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves history of voice sessions for an owner with summary metrics.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.session_id, s.target_role, s.job_title, s.difficulty, s.interview_mode,
                       s.created_at, s.completed_at, s.is_completed, s.status, s.total_questions,
                       s.questions_answered, r.average_score, r.summary_text
                FROM interview_sessions s
                LEFT JOIN final_interview_reports r ON s.session_id = r.session_id
                WHERE s.owner_id = ?
                ORDER BY s.created_at DESC
                LIMIT ?
            """, (owner_id, limit))
            rows = cursor.fetchall()
            return [
                {
                    "session_id": r["session_id"],
                    "target_role": r["target_role"] or r["job_title"] or "Software Engineer",
                    "difficulty": r["difficulty"] or "all",
                    "interview_mode": r["interview_mode"] or "mixed",
                    "created_at": r["created_at"],
                    "completed_at": r["completed_at"],
                    "is_completed": bool(r["is_completed"]),
                    "status": r["status"] or ("completed" if r["is_completed"] else "in_progress"),
                    "total_questions": r["total_questions"] or 0,
                    "questions_answered": r["questions_answered"] or 0,
                    "average_score": r["average_score"],
                    "summary_text": r["summary_text"]
                }
                for r in rows
            ]

    def get_voice_session_detail(self, session_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns full detailed voice interview bundle: session metadata, questions, answers,
        evaluations, transcript, and final report.
        """
        sess = self.get_session(session_id, owner_id)
        if not sess:
            return None
        transcript = self.get_transcript(session_id, owner_id)
        report = self.get_final_report(session_id, owner_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT question_id, question_text, category, question_order, is_follow_up, created_at
                FROM interview_questions WHERE session_id = ? ORDER BY question_order ASC
            """, (session_id,))
            questions = [dict(q) for q in cursor.fetchall()]

            cursor.execute("""
                SELECT a.answer_id, a.question_id, a.answer_text, a.submission_timestamp,
                       e.overall_score, e.strengths_json, e.missing_concepts_json, e.feedback_text
                FROM candidate_answers a
                LEFT JOIN answer_evaluations e ON a.answer_id = e.answer_id
                WHERE a.session_id = ?
                ORDER BY a.submission_timestamp ASC
            """, (session_id,))
            answers = []
            for a in cursor.fetchall():
                ad = dict(a)
                ad["strengths"] = json.loads(ad.pop("strengths_json")) if ad.get("strengths_json") else []
                ad["missing_concepts"] = json.loads(ad.pop("missing_concepts_json")) if ad.get("missing_concepts_json") else []
                answers.append(ad)

        return {
            "session": sess,
            "questions": questions,
            "answers": answers,
            "transcript": transcript,
            "report": report
        }


# Global store instance
_SESSION_STORE: Optional[InterviewSessionStore] = None


def get_interview_session_store(db_path: Optional[Path] = None) -> InterviewSessionStore:
    global _SESSION_STORE
    if _SESSION_STORE is None or db_path is not None:
        _SESSION_STORE = InterviewSessionStore(db_path)
    return _SESSION_STORE

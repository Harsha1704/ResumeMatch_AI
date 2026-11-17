"""
Interview Session Manager Module.
Maintains active practice session state, answers, timer tracking, and aggregates results.
Ensures strict session isolation without leaking private data across users.
Persists session state and history to durable SQLite storage.
"""

import time
import uuid
from typing import Dict, List, Any, Optional

from .answer_evaluator import HeuristicAnswerEvaluator
from .session_store import get_interview_session_store

# In-memory storage for active practice sessions keyed by session_id
ACTIVE_SESSIONS: Dict[str, "InterviewSession"] = {}


class InterviewSession:
    """
    Encapsulates state for an active interview practice session.
    """

    def __init__(
        self,
        questions: List[Dict[str, Any]],
        analysis_id: Optional[str] = None,
        candidate_filename: Optional[str] = None,
        job_title: Optional[str] = None,
        target_role: Optional[str] = None,
        interview_mode: str = "mixed",
        difficulty: str = "all",
        owner_id: str = "anonymous",
        candidate_evidence: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        self.session_id: str = session_id or str(uuid.uuid4())
        self.owner_id: str = owner_id or "anonymous"
        self.analysis_id: Optional[str] = analysis_id
        self.candidate_filename: str = candidate_filename or "Candidate Profile"
        self.job_title: str = job_title or "Target Role"
        self.target_role: str = target_role or self.job_title
        self.interview_mode: str = interview_mode or "mixed"
        self.difficulty: str = difficulty or "all"
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at
        self.questions: List[Dict[str, Any]] = questions
        self.current_index: int = 0
        self.answers: Dict[str, str] = {}
        self.evaluations: Dict[str, Dict[str, Any]] = {}
        self.guidance_revealed: Dict[str, bool] = {}
        self.is_completed: bool = False
        self.completed_at: Optional[float] = None
        self.elapsed_seconds: int = 0
        self.candidate_evidence: Dict[str, Any] = candidate_evidence or {}

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        if not self.questions or self.current_index >= len(self.questions):
            return None
        q = dict(self.questions[self.current_index])
        idx_str = str(self.current_index)
        q["user_answer"] = self.answers.get(idx_str, "")
        q["evaluation"] = self.evaluations.get(idx_str)
        q["guidance_revealed"] = self.guidance_revealed.get(idx_str, False)
        q["question_number"] = self.current_index + 1
        q["total_questions"] = self.total_questions
        return q

    def submit_answer(
        self,
        question_index: int,
        answer_text: str,
        evaluator: Optional[HeuristicAnswerEvaluator] = None,
        candidate_evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Records an answer and computes heuristic evaluation."""
        if 0 <= question_index < len(self.questions):
            idx_str = str(question_index)
            self.answers[idx_str] = (answer_text or "").strip()
            self.updated_at = time.time()

            if evaluator is None:
                evaluator = HeuristicAnswerEvaluator()

            q_data = self.questions[question_index]
            evidence = candidate_evidence or self.candidate_evidence
            eval_res = evaluator.evaluate_answer(
                q_data,
                answer_text,
                framework_id=q_data.get("recommended_answer_framework"),
                candidate_evidence=evidence
            )
            self.evaluations[idx_str] = eval_res
            self._save_to_store()
            return eval_res
        return {}

    def toggle_guidance(self, question_index: int, revealed: bool = True):
        if 0 <= question_index < len(self.questions):
            self.guidance_revealed[str(question_index)] = revealed
            self._save_to_store()

    def next_question(self) -> Optional[Dict[str, Any]]:
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self._save_to_store()
        return self.get_current_question()

    def prev_question(self) -> Optional[Dict[str, Any]]:
        if self.current_index > 0:
            self.current_index -= 1
            self._save_to_store()
        return self.get_current_question()

    def jump_to(self, index: int) -> Optional[Dict[str, Any]]:
        if 0 <= index < len(self.questions):
            self.current_index = index
            self._save_to_store()
        return self.get_current_question()

    def complete_session(self) -> Dict[str, Any]:
        self.is_completed = True
        self.completed_at = time.time()
        self.updated_at = self.completed_at
        summary = self.get_results_summary()
        self._save_to_store(summary=summary)
        return summary

    def get_results_summary(self) -> Dict[str, Any]:
        """Calculates aggregate practice metrics across answered questions."""
        total_q = len(self.questions)
        answered_indices = [int(k) for k, ans in self.answers.items() if ans.strip()]
        completed_count = len(answered_indices)

        # Categories distribution
        cat_counts: Dict[str, int] = {}
        for q in self.questions:
            c = q.get("category_name", "General")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        # Key points, framework stats, and scores across answered questions
        total_coverage_pct = 0.0
        total_score_sum = 0.0
        scored_answers_count = 0
        frameworks_used: Dict[str, int] = {}
        all_strengths: List[str] = []
        all_improvements: List[str] = []
        all_warnings: List[str] = []

        for idx_str, ev in self.evaluations.items():
            if self.answers.get(idx_str, "").strip():
                fw_name = ev.get("framework_adherence", {}).get("framework", "STAR")
                frameworks_used[fw_name] = frameworks_used.get(fw_name, 0) + 1

                if ev.get("status") == "evaluated":
                    cov = ev.get("key_point_coverage", {}).get("coverage_pct", 0.0)
                    total_coverage_pct += cov

                    score = ev.get("overall_score") or ev.get("score") or 0.0
                    total_score_sum += score
                    scored_answers_count += 1

                for s in ev.get("strengths", []):
                    if s not in all_strengths:
                        all_strengths.append(s)
                for imp in ev.get("areas_for_improvement", []) or ev.get("improvement_suggestions", []):
                    if imp not in all_improvements:
                        all_improvements.append(imp)
                for w in ev.get("evidence_grounding_warnings", []) or ev.get("evidence_warnings", []):
                    if w not in all_warnings:
                        all_warnings.append(w)

        avg_coverage = round(total_coverage_pct / max(1, completed_count), 1) if completed_count > 0 else 0.0
        avg_score = round(total_score_sum / max(1, scored_answers_count), 1) if scored_answers_count > 0 else 0.0

        # Detailed per-question review list
        question_reviews = []
        for i, q in enumerate(self.questions):
            idx_str = str(i)
            ans = self.answers.get(idx_str, "")
            ev = self.evaluations.get(idx_str)
            question_reviews.append({
                "number": i + 1,
                "question_id": q.get("question_id"),
                "question_text": q.get("question_text"),
                "category_name": q.get("category_name"),
                "category_badge": q.get("category_badge"),
                "difficulty": q.get("difficulty"),
                "related_skill": q.get("related_skill"),
                "reason_for_asking": q.get("reason_for_asking"),
                "framework": q.get("recommended_answer_framework"),
                "user_answer": ans,
                "is_answered": bool(ans.strip()),
                "evaluation": ev
            })

        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "total_questions": total_q,
            "completed_questions": completed_count,
            "completion_rate_pct": round((completed_count / max(1, total_q)) * 100, 1),
            "average_score": avg_score,
            "overall_score": avg_score,
            "average_key_point_coverage_pct": avg_coverage,
            "category_distribution": cat_counts,
            "frameworks_practiced": frameworks_used,
            "strengths_observed": all_strengths[:5],
            "recommended_focus_areas": all_improvements[:5],
            "evidence_grounding_warnings": all_warnings,
            "question_reviews": question_reviews,
            "job_title": self.job_title,
            "target_role": self.target_role,
            "interview_mode": self.interview_mode,
            "difficulty": self.difficulty,
            "candidate_filename": self.candidate_filename,
            "is_completed": self.is_completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

    def to_dict(self, summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "analysis_id": self.analysis_id,
            "candidate_filename": self.candidate_filename,
            "job_title": self.job_title,
            "target_role": self.target_role,
            "interview_mode": self.interview_mode,
            "difficulty": self.difficulty,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "is_completed": self.is_completed,
            "elapsed_seconds": self.elapsed_seconds,
            "current_index": self.current_index,
            "questions": self.questions,
            "answers": self.answers,
            "evaluations": self.evaluations,
            "results_summary": summary or (self.get_results_summary() if self.is_completed else None)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewSession":
        session = cls(
            questions=data.get("questions", []),
            analysis_id=data.get("analysis_id"),
            candidate_filename=data.get("candidate_filename"),
            job_title=data.get("job_title"),
            target_role=data.get("target_role"),
            interview_mode=data.get("interview_mode", "mixed"),
            difficulty=data.get("difficulty", "all"),
            owner_id=data.get("owner_id", "anonymous"),
            session_id=data.get("session_id")
        )
        session.created_at = data.get("created_at", time.time())
        session.updated_at = data.get("updated_at", session.created_at)
        session.completed_at = data.get("completed_at")
        session.is_completed = bool(data.get("is_completed"))
        session.elapsed_seconds = data.get("elapsed_seconds", 0)
        session.current_index = data.get("current_index", 0)
        session.answers = data.get("answers", {})
        session.evaluations = data.get("evaluations", {})
        return session

    def _save_to_store(self, summary: Optional[Dict[str, Any]] = None):
        try:
            store = get_interview_session_store()
            store.save_session(self.to_dict(summary=summary))
        except Exception:
            pass


class InterviewSessionManager:
    """
    Factory and manager for isolated practice sessions with persistent storage.
    """

    @staticmethod
    def create_session(
        questions: List[Dict[str, Any]],
        analysis_id: Optional[str] = None,
        candidate_filename: Optional[str] = None,
        job_title: Optional[str] = None,
        target_role: Optional[str] = None,
        interview_mode: str = "mixed",
        difficulty: str = "all",
        owner_id: str = "anonymous",
        candidate_evidence: Optional[Dict[str, Any]] = None
    ) -> InterviewSession:
        session = InterviewSession(
            questions=questions,
            analysis_id=analysis_id,
            candidate_filename=candidate_filename,
            job_title=job_title,
            target_role=target_role,
            interview_mode=interview_mode,
            difficulty=difficulty,
            owner_id=owner_id,
            candidate_evidence=candidate_evidence
        )
        ACTIVE_SESSIONS[session.session_id] = session
        # Persist immediately to SQLite
        session._save_to_store()

        # Keep memory cache bounded to 100 active sessions
        if len(ACTIVE_SESSIONS) > 100:
            oldest_key = next(iter(ACTIVE_SESSIONS))
            del ACTIVE_SESSIONS[oldest_key]
        return session

    @staticmethod
    def get_session(session_id: str, owner_id: Optional[str] = None) -> Optional[InterviewSession]:
        """
        Retrieves a session from memory or persistent SQLite.
        If owner_id is provided, enforces session ownership isolation.
        """
        session = ACTIVE_SESSIONS.get(session_id)
        if session:
            if owner_id and session.owner_id != owner_id:
                return None
            return session

        # Fallback to persistent SQLite store
        try:
            store = get_interview_session_store()
            data = store.get_session(session_id, owner_id=owner_id)
            if data:
                session = InterviewSession.from_dict(data)
                ACTIVE_SESSIONS[session.session_id] = session
                return session
        except Exception:
            pass
        return None

    @staticmethod
    def delete_session(session_id: str, owner_id: Optional[str] = None) -> bool:
        """
        Safely deletes a session from memory and SQLite store.
        If owner_id is provided, verifies ownership before deleting.
        """
        session = ACTIVE_SESSIONS.get(session_id)
        if session and owner_id and session.owner_id != owner_id:
            return False

        if session_id in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[session_id]

        try:
            store = get_interview_session_store()
            if owner_id:
                return store.delete_session(session_id, owner_id=owner_id)
            else:
                # Direct delete if no owner specified
                with store._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM interview_sessions WHERE session_id = ?", (session_id,))
                    deleted = cursor.rowcount > 0
                    conn.commit()
                    return deleted
        except Exception:
            return True

    @staticmethod
    def list_sessions(owner_id: str, analysis_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves session history for an owner.
        """
        try:
            store = get_interview_session_store()
            return store.list_sessions(owner_id=owner_id, analysis_id=analysis_id, limit=limit)
        except Exception:
            return []

    @staticmethod
    def get_progress(owner_id: str, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregates practice progress metrics.
        """
        try:
            store = get_interview_session_store()
            return store.get_progress(owner_id=owner_id, analysis_id=analysis_id)
        except Exception:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "total_questions_attempted": 0,
                "average_score": 0.0,
                "categories_practiced": {},
                "struggled_topics": [],
                "recent_sessions": []
            }

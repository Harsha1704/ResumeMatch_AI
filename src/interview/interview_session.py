"""
Interview Session Manager Module.
Maintains active practice session state, answers, timer tracking, and aggregates results.
Ensures strict session isolation without leaking private data across users.
"""

import time
import uuid
from typing import Dict, List, Any, Optional

from .answer_evaluator import HeuristicAnswerEvaluator

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
        owner_session_id: Optional[str] = None
    ):
        self.session_id: str = str(uuid.uuid4())
        self.analysis_id: Optional[str] = analysis_id
        self.owner_session_id: Optional[str] = owner_session_id
        self.candidate_filename: str = candidate_filename or "Candidate Profile"
        self.job_title: str = job_title or "Target Role"
        self.created_at: float = time.time()
        self.questions: List[Dict[str, Any]] = questions
        self.current_index: int = 0
        self.answers: Dict[str, str] = {}
        self.evaluations: Dict[str, Dict[str, Any]] = {}
        self.guidance_revealed: Dict[str, bool] = {}
        self.is_completed: bool = False
        self.completed_at: Optional[float] = None
        self.elapsed_seconds: int = 0

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
        evaluator: Optional[HeuristicAnswerEvaluator] = None
    ) -> Dict[str, Any]:
        """Records an answer and computes heuristic evaluation."""
        if 0 <= question_index < len(self.questions):
            idx_str = str(question_index)
            self.answers[idx_str] = answer_text.strip()
            
            if evaluator is None:
                evaluator = HeuristicAnswerEvaluator()
                
            q_data = self.questions[question_index]
            eval_res = evaluator.evaluate_answer(q_data, answer_text)
            self.evaluations[idx_str] = eval_res
            return eval_res
        return {}

    def toggle_guidance(self, question_index: int, revealed: bool = True):
        if 0 <= question_index < len(self.questions):
            self.guidance_revealed[str(question_index)] = revealed

    def next_question(self) -> Optional[Dict[str, Any]]:
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
        return self.get_current_question()

    def prev_question(self) -> Optional[Dict[str, Any]]:
        if self.current_index > 0:
            self.current_index -= 1
        return self.get_current_question()

    def jump_to(self, index: int) -> Optional[Dict[str, Any]]:
        if 0 <= index < len(self.questions):
            self.current_index = index
        return self.get_current_question()

    def complete_session(self) -> Dict[str, Any]:
        self.is_completed = True
        self.completed_at = time.time()
        return self.get_results_summary()

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

        # Key points & framework stats across answered questions
        total_coverage_pct = 0.0
        frameworks_used: Dict[str, int] = {}
        all_strengths: List[str] = []
        all_improvements: List[str] = []

        for idx_str, ev in self.evaluations.items():
            # Count every answered question's framework, even when the answer is
            # too short to score. Insufficient answers contribute zero coverage.
            if self.answers.get(idx_str, "").strip():
                fw_name = ev.get("framework_adherence", {}).get("framework", "STAR")
                frameworks_used[fw_name] = frameworks_used.get(fw_name, 0) + 1

                if ev.get("status") == "evaluated":
                    cov = ev.get("key_point_coverage", {}).get("coverage_pct", 0.0)
                    total_coverage_pct += cov

                for s in ev.get("strengths", []):
                    if s not in all_strengths:
                        all_strengths.append(s)
                for imp in ev.get("areas_for_improvement", []):
                    if imp not in all_improvements:
                        all_improvements.append(imp)

        avg_coverage = round(total_coverage_pct / max(1, completed_count), 1) if completed_count > 0 else 0.0

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
                "framework": q.get("recommended_answer_framework"),
                "user_answer": ans,
                "is_answered": bool(ans.strip()),
                "evaluation": ev
            })

        return {
            "session_id": self.session_id,
            "total_questions": total_q,
            "completed_questions": completed_count,
            "completion_rate_pct": round((completed_count / max(1, total_q)) * 100, 1),
            "average_key_point_coverage_pct": avg_coverage,
            "category_distribution": cat_counts,
            "frameworks_practiced": frameworks_used,
            "strengths_observed": all_strengths[:5],
            "recommended_focus_areas": all_improvements[:5],
            "question_reviews": question_reviews,
            "job_title": self.job_title,
            "candidate_filename": self.candidate_filename,
            "is_completed": self.is_completed
        }


class InterviewSessionManager:
    """
    Factory and manager for isolated practice sessions.
    """

    @staticmethod
    def create_session(
        questions: List[Dict[str, Any]],
        analysis_id: Optional[str] = None,
        candidate_filename: Optional[str] = None,
        job_title: Optional[str] = None,
        owner_session_id: Optional[str] = None
    ) -> InterviewSession:
        session = InterviewSession(
            questions=questions,
            analysis_id=analysis_id,
            candidate_filename=candidate_filename,
            job_title=job_title,
            owner_session_id=owner_session_id
        )
        ACTIVE_SESSIONS[session.session_id] = session
        # Keep cache bounded to 50 active sessions
        if len(ACTIVE_SESSIONS) > 50:
            oldest_key = next(iter(ACTIVE_SESSIONS))
            del ACTIVE_SESSIONS[oldest_key]
        return session

    @staticmethod
    def get_session(session_id: str) -> Optional[InterviewSession]:
        return ACTIVE_SESSIONS.get(session_id)

    @staticmethod
    def validate_ownership(session_id: str, owner_id: Optional[str]) -> bool:
        """Validates that the session belongs to owner_id."""
        sess = ACTIVE_SESSIONS.get(session_id)
        if not sess:
            return False
        if sess.owner_session_id is None:
            return True  # Legacy/unattributed session
        return sess.owner_session_id == owner_id

    @staticmethod
    def delete_session(session_id: str):
        if session_id in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[session_id]

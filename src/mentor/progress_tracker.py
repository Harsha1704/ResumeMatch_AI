"""
Preparation Progress Tracker Module.
Maintains independent task tracking across four explicit stages:
- Not started
- Learning
- Practicing
- Completed

Explicitly adheres to:
- Manual user status updates only (never auto-marks mastered).
- Strict separation between learning tasks completed and verified professional proficiency.
"""

from typing import Dict, List, Any, Optional

VALID_STATUSES = ["Not started", "Learning", "Practicing", "Completed"]


class CandidateProgressTracker:
    """
    Session-bound progress tracker for skills and preparation roadmap stages.
    """

    def __init__(self):
        # Maps task_key (e.g. "docker_stage_1") -> status ("Not started", "Learning", "Practicing", "Completed")
        self.task_states: Dict[str, str] = {}
        # Tracks interview questions practiced via Interview Studio integration
        self.practiced_question_ids: List[str] = []

    def set_task_status(self, task_key: str, status: str):
        if status in VALID_STATUSES:
            self.task_states[task_key] = status

    def get_task_status(self, task_key: str) -> str:
        return self.task_states.get(task_key, "Not started")

    def record_practiced_question(self, question_id: str):
        if question_id and question_id not in self.practiced_question_ids:
            self.practiced_question_ids.append(question_id)

    def calculate_progress_summary(self, all_task_keys: List[str]) -> Dict[str, Any]:
        """
        Computes aggregate preparation progress across scheduled tasks.
        """
        total_tasks = len(all_task_keys)
        completed_count = sum(1 for k in all_task_keys if self.task_states.get(k) == "Completed")
        learning_count = sum(1 for k in all_task_keys if self.task_states.get(k) == "Learning")
        practicing_count = sum(1 for k in all_task_keys if self.task_states.get(k) == "Practicing")
        not_started_count = total_tasks - completed_count - learning_count - practicing_count

        completion_pct = round((completed_count / max(1, total_tasks)) * 100, 1) if total_tasks > 0 else 0.0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_count,
            "learning_tasks": learning_count,
            "practicing_tasks": practicing_count,
            "not_started_tasks": max(0, not_started_count),
            "completion_percentage": completion_pct,
            "interview_questions_attempted": len(self.practiced_question_ids),
            "disclaimer": "Preparation progress reflects your personal task completion in this study plan. It does not represent accredited or verified commercial employment qualifications."
        }

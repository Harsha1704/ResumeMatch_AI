"""
Local Interview Intelligence Backend Service (Strict ₹0 Budget).
Phase 2C Implementation: 100% Offline, Deterministic, Grounded in Resume & Job Evidence.

Key Capabilities:
- Zero External API Costs / Zero Billing: Pure CPU execution with no external LLMs.
- Grounded Question Generation: Leverages InterviewQuestionGenerator across 6 distinct categories.
- Heuristic Answer Evaluation: Real-time rubric evaluation, evidence detection, and concept coverage.
- Adaptive Follow-Ups: Dynamic follow-up selection tailored to candidate's previous response depth.
- Turn-Based Spoken Prompts: Generates concise, natural interviewer spoken scripts for browser speech synthesis (TTS).
- Strict Session Isolation: Validates session ownership and CSRF protection fail-closed.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from .question_generator import InterviewQuestionGenerator
from .interview_session import InterviewSessionManager, InterviewSession
from .answer_evaluator import HeuristicAnswerEvaluator
from .evidence_mapper import extract_candidate_evidence
from .session_store import get_interview_session_store

logger = logging.getLogger(__name__)

# Maximum allowed answer text length from speech recognition (defensive input guard)
MAX_ANSWER_TEXT_LENGTH = 10000


class LocalVoiceInterviewError(Exception):
    """Base exception for local voice interview errors."""
    pass


class LocalVoiceSessionNotFoundError(LocalVoiceInterviewError):
    """Raised when the requested interview session does not exist."""
    pass


class LocalVoiceAccessDeniedError(LocalVoiceInterviewError):
    """Raised when an unauthenticated or unauthorized owner accesses a session."""
    pass


class LocalVoiceValidationError(LocalVoiceInterviewError):
    """Raised when request payload or parameters fail validation."""
    pass


class LocalVoiceInterviewService:
    """
    Dedicated local interview intelligence service for voice interview rooms.
    Runs entirely on-device/in-memory with zero cloud API dependencies.
    """

    @classmethod
    def start_session(
        cls,
        owner_id: str,
        analysis_data: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None,
        candidate_filename: Optional[str] = None,
        job_title: Optional[str] = None,
        target_role: Optional[str] = None,
        difficulty: str = "all",
        interview_mode: str = "mixed",
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        max_questions: int = 10
    ) -> Dict[str, Any]:
        """
        Initializes a grounded voice interview session using local intelligence.
        Generates resume and job-description grounded questions without external LLM calls.
        """
        if not owner_id or not isinstance(owner_id, str):
            raise LocalVoiceValidationError("Valid session owner_id is required.")

        # Prepare analysis structure if raw text is provided
        analysis = dict(analysis_data) if isinstance(analysis_data, dict) else {}
        if analysis_id and not analysis.get("analysis_id"):
            analysis["analysis_id"] = analysis_id

        if resume_text and not analysis.get("resume_text"):
            analysis["resume_text"] = resume_text[:20000]

        effective_role = (target_role or job_title or analysis.get("job_title") or "Software Engineer").strip()
        if not analysis.get("job_title"):
            analysis["job_title"] = effective_role
        if not analysis.get("target_role"):
            analysis["target_role"] = effective_role

        if job_description and not analysis.get("job_description"):
            analysis["job_description"] = job_description[:10000]

        # 1. Extract verified evidence
        candidate_evidence = extract_candidate_evidence(analysis)

        # 2. Generate grounded questions using the deterministic question generator
        generator = InterviewQuestionGenerator(analysis)
        questions = generator.generate_questions(
            category="ALL",
            difficulty=difficulty or "all",
            max_questions=max_questions or 10,
            interview_mode=interview_mode or "mixed",
            target_role=effective_role
        )

        if not questions:
            # Fallback safe technical questions if generator returns empty
            questions = generator.generate_category_e(max_questions=5)

        # 3. Create active session in InterviewSessionManager
        session_obj = InterviewSessionManager.create_session(
            questions=questions,
            analysis_id=analysis_id or analysis.get("analysis_id"),
            candidate_filename=candidate_filename or analysis.get("candidate_filename") or "Candidate",
            job_title=effective_role,
            target_role=effective_role,
            interview_mode=interview_mode,
            difficulty=difficulty,
            owner_id=owner_id,
            candidate_evidence=candidate_evidence
        )

        current_q = session_obj.get_current_question()
        q_text = current_q.get("question_text", "") if current_q else ""

        # Formulate initial welcoming script for browser speech synthesis (TTS)
        cand_name = candidate_evidence.get("candidate_name") or "Candidate"
        interviewer_greeting = (
            f"Hello and welcome to your mock interview for the role of {effective_role}. "
            f"I will be asking you several technical and experience-based questions. "
            f"Please speak clearly after each question. Let's begin with your first question: {q_text}"
        )

        # Phase 3 Relational & Transcript Persistence
        store = get_interview_session_store()
        try:
            store.save_questions(session_obj.session_id, questions)
            store.append_transcript_entry(
                session_id=session_obj.session_id,
                speaker="interviewer",
                message_type="greeting",
                message_text=interviewer_greeting
            )
            if current_q:
                first_prompt = f"Question 1 of {session_obj.total_questions}: {q_text}"
                store.append_transcript_entry(
                    session_id=session_obj.session_id,
                    speaker="interviewer",
                    message_type="question",
                    message_text=first_prompt,
                    question_id=current_q.get("question_id")
                )
        except Exception as e:
            logger.warning("Could not persist initial questions/transcript: %s", e)

        return {
            "status": "success",
            "session_id": session_obj.session_id,
            "target_role": effective_role,
            "difficulty": difficulty,
            "total_questions": session_obj.total_questions,
            "current_index": 0,
            "current_question": current_q,
            "interviewer_speech": interviewer_greeting,
            "provider": "local_grounded_engine",
            "budget": "₹0"
        }

    @classmethod
    def get_question(
        cls,
        session_id: str,
        owner_id: str,
        direction: str = "current"
    ) -> Dict[str, Any]:
        """
        Retrieves current, next, or previous question for an active voice interview.
        Prepares concise spoken question prompt for browser TTS.
        """
        session_obj = cls._get_authorized_session(session_id, owner_id)

        if direction == "next":
            q_data = session_obj.next_question()
        elif direction == "prev":
            q_data = session_obj.prev_question()
        else:
            q_data = session_obj.get_current_question()

        if not q_data:
            return {
                "status": "completed",
                "session_id": session_id,
                "message": "All interview questions have been completed.",
                "total_questions": session_obj.total_questions,
                "current_index": session_obj.current_index
            }

        q_number = session_obj.current_index + 1
        q_text = q_data.get("question_text", "")

        # Conversational transition for browser speech synthesis
        interviewer_speech = f"Question {q_number} of {session_obj.total_questions}: {q_text}"

        # Phase 3: Record question navigation in transcript
        if direction in ("next", "prev"):
            store = get_interview_session_store()
            try:
                store.append_transcript_entry(
                    session_id=session_id,
                    speaker="interviewer",
                    message_type="question",
                    message_text=interviewer_speech,
                    question_id=q_data.get("question_id")
                )
            except Exception as e:
                logger.warning("Could not append question to transcript: %s", e)

        return {
            "status": "success",
            "session_id": session_id,
            "current_index": session_obj.current_index,
            "question_number": q_number,
            "total_questions": session_obj.total_questions,
            "question": q_data,
            "interviewer_speech": interviewer_speech
        }

    @classmethod
    def submit_answer(
        cls,
        session_id: str,
        owner_id: str,
        question_index: int,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Submits candidate's spoken answer (transcribed to text by browser speech recognition).
        Evaluates heuristic completeness, strengths, and missing concepts.
        Generates natural spoken reaction for browser TTS.
        """
        session_obj = cls._get_authorized_session(session_id, owner_id)

        if session_obj.is_completed:
            raise LocalVoiceValidationError("Cannot submit answers to an already completed interview session.")

        if not isinstance(question_index, int) or question_index < 0 or question_index >= len(session_obj.questions):
            raise LocalVoiceValidationError(f"Invalid question_index {question_index}. Must be between 0 and {len(session_obj.questions) - 1}.")

        if not isinstance(answer_text, str):
            raise LocalVoiceValidationError("answer_text must be a string.")

        clean_answer = answer_text.strip()
        if not clean_answer:
            raise LocalVoiceValidationError("answer_text cannot be empty.")

        if len(clean_answer) > MAX_ANSWER_TEXT_LENGTH:
            raise LocalVoiceValidationError(f"answer_text exceeds maximum allowed length of {MAX_ANSWER_TEXT_LENGTH} characters.")

        # Evaluate using heuristic rubric
        evaluator = HeuristicAnswerEvaluator()
        eval_result = session_obj.submit_answer(
            question_index=question_index,
            answer_text=clean_answer,
            evaluator=evaluator
        )

        overall_score = float(eval_result.get("overall_score") or 0.0)
        word_count = int(eval_result.get("word_count") or 0)
        missing_concepts = eval_result.get("missing_concepts") or []
        strengths = eval_result.get("strengths") or []

        # Formulate natural, concise conversational reaction for browser TTS
        spoken_reaction = cls._build_spoken_reaction(overall_score, word_count, missing_concepts, strengths)

        # Check if question has pre-computed follow-ups available
        current_q = session_obj.questions[question_index]
        has_followups = bool(current_q.get("follow_up_questions"))

        # Phase 3 Relational & Transcript Persistence
        store = get_interview_session_store()
        qid = current_q.get("question_id") or f"q_{question_index}"
        try:
            aid = store.save_answer(session_id=session_id, question_id=qid, answer_text=clean_answer)
            store.save_evaluation(answer_id=aid, session_id=session_id, question_id=qid, eval_data=eval_result)
            store.append_transcript_entry(
                session_id=session_id,
                speaker="candidate",
                message_type="answer",
                message_text=clean_answer,
                question_id=qid,
                answer_id=aid
            )
            store.append_transcript_entry(
                session_id=session_id,
                speaker="interviewer",
                message_type="feedback",
                message_text=spoken_reaction,
                question_id=qid,
                answer_id=aid
            )
        except Exception as e:
            logger.warning("Could not persist answer/evaluation/transcript: %s", e)

        return {
            "status": "success",
            "session_id": session_id,
            "question_index": question_index,
            "evaluation": eval_result,
            "interviewer_reaction": spoken_reaction,
            "has_adaptive_followup": has_followups,
            "is_last_question": (question_index >= len(session_obj.questions) - 1)
        }

    @classmethod
    def generate_adaptive_followup(
        cls,
        session_id: str,
        owner_id: str,
        question_index: int
    ) -> Dict[str, Any]:
        """
        Selects an adaptive follow-up question grounded in the candidate's previous response depth.
        """
        session_obj = cls._get_authorized_session(session_id, owner_id)

        if not isinstance(question_index, int) or question_index < 0 or question_index >= len(session_obj.questions):
            raise LocalVoiceValidationError(f"Invalid question_index {question_index}.")

        current_q = session_obj.questions[question_index]
        followups = current_q.get("follow_up_questions") or []

        if not followups:
            # Fallback follow-up if question bank does not have specific items
            topic = current_q.get("topic") or current_q.get("related_skill") or "this technology"
            followup_obj = {
                "question": f"Can you describe a specific technical challenge or edge case you encountered when implementing {topic}?",
                "reference_answer": "In production, handling edge cases requires defensive parameter validation, automated unit testing, and graceful error recovery.",
                "interview_takeaway": "Provide a concrete production example rather than purely theoretical descriptions.",
                "practical_example": "Benchmarking under peak load or handling network timeouts."
            }
        else:
            # Select first or most relevant follow-up
            followup_obj = followups[0]

        followup_text = followup_obj.get("question", "")
        spoken_followup = f"Following up on that: {followup_text}"

        # Phase 3 Persistence: record follow-up question and transcript entry
        store = get_interview_session_store()
        parent_qid = current_q.get("question_id") or f"q_{question_index}"
        followup_qid = f"{parent_qid}_fu_{int(time.time())}"
        try:
            store.save_questions(session_id, [{
                "question_id": followup_qid,
                "question_text": followup_text,
                "category": "Follow-Up",
                "is_follow_up": 1,
                "parent_question_id": parent_qid
            }])
            store.append_transcript_entry(
                session_id=session_id,
                speaker="interviewer",
                message_type="followup",
                message_text=spoken_followup,
                question_id=followup_qid
            )
        except Exception as e:
            logger.warning("Could not persist follow-up question/transcript: %s", e)

        return {
            "status": "success",
            "session_id": session_id,
            "question_index": question_index,
            "follow_up": followup_obj,
            "interviewer_speech": spoken_followup
        }

    @classmethod
    def complete_session(
        cls,
        session_id: str,
        owner_id: str
    ) -> Dict[str, Any]:
        """
        Concludes the voice interview session and generates a structured performance report.
        Prepares final concluding remarks for browser speech synthesis.
        Idempotent: repeating an end request returns the stored report without duplicate entries.
        """
        session_obj = cls._get_authorized_session(session_id, owner_id)
        store = get_interview_session_store()

        # Idempotency check: if report already exists, return it without re-appending closing message
        existing_report = store.get_final_report(session_id, owner_id)
        if existing_report:
            return {
                "status": "success",
                "session_id": session_id,
                "is_completed": True,
                "results": session_obj.get_results_summary(),
                "final_report": existing_report,
                "interviewer_speech": (
                    f"Welcome back. This mock voice interview is already completed. "
                    f"Your overall evaluation score was {round(float(existing_report.get('average_score', 0)), 1)} percent."
                ),
                "provider": "local_grounded_engine",
                "budget": "₹0"
            }

        results_summary = session_obj.complete_session()
        total_q = session_obj.total_questions
        answered_q = len(session_obj.answers)
        overall_score = results_summary.get("overall_score") or results_summary.get("average_score") or 0.0

        concluding_speech = (
            f"Thank you for completing this mock voice interview! You responded to {answered_q} of {total_q} questions. "
            f"Your overall evaluation score is {round(float(overall_score), 1)} percent. "
            f"Your comprehensive performance breakdown and category insights are now available on screen."
        )

        # Phase 3 Persistence: closing transcript and final report
        try:
            store.append_transcript_entry(
                session_id=session_id,
                speaker="interviewer",
                message_type="closing",
                message_text=concluding_speech
            )
            report_dict = {
                "total_questions": total_q,
                "questions_answered": answered_q,
                "average_score": float(overall_score),
                "strengths": results_summary.get("strengths", []),
                "improvement_areas": results_summary.get("areas_for_improvement", []),
                "category_performance": results_summary.get("category_performance", {}),
                "summary_text": concluding_speech,
                "completed_at": time.time()
            }
            final_report = store.save_final_report(session_id, report_dict)
        except Exception as e:
            logger.warning("Could not persist closing transcript/report: %s", e)
            final_report = results_summary

        return {
            "status": "success",
            "session_id": session_id,
            "is_completed": True,
            "results": results_summary,
            "final_report": final_report,
            "interviewer_speech": concluding_speech,
            "provider": "local_grounded_engine",
            "budget": "₹0"
        }

    @classmethod
    def get_voice_history(cls, owner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves user's voice interview history."""
        if not owner_id or not isinstance(owner_id, str):
            raise LocalVoiceValidationError("Valid session owner_id is required.")
        store = get_interview_session_store()
        return store.get_voice_history(owner_id, limit)

    @classmethod
    def get_voice_session_detail(cls, session_id: str, owner_id: str) -> Dict[str, Any]:
        """Retrieves full voice session bundle with questions, answers, evaluations, report, and ordered transcript."""
        cls._get_authorized_session(session_id, owner_id)
        store = get_interview_session_store()
        detail = store.get_voice_session_detail(session_id, owner_id)
        if not detail:
            raise LocalVoiceSessionNotFoundError(f"Voice interview detail for '{session_id}' not found.")
        return detail

    @classmethod
    def _get_authorized_session(cls, session_id: str, owner_id: str) -> InterviewSession:
        """Validates session existence and verifies owner isolation fail-closed."""
        if not session_id or not isinstance(session_id, str):
            raise LocalVoiceValidationError("Missing or invalid session_id.")

        session_obj = InterviewSessionManager.get_session(session_id.strip())
        if not session_obj:
            raise LocalVoiceSessionNotFoundError(f"Interview session '{session_id}' not found.")

        # Strict session ownership check
        if session_obj.owner_id and session_obj.owner_id != "anonymous":
            if owner_id != session_obj.owner_id:
                logger.warning("Unauthorized voice session access attempt: caller %s != owner %s", owner_id, session_obj.owner_id)
                raise LocalVoiceAccessDeniedError("Access denied: You do not have permission to view or modify this interview session.")

        return session_obj

    @staticmethod
    def _build_spoken_reaction(
        score: float,
        word_count: int,
        missing_concepts: List[str],
        strengths: List[str]
    ) -> str:
        """Generates natural, concise conversational interviewer reaction for browser TTS."""
        if word_count < 10:
            return "Thank you. That answer was quite brief. In an interview, aim to share a bit more context and detail."

        if score >= 75.0:
            if strengths:
                return f"Great explanation. You covered {strengths[0].lower().rstrip('.')}. Let's keep this momentum going."
            return "Well explained. That demonstrated good technical understanding."

        if score >= 50.0:
            if missing_concepts:
                first_missing = str(missing_concepts[0]).replace("_", " ")
                return f"Solid answer. You touched on the main idea, and you can strengthen it by highlighting {first_missing}."
            return "Good response. You addressed the core concept."

        # Lower score or missing foundational points
        if missing_concepts:
            first_missing = str(missing_concepts[0]).replace("_", " ")
            return f"Thank you for that response. To make it more comprehensive, consider expanding on {first_missing}."

        return "Thank you. Let's move on to explore the next aspect."

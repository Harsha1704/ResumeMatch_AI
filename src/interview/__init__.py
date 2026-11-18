"""
Interview Intelligence Studio package.
Provides deterministic, resume-aware interview preparation, curated question banks,
structured answer frameworks, and transparent heuristic evaluation.
"""

from .answer_frameworks import FRAMEWORKS, get_framework, format_answer_template
from .question_bank import TECHNICAL_QUESTION_BANK, HR_QUESTION_BANK, get_all_technical_topics
from .difficulty_engine import filter_by_difficulty, classify_question_difficulty
from .evidence_mapper import extract_candidate_evidence, ground_guidance_in_evidence
from .question_generator import InterviewQuestionGenerator
from .interview_session import InterviewSessionManager
from .answer_evaluator import HeuristicAnswerEvaluator
from .gemini_voice_service import (
    GeminiVoiceService,
    VoiceSessionRateLimiter,
    get_voice_rate_limiter,
    strip_candidate_pii,
)
from .local_voice_service import (
    LocalVoiceInterviewService,
    LocalVoiceInterviewError,
    LocalVoiceSessionNotFoundError,
    LocalVoiceAccessDeniedError,
    LocalVoiceValidationError,
)

from .session_store import InterviewSessionStore, get_interview_session_store

__all__ = [
    "FRAMEWORKS",
    "get_framework",
    "format_answer_template",
    "TECHNICAL_QUESTION_BANK",
    "HR_QUESTION_BANK",
    "get_all_technical_topics",
    "filter_by_difficulty",
    "classify_question_difficulty",
    "extract_candidate_evidence",
    "ground_guidance_in_evidence",
    "InterviewQuestionGenerator",
    "InterviewSessionManager",
    "HeuristicAnswerEvaluator",
    "InterviewSessionStore",
    "get_interview_session_store",
    "GeminiVoiceService",
    "VoiceSessionRateLimiter",
    "get_voice_rate_limiter",
    "strip_candidate_pii",
    "LocalVoiceInterviewService",
    "LocalVoiceInterviewError",
    "LocalVoiceSessionNotFoundError",
    "LocalVoiceAccessDeniedError",
    "LocalVoiceValidationError",
]

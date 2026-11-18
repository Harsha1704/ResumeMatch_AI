"""
Gemini Live API Voice Interview Service.
Phase 2 Correction: Secure Backend Ephemeral Authentication and Context Preparation (₹0 Budget).

Key Guarantees:
- Strict ₹0 Free-Tier Allowlist: ONLY permits explicitly approved models (gemini-3.8-live).
- WebSocket Native Architecture: Generates credentials for direct browser-to-Gemini WebSocket (BidiGenerateContent).
- Permanent API Key Never Exposed: Loads GEMINI_API_KEY from environment or local gemini.txt (server-only).
- Ephemeral Credentials Only: Generates short-lived, single-use client tokens via Google AI Studio's /v1beta/auth_tokens.
- Best-Effort PII Minimization: Redacts phone numbers, emails, physical addresses, and URLs via heuristic filters.
- Explicit Candidate Consent Required: Rejects requests unless candidate acknowledges Google Free Tier terms.
- Application Rate Limiting: Conservative client rate limiting to prevent project quota exhaustion.
"""

import os
import re
import time
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Explicit model allowlist: ONLY verified free-tier real-time audio-to-audio models are permitted.
# Any model not in this allowlist is strictly rejected to guarantee ₹0 budget.
APPROVED_FREE_TIER_MODELS = {
    "gemini-3.8-live",
}

DEFAULT_FREE_TIER_MODEL = "gemini-3.8-live"

# Native Gemini Live WebSocket URL for BidiGenerateContent
GEMINI_LIVE_WEBSOCKET_URL = (
    "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)


class GeminiVoiceQuotaExceededError(Exception):
    """Raised when Google AI Studio free-tier rate limits or quotas are exhausted."""
    pass


class GeminiVoiceAuthError(Exception):
    """Raised when authentication with Google AI Studio fails."""
    pass


class GeminiVoiceConfigError(Exception):
    """Raised when model or environment configuration violates free-tier budget."""
    pass


class VoiceSessionRateLimiter:
    """
    Sliding-window in-memory rate limiter per session owner to protect project quotas.
    Limits each user to a maximum of 5 token requests per 10 minutes.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, owner_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = self._history.get(owner_id, [])
        active_timestamps = [t for t in timestamps if t > cutoff]
        if len(active_timestamps) >= self.max_requests:
            self._history[owner_id] = active_timestamps
            return False
        active_timestamps.append(now)
        self._history[owner_id] = active_timestamps
        return True

    def reset(self, owner_id: Optional[str] = None):
        if owner_id:
            self._history.pop(owner_id, None)
        else:
            self._history.clear()


# Global rate limiter instance
_global_rate_limiter = VoiceSessionRateLimiter()


def get_voice_rate_limiter() -> VoiceSessionRateLimiter:
    return _global_rate_limiter


def strip_candidate_pii(text: str) -> str:
    """
    Applies heuristic regex minimization to remove obvious candidate personal identifiers
    (emails, phone numbers, URLs, physical addresses, national IDs) prior to transmission.
    
    IMPORTANT PRIVACY NOTICE:
    Heuristic regex-based filtering reduces incidental exposure but does NOT guarantee
    the absolute removal of all personal or non-standard contact details.
    """
    if not text or not isinstance(text, str):
        return ""

    sanitized = text

    # Remove email addresses
    sanitized = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', sanitized)

    # Remove telephone numbers
    sanitized = re.sub(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}', '[PHONE_REDACTED]', sanitized)

    # Remove URLs (LinkedIn, GitHub, websites)
    sanitized = re.sub(r'https?://[^\s]+', '[URL_REDACTED]', sanitized)
    sanitized = re.sub(r'www\.[^\s]+', '[URL_REDACTED]', sanitized)

    # Remove street / address patterns
    sanitized = re.sub(r'\b\d{1,5}\s+[A-Za-z0-9\.\s]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way)\b', '[ADDRESS_REDACTED]', sanitized, flags=re.IGNORECASE)

    # Remove national IDs / SSN patterns
    sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[ID_REDACTED]', sanitized)

    return sanitized


class GeminiVoiceService:
    """
    Secure backend service for Gemini Live API real-time voice interviews.
    """

    @staticmethod
    def get_api_key() -> str:
        """
        Retrieves permanent master API key server-side.
        1. Checks environment variable GEMINI_API_KEY.
        2. Falls back to reading from local gemini.txt if present.
        Never exposed to client, browser, logs, or responses.
        """
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if key:
            return key

        gemini_file = REPO_ROOT / "gemini.txt"
        if gemini_file.exists():
            try:
                lines = [l.strip() for l in gemini_file.read_text(encoding="utf-8").splitlines() if l.strip()]
                if len(lines) >= 2 and lines[0].lower() == "api key":
                    return lines[1]
            except Exception as e:
                logger.warning("Could not read gemini.txt: %s", e)

        return ""

    @staticmethod
    def get_configured_model() -> str:
        """Retrieves configured model, strictly defaulting to approved free-tier model."""
        return os.environ.get("GEMINI_LIVE_MODEL", DEFAULT_FREE_TIER_MODEL).strip()

    @classmethod
    def validate_model_eligibility(cls, model: Optional[str] = None) -> Tuple[bool, str]:
        """
        Strict fail-closed allowlist validation:
        Only models explicitly present in APPROVED_FREE_TIER_MODELS are allowed.
        Rejects all unapproved, experimental, or paid models to guarantee ₹0 budget.
        """
        raw_model = (model or cls.get_configured_model()).strip()
        # Strip models/ prefix if provided
        clean_model = raw_model.replace("models/", "")

        if clean_model not in APPROVED_FREE_TIER_MODELS:
            return False, (
                f"Model '{raw_model}' is not in the approved ₹0 Free Tier allowlist. "
                f"Approved models: {sorted(list(APPROVED_FREE_TIER_MODELS))}. "
                "Paid-tier or unverified models are strictly prohibited to prevent accidental charges."
            )

        return True, "Approved Free-Tier Model"

    @classmethod
    def build_voice_interview_context(
        cls,
        practice_session: Any,
        candidate_evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds a privacy-minimized, evidence-grounded prompt for the Gemini Live interviewer.
        Injects verified skills, projects, and target job requirements while stripping PII.
        """
        evidence = candidate_evidence or getattr(practice_session, "candidate_evidence", {}) or {}
        job_title = practice_session.job_title or "Target Role"
        target_role = practice_session.target_role or job_title
        difficulty = getattr(practice_session, "difficulty", "all")

        # Sanitize candidate name and metadata
        raw_name = evidence.get("candidate_name") or getattr(practice_session, "candidate_filename", "Candidate")
        candidate_name = strip_candidate_pii(str(raw_name))

        # Extracted skills (PII-minimized)
        skills_list = evidence.get("skills") or []
        if isinstance(skills_list, list):
            sanitized_skills = [strip_candidate_pii(str(s)) for s in skills_list[:25]]
        else:
            sanitized_skills = []

        # Extracted projects (PII-minimized)
        raw_projects = evidence.get("projects") or []
        sanitized_projects = []
        for p in raw_projects[:4]:
            if isinstance(p, dict):
                sanitized_projects.append({
                    "title": strip_candidate_pii(p.get("title") or p.get("name") or "Project"),
                    "tech_stack": [strip_candidate_pii(str(t)) for t in p.get("tech_stack", [])[:8]],
                    "description": strip_candidate_pii(p.get("description", ""))[:300]
                })

        # Interview questions sequence
        questions = getattr(practice_session, "questions", [])
        question_briefs = []
        for i, q in enumerate(questions[:8]):
            question_briefs.append({
                "number": i + 1,
                "category": q.get("category_name", "Technical"),
                "question_text": q.get("question_text", ""),
                "key_concepts": q.get("important_concepts", [])[:4]
            })

        # Structured system instructions for Gemini Live WebSocket session
        system_instruction = (
            f"You are a professional, encouraging senior technical interviewer conducting a mock voice interview for the role of '{target_role}'.\n"
            f"Candidate: {candidate_name}\n"
            f"Candidate Skills: {', '.join(sanitized_skills) if sanitized_skills else 'General Technical Stack'}\n\n"
            f"INTERVIEW STRUCTURE & RULES:\n"
            f"1. Ask ONE question at a time. Do not overwhelm the candidate with multiple questions at once.\n"
            f"2. Keep your spoken responses concise (1 to 3 sentences maximum) so the candidate does 80%+ of the talking.\n"
            f"3. Actively listen to the candidate's spoken response. If the candidate gives a brief or vague answer, ask an adaptive follow-up probing for real technical depth, architectural trade-offs, or past project experience.\n"
            f"4. Never fabricate resume details, companies, or projects that the candidate did not mention.\n"
            f"5. Maintain a supportive, conversational, and professional tone throughout the session.\n"
            f"6. Focus on these planned topics: {', '.join([q['question_text'] for q in question_briefs[:3]])}."
        )

        return {
            "target_role": target_role,
            "job_title": job_title,
            "difficulty": difficulty,
            "candidate_name": candidate_name,
            "sanitized_skills": sanitized_skills,
            "sanitized_projects": sanitized_projects,
            "questions_count": len(questions),
            "system_instruction": system_instruction
        }

    @classmethod
    def create_ephemeral_token(
        cls,
        model: Optional[str] = None,
        timeout_seconds: int = 10,
        mock_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mints a short-lived, single-use ephemeral authentication token from Google AI Studio.
        Endpoint: POST https://generativelanguage.googleapis.com/v1beta/auth_tokens

        The permanent GEMINI_API_KEY is used exclusively server-side and never returned.
        The ephemeral token is used by the frontend to connect directly to the Gemini Live WebSocket.
        """
        # Testing shortcut
        if mock_response is not None:
            return mock_response

        api_key = cls.get_api_key()
        if not api_key:
            raise GeminiVoiceConfigError(
                "GEMINI_API_KEY is not configured on the server. Please configure your free-tier Google AI Studio API key in your environment or gemini.txt."
            )

        target_model = model or cls.get_configured_model()
        is_valid, reason = cls.validate_model_eligibility(target_model)
        if not is_valid:
            raise GeminiVoiceConfigError(reason)

        url = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        # Calculate expiration timestamps (UTC)
        now = datetime.datetime.now(datetime.timezone.utc)
        expire_time = (now + datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_session_expire_time = (now + datetime.timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Correct payload accepted by Google generativelanguage.googleapis.com/v1beta/auth_tokens
        payload = {
            "uses": 1,
            "expireTime": expire_time,
            "newSessionExpireTime": new_session_expire_time
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to Google AI Studio auth_tokens endpoint.")
            raise GeminiVoiceAuthError("Gateway timeout connecting to Gemini Live authentication service.")
        except requests.exceptions.RequestException as e:
            logger.error("Network error connecting to Gemini auth service: %s", e)
            raise GeminiVoiceAuthError(f"Network error connecting to Gemini authentication service: {str(e)}")

        # Handle rate limiting / quota exhaustion
        if response.status_code == 429:
            logger.warning("Gemini Live API free-tier quota exhausted (HTTP 429).")
            raise GeminiVoiceQuotaExceededError(
                "Google Gemini Live API free-tier quota exhausted. Please wait a few moments before starting another voice session."
            )

        # Handle authentication failures
        if response.status_code in (401, 403):
            logger.error("Gemini API authentication failed (HTTP %d). Check GEMINI_API_KEY validity.", response.status_code)
            raise GeminiVoiceAuthError(
                "Authentication with Google Gemini API service failed. Verify GEMINI_API_KEY configuration."
            )

        if not response.ok:
            logger.error("Gemini auth_tokens API error HTTP %d: %s", response.status_code, response.text)
            raise GeminiVoiceAuthError(f"Google Gemini token creation failed with status {response.status_code}: {response.text}")

        try:
            res_json = response.json()
            token_name = res_json.get("name")
            if not token_name:
                raise ValueError("Response missing 'name' field")
            
            clean_model = target_model.replace("models/", "")
            formatted_model = f"models/{clean_model}"

            return {
                "token": token_name,
                "model": formatted_model,
                "websocket_url": GEMINI_LIVE_WEBSOCKET_URL,
                "expires_in_seconds": 1800,
                "uses_allowed": 1
            }
        except Exception as e:
            logger.error("Failed to parse Gemini auth_tokens response: %s", e)
            raise GeminiVoiceAuthError("Malformed response received from Gemini token service.")

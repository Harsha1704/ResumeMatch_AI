"""
Candidate Name Extractor Module.
Extracts candidate's preferred first name from parsed resume header text.
Enforces strict rules:
- Strictly does NOT infer names from email addresses, URLs, or phone numbers.
- Handles uncertain or ambiguous name extraction with graceful fallback.
- Avoids exposing full legal names unnecessarily.
- Dynamically generates mentor titles (e.g. "Harsha's Career Mentor" vs "Your Career Mentor").
- Supports user-edited preferred display names.
"""

import re
from typing import Dict, Any, Optional

DISALLOWED_NAME_TOKENS = {
    "resume", "curriculum", "vitae", "cv", "profile", "summary", "objective",
    "contact", "phone", "email", "address", "education", "experience", "projects",
    "skills", "technical", "page", "developer", "engineer", "scientist", "analyst",
    "intern", "candidate", "name", "student", "portfolio", "github", "linkedin"
}


def extract_candidate_name(resume_text: Optional[str]) -> Dict[str, Any]:
    """
    Deterministically identifies a candidate's preferred name from resume header lines.
    Returns:
    - preferred_name: str (e.g. "Harsha" or fallback "Candidate")
    - full_name: Optional[str]
    - mentor_title: str ("{Name}'s Career Mentor" or "Your Career Mentor")
    - is_confident: bool
    """
    fallback_res = {
        "preferred_name": "Candidate",
        "full_name": None,
        "mentor_title": "Your Career Mentor",
        "is_confident": False,
        "extraction_method": "fallback"
    }

    if not resume_text or not isinstance(resume_text, str):
        return fallback_res

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return fallback_res

    # Inspect the first 5 non-empty lines
    candidate_lines = lines[:5]

    for raw_line in candidate_lines:
        line = raw_line.strip()

        # Skip lines that contain email, phone numbers, or web URLs
        if re.search(r"[@\+0-9]|http|www\.|\.com|\.org|\.edu|\.io|linkedin|github", line, re.I):
            continue

        # Strip subtitle/role suffixes after delimiters like ' - ', ' | ', ' – ', ' — ', ' / '
        cleaned_line = re.split(r"\s+[-–—|/]\s+", line)[0].strip()

        # Strip leading numbering (e.g. "1. Harsha Vardhan")
        cleaned_line = re.sub(r"^\d+[\.\)]\s*", "", cleaned_line).strip()

        # Check token validity
        tokens = cleaned_line.split()
        if not (1 <= len(tokens) <= 4):
            continue

        # Check if all tokens are alphabetic words
        is_alpha_name = all(
            re.match(r"^[A-Za-z]+(?:'[A-Za-z]+)?\.?$", tok) and tok.lower() not in DISALLOWED_NAME_TOKENS
            for tok in tokens
        )

        if is_alpha_name:
            full_name = " ".join(t.capitalize() for t in tokens)
            first_name = tokens[0].capitalize()

            # Ignore generic placeholders
            if first_name.lower() in DISALLOWED_NAME_TOKENS:
                continue

            return {
                "preferred_name": first_name,
                "full_name": full_name,
                "mentor_title": f"{first_name}'s Career Mentor",
                "is_confident": True,
                "extraction_method": "header_heuristic"
            }

    return fallback_res


def format_mentor_identity(user_override_name: Optional[str], extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies user-edited preferred display name or defaults to extracted/fallback name.
    """
    if user_override_name and isinstance(user_override_name, str) and user_override_name.strip():
        clean_override = user_override_name.strip().split()[0].capitalize()
        return {
            "preferred_name": clean_override,
            "full_name": clean_override,
            "mentor_title": f"{clean_override}'s Career Mentor",
            "is_confident": True,
            "is_user_override": True
        }

    return {
        "preferred_name": extracted_info.get("preferred_name", "Candidate"),
        "full_name": extracted_info.get("full_name"),
        "mentor_title": extracted_info.get("mentor_title", "Your Career Mentor"),
        "is_confident": extracted_info.get("is_confident", False),
        "is_user_override": False
    }

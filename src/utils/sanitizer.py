"""
Centralized Output Sanitizer Module for ResumeMatch AI.
Ensures zero placeholders, unrendered templates, internal error codes, or broken grammar
reach user-visible interfaces.
"""

from typing import Any, Dict, List, Optional, Union
import re


# Disallowed literal placeholder strings that must never be presented as proper names or valid content
DISALLOWED_LITERAL_NAME = "Candidate"
DEFAULT_ROLE_FALLBACK = "Target role not specified"
OLD_ROLE_FALLBACK = "Target Position"
OLD_EDU_NOTE = "Verified against degree mentions in parsed resume."
CLEAN_EDU_NOTE = "Education details not confidently identified"

# Regex for bracketed prompt/customization placeholders
BRACKETED_PLACEHOLDER_REGEX = re.compile(
    r"\[(?:Mention|Personal Detail to Customize|Optional Personal Detail|Describe specific|Personal Detail)[^\]]*\]",
    re.IGNORECASE
)

# Regex for unrendered Jinja tags
UNRENDERED_JINJA_REGEX = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")

# Regex for literal None/null artifacts in strings
LITERAL_NONE_REGEX = re.compile(r"\b(?:None|null|undefined)\b")


def sanitize_text(text: Optional[str]) -> str:
    """
    Sanitizes a single text string by removing placeholders, brackets, and template artifacts.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. Clean old role fallback
    text = text.replace(OLD_ROLE_FALLBACK, DEFAULT_ROLE_FALLBACK)

    # 2. Clean old degree note if present verbatim
    text = text.replace(OLD_EDU_NOTE, CLEAN_EDU_NOTE)

    # 3. Strip bracketed placeholders cleanly
    text = BRACKETED_PLACEHOLDER_REGEX.sub("", text)

    # 4. Strip unrendered Jinja syntax
    text = UNRENDERED_JINJA_REGEX.sub("", text)

    # 5. Fix common grammar defects
    text = re.sub(r"\bwhile its was\b", "while it was", text)
    text = re.sub(r"\bwhile its prioritizes\b", "while it prioritizes", text)
    text = re.sub(r"\bwhile its provides\b", "while it provides", text)
    text = re.sub(r"\bwhile its delivers\b", "while it delivers", text)
    text = re.sub(r"\bwhile its acts\b", "while it acts", text)
    text = re.sub(r"\bwhile its enables\b", "while it enables", text)
    text = re.sub(r"\bwhile its offers\b", "while it offers", text)
    text = re.sub(r"\bwhile its leverages\b", "while it leverages", text)
    text = re.sub(r"\bwhile its\b", "while it", text)

    # Clean "to address Built a..." / "to address Developed a..."
    text = re.sub(
        r"(?i)\bto address\s+(?:built|developed|designed|created|engineered|implemented|trained|deployed)\s+(?:an?|the)?\s*",
        "to implement a ",
        text
    )

    # Clean whitespace and trailing punctuation after bracket removal
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"\([,\s]*\)", "", text)
    text = re.sub(r"\[[,\s]*\]", "", text)

    return text.strip()


def extract_customization_prompts(text: Optional[str]) -> List[str]:
    """
    Extracts any bracketed personal customization suggestions so they can be shown
    in dedicated prompt boxes rather than embedded in polished answer text.
    """
    if not text or not isinstance(text, str):
        return []

    matches = BRACKETED_PLACEHOLDER_REGEX.findall(text)
    prompts = []
    for m in matches:
        clean = m.strip("[]").strip()
        # Clean prefix like "Personal Detail to Customize:"
        clean = re.sub(r"^(?:personal detail to customize|optional personal detail|mention|describe)\s*[:\-]?\s*", "", clean, flags=re.I)
        if clean and clean not in prompts:
            prompts.append(clean)
    return prompts


def clean_project_title(title: Optional[str]) -> str:
    """
    Strips repository metadata, URLs, and noisy suffixes from project titles.
    "Brain Tumor Classification | GitHub" -> "Brain Tumor Classification"
    """
    if not title or not isinstance(title, str):
        return "Technical Project"

    # Strip GitHub / URL / Repo markers
    cleaned = re.sub(
        r"(?i)\s*(?:\|\s*|\s*-\s*|\s*–\s*|\s*—\s*)?(?:github(?:\.com)?|repo|repository|code|demo|website|url)\s*[:\-]?\s*(?:https?://\S+)?",
        "",
        title
    ).strip(" |-,()[]")

    # Strip any bare URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", cleaned).strip(" |-,()[]")

    if not cleaned or len(cleaned) < 2:
        return "Technical Project"
    return cleaned


def format_estimated_hours(hours: Any) -> Optional[str]:
    """
    Formats estimated hours cleanly. Eliminates '~h' or '~0h'.
    Returns None if missing/invalid so UI can omit the badge.
    """
    if hours is None:
        return None
    try:
        val = float(hours)
        if val <= 0:
            return None
        if val.is_integer():
            return f"~{int(val)} hrs"
        return f"~{val:.1f} hrs"
    except (ValueError, TypeError):
        return None


def sanitize_data_structure(data: Any) -> Any:
    """
    Recursively traverses dictionaries, lists, and strings to sanitize visible outputs.
    """
    if isinstance(data, dict):
        sanitized_dict = {}
        for k, v in data.items():
            if k == "preferred_name" and v == DISALLOWED_LITERAL_NAME:
                # Replace proper-name "Candidate" with empty string so templates handle gracefully
                sanitized_dict[k] = ""
            elif k in {"target_role", "job_title"} and v == OLD_ROLE_FALLBACK:
                sanitized_dict[k] = DEFAULT_ROLE_FALLBACK
            elif k == "notes" and v == OLD_EDU_NOTE:
                sanitized_dict[k] = CLEAN_EDU_NOTE
            else:
                sanitized_dict[k] = sanitize_data_structure(v)
        return sanitized_dict
    elif isinstance(data, list):
        return [sanitize_data_structure(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    else:
        return data

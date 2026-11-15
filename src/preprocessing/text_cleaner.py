"""
Text Cleaning and Normalization Utilities for Resume & Job Description Processing.
Preserves technical tokens (C++, C#, .NET, Node.js, etc.) and extracts explicit experience.
"""

import re
import html
import unicodedata
from typing import Dict, List, Optional, Tuple


# Regex pattern to preserve technical tokens with symbols
PRESERVED_TOKEN_PATTERN = r"(?i)\b(?:c\+\+|c#|\.net|node\.js|vue\.js|react\.js|angular\.js|pl/sql|tcp/ip|ci/cd)\b"

# Section header patterns common in resumes
SECTION_HEADERS = [
    "experience",
    "work experience",
    "employment history",
    "professional experience",
    "education",
    "academic background",
    "qualifications",
    "skills",
    "technical skills",
    "core competencies",
    "projects",
    "key projects",
    "certifications",
    "licenses",
    "summary",
    "professional summary",
    "objective",
    "publications",
    "awards",
    "achievements",
    "languages"
]

SECTION_REGEX = re.compile(
    r"(?im)^(?:\s*#*\s*)(?:" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r")\s*[:\n\-]"
)

# Experience extraction pattern: captures explicit mentions like "5+ years of experience", "3 yrs exp", "6+ years of professional software engineering experience", etc.
EXPERIENCE_PATTERN = re.compile(
    r"(?i)\b(?:(\d{1,2}(?:\.\d+)?)\s*(?:\+|-|\s*to\s*\d{1,2})?\s*(?:years?|yrs?)(?:\s+(?:of|in))?(?:\s+[a-zA-Z]{2,20}){0,3}\s+(?:experience|exp)\b"
    r"|(?:experience|exp)\s*(?:of|:)?\s*(\d{1,2}(?:\.\d+)?)\+?\s*(?:years?|yrs?))\b"
)


def clean_text(text: Optional[str]) -> str:
    """
    Cleans and standardizes raw text:
    - Normalizes Unicode (NFKC)
    - Unescapes HTML entities and strips HTML tags
    - Replaces odd punctuation while safeguarding technical tokens (C++, C#, .NET, Node.js)
    - Normalizes whitespace
    """
    if not text or not isinstance(text, str):
        return ""

    # Normalize Unicode representations
    text = unicodedata.normalize("NFKC", text)

    # Decode HTML entities (e.g. &amp;, &lt;, &nbsp;)
    text = html.unescape(text)

    # Remove HTML tags if present
    text = re.sub(r"<[^>]+>", " ", text)

    # Protect technical tokens before generic punctuation stripping
    # We substitute preserved tokens with unique placeholders
    replacements: Dict[str, str] = {
        r"(?i)\bc\+\+": " __TECH_TOKEN_CPP__ ",
        r"(?i)\bc#": " __TECH_TOKEN_CSHARP__ ",
        r"(?i)\.net\b": " __TECH_TOKEN_DOTNET__ ",
        r"(?i)\bnode\.js\b": " __TECH_TOKEN_NODEJS__ ",
        r"(?i)\bvue\.js\b": " __TECH_TOKEN_VUEJS__ ",
        r"(?i)\breact\.js\b": " __TECH_TOKEN_REACTJS__ ",
        r"(?i)\bangular\.js\b": " __TECH_TOKEN_ANGULARJS__ ",
        r"(?i)\bpl/sql\b": " __TECH_TOKEN_PLSQL__ ",
        r"(?i)\btcp/ip\b": " __TECH_TOKEN_TCPIP__ ",
        r"(?i)\bci/cd\b": " __TECH_TOKEN_CICD__ ",
    }

    protected_text = text
    for pattern, placeholder in replacements.items():
        protected_text = re.sub(pattern, placeholder, protected_text)

    # Remove email addresses and URLs to prevent identifier overfitting
    protected_text = re.sub(r"\S+@\S+\.\S+", " ", protected_text)
    protected_text = re.sub(r"https?://\S+|www\.\S+", " ", protected_text)

    # Replace formatting symbols (bullet points, pipes, tabs, weird quotes) with whitespace
    protected_text = re.sub(r"[\t\r\n\xa0\u2022\u25cf\u25cb\u25aa\u25ab\u25ba\u2013\u2014|\\/]", " ", protected_text)

    # Remove special characters except alphanumeric, basic punctuation, underscores, and dashes
    protected_text = re.sub(r"[^\w\s\.\,\-\_]", " ", protected_text)

    # Restore protected technical tokens in normalized lowercase
    restorations = {
        "__TECH_TOKEN_CPP__": "c++",
        "__TECH_TOKEN_CSHARP__": "c#",
        "__TECH_TOKEN_DOTNET__": ".net",
        "__TECH_TOKEN_NODEJS__": "node.js",
        "__TECH_TOKEN_VUEJS__": "vue.js",
        "__TECH_TOKEN_REACTJS__": "react.js",
        "__TECH_TOKEN_ANGULARJS__": "angular.js",
        "__TECH_TOKEN_PLSQL__": "pl/sql",
        "__TECH_TOKEN_TCPIP__": "tcp/ip",
        "__TECH_TOKEN_CICD__": "ci/cd",
    }
    for placeholder, restored in restorations.items():
        protected_text = protected_text.replace(placeholder, f" {restored} ")

    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", protected_text).strip()
    return cleaned


def extract_explicit_experience_years(text: Optional[str]) -> float:
    """
    Extracts the highest explicitly stated years of experience from text.
    Returns 0.0 if no explicit experience years are mentioned.
    Strictly follows the non-negotiable rule: DO NOT invent experience.
    """
    if not text or not isinstance(text, str):
        return 0.0

    matches = EXPERIENCE_PATTERN.findall(text)
    years_found: List[float] = []

    for m in matches:
        # Group 1 or Group 2 contains the number
        val_str = m[0] if m[0] else m[1]
        if val_str:
            try:
                y = float(val_str)
                # Cap unrealistic single numbers (e.g. 1998, 2024 dates accidentally captured)
                if 0.5 <= y <= 40.0:
                    years_found.append(y)
            except ValueError:
                pass

    if years_found:
        return max(years_found)
    return 0.0


def parse_structural_features(text: Optional[str]) -> Dict[str, float]:
    """
    Parses structural attributes of a resume or job description:
    - word count
    - character count
    - detected section count
    - explicit years of experience
    """
    if not text or not isinstance(text, str):
        return {
            "word_count": 0.0,
            "char_count": 0.0,
            "section_count": 0.0,
            "explicit_years_exp": 0.0
        }

    cleaned = clean_text(text)
    words = cleaned.split()
    word_count = float(len(words))
    char_count = float(len(cleaned))

    # Detect section headers in original formatted text
    sections = len(SECTION_REGEX.findall(text))
    # If standard multiline regex found 0, check inline headers
    if sections == 0:
        lower_raw = text.lower()
        sections = sum(1 for h in SECTION_HEADERS if h in lower_raw)

    explicit_years = extract_explicit_experience_years(text)

    return {
        "word_count": word_count,
        "char_count": char_count,
        "section_count": float(sections),
        "explicit_years_exp": explicit_years
    }

"""
Candidate Profile Extractor Module.
Extracts structured candidate profile information from resume raw text:
- Candidate name (integrating with mentor name extractor)
- Contact details: email addresses, phone numbers, portfolio / GitHub / LinkedIn URLs
- Structured education records: degree levels, majors, institutions, graduation years, GPA
- Structured certifications: title, issuer, year
- Duplicate skills detection across sections
- Conflicting information detection (e.g. chronology conflicts, future graduation vs tenure)
- Missing field tracking without hallucination

Zero LLM reliance. Fully deterministic.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import re
from datetime import datetime

from src.mentor.name_extractor import extract_candidate_name
from src.analysis.experience_analyzer import split_resume_into_sections


EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Phone number regex supporting international and standard domestic formats
# Requires at least 7 and at most 15 digits; excludes pure 4-digit years or standalone numbers
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b"
)

LINKEDIN_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|profile)/[A-Za-z0-9_-]+/?",
    re.I
)

GITHUB_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)?/?",
    re.I
)

GENERIC_URL_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.(?:com|org|io|dev|me|net|tech|app|edu|ai)(?:/[^\s,;\)]*)?",
    re.I
)

DEGREE_LEVEL_PATTERNS = [
    ("Doctorate", [r"\bph\.?d\b", r"\bdoctorate\b", r"\bdoctoral\b"]),
    ("Master's", [r"\bmaster(?:'s)?\b", r"\bm\.?tech\b", r"\bm\.?e\.?\b", r"\bm\.?s\.?\b", r"\bm\.?sc\b", r"\bmba\b", r"\bpostgraduate\b"]),
    ("Bachelor's", [r"\bbachelor(?:'s)?\b", r"\bb\.?tech\b", r"\bb\.?e\.?\b", r"\bb\.?s\.?\b", r"\bb\.?sc\b", r"\bb\.?a\b", r"\bundergraduate\b"]),
    ("Associate", [r"\bassociate(?:'s)?\b", r"\bdiploma\b"]),
]

FIELD_OF_STUDY_PATTERNS = [
    r"computer\s+science(?:\s+and\s+engineering)?",
    r"information\s+technology",
    r"software\s+engineering",
    r"electrical(?:\s+and\s+electronics)?\s+engineering",
    r"electronics(?:\s+and\s+communication)?\s+engineering",
    r"mechanical\s+engineering",
    r"civil\s+engineering",
    r"data\s+science",
    r"artificial\s+intelligence(?:\s+and\s+machine\s+learning)?",
    r"machine\s+learning",
    r"cybersecurity",
    r"mathematics",
    r"statistics",
    r"physics",
    r"business\s+administration",
    r"economics",
]

INSTITUTION_MARKERS = [
    r"university", r"college", r"institute", r"school\s+of", r"academy",
    r"polytechnic", r"\biit\b", r"\bnit\b", r"\bbits\b", r"\bstanford\b",
    r"\bmit\b", r"\bharvard\b", r"\bberkeley\b", r"\boxford\b", r"\bcambridge\b"
]

YEAR_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\b")
GPA_REGEX = re.compile(r"(?i)\b(?:cgpa|gpa)[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)")


def extract_candidate_profile(raw_text: Optional[str], cleaned_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministically parses structured candidate information:
    - Name and titles
    - Contact info: emails, phones, professional links
    - Structured education history
    - Certifications
    - Duplicate skill occurrences across sections
    - Information inconsistencies and conflicts
    - Explicit list of missing fields
    """
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        return {
            "name": {
                "preferred_name": "Candidate",
                "full_name": None,
                "mentor_title": "Your Career Mentor",
                "is_confident": False,
                "extraction_method": "fallback"
            },
            "contact_info": {
                "emails": [],
                "primary_email": "Not provided",
                "phones": [],
                "primary_phone": "Not provided",
                "links": {
                    "linkedin": "Not provided",
                    "github": "Not provided",
                    "portfolio": "Not provided",
                    "all_links": []
                }
            },
            "education": [],
            "certifications": [],
            "duplicate_skills": [],
            "conflicts": [],
            "missing_fields": ["name", "email", "phone", "education", "linkedin", "github"]
        }

    # 1. Candidate Name
    name_info = extract_candidate_name(raw_text)

    # 2. Contact Information
    emails = _extract_emails(raw_text)
    phones = _extract_phones(raw_text)
    links_dict = _extract_links(raw_text)

    # 3. Section Partitioning
    sections = split_resume_into_sections(raw_text)

    # 4. Education Extraction
    education_records = _extract_education(raw_text, sections.get("education", []))

    # 5. Certifications Extraction
    certifications_records = _extract_certifications(raw_text, sections.get("certifications", []))

    # 6. Duplicate Skills Detection Across Sections
    duplicate_skills = _detect_duplicate_skills(sections)

    # 7. Conflicting Information Detection
    conflicts = _detect_conflicts(raw_text, education_records)

    # 8. Missing Fields Tracking
    missing_fields = []
    if not name_info.get("is_confident"):
        missing_fields.append("confident_name")
    if not emails:
        missing_fields.append("email")
    if not phones:
        missing_fields.append("phone")
    if not links_dict["linkedin"] or links_dict["linkedin"] == "Not provided":
        missing_fields.append("linkedin")
    if not links_dict["github"] or links_dict["github"] == "Not provided":
        missing_fields.append("github")
    if not education_records:
        missing_fields.append("education")
    if not certifications_records:
        missing_fields.append("certifications")

    return {
        "name": name_info,
        "contact_info": {
            "emails": emails,
            "primary_email": emails[0] if emails else "Not provided",
            "phones": phones,
            "primary_phone": phones[0] if phones else "Not provided",
            "links": links_dict
        },
        "education": education_records,
        "certifications": certifications_records,
        "duplicate_skills": duplicate_skills,
        "conflicts": conflicts,
        "missing_fields": missing_fields
    }


def _extract_emails(text: str) -> List[str]:
    raw_matches = EMAIL_REGEX.findall(text)
    seen = set()
    cleaned = []
    for email in raw_matches:
        e_lower = email.lower().strip()
        # Filter out common placeholders or document artifacts
        if any(p in e_lower for p in ["yourname@", "example.com", "email.com", "user@domain"]):
            continue
        if e_lower not in seen:
            seen.add(e_lower)
            cleaned.append(email.strip())
    return cleaned


def _extract_phones(text: str) -> List[str]:
    candidates = PHONE_REGEX.findall(text)
    valid_phones = []
    seen = set()

    for cand in candidates:
        s = cand.strip()
        digits = re.sub(r"\D", "", s)
        # Require 7-15 digits and avoid capturing standalone years (e.g. 2020-2024 is 8 digits, but split by dash)
        if 7 <= len(digits) <= 15:
            # Check if this is a year range like "2020 - 2024"
            if re.search(r"\b(19\d{2}|20\d{2})\s*[-–—]\s*(19\d{2}|20\d{2})\b", s):
                continue
            if digits not in seen:
                seen.add(digits)
                valid_phones.append(s)
    return valid_phones


def _extract_links(text: str) -> Dict[str, Any]:
    linkedin = "Not provided"
    github = "Not provided"
    portfolio = "Not provided"
    all_links = []
    seen_links = set()

    # LinkedIn
    l_matches = LINKEDIN_REGEX.findall(text)
    if l_matches:
        linkedin = l_matches[0].strip()
        seen_links.add(linkedin.lower())
        all_links.append(linkedin)

    # GitHub
    g_matches = GITHUB_REGEX.findall(text)
    if g_matches:
        github = g_matches[0].strip()
        seen_links.add(github.lower())
        all_links.append(github)

    # All URLs (strip emails first to prevent email domains from being treated as portfolio URLs)
    text_without_emails = EMAIL_REGEX.sub(" ", text)
    for m in GENERIC_URL_REGEX.finditer(text_without_emails):
        url = m.group(0).strip().rstrip(".,;")
        if url.lower() not in seen_links:
            seen_links.add(url.lower())
            all_links.append(url)
            # Identify possible personal portfolio
            if portfolio == "Not provided":
                lower_u = url.lower()
                if not any(k in lower_u for k in ["linkedin", "github", "twitter", "medium", "facebook", "instagram"]):
                    portfolio = url

    return {
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
        "all_links": all_links
    }


def _extract_education(raw_text: str, edu_lines: List[str]) -> List[Dict[str, Any]]:
    records = []
    text_to_scan = edu_lines if edu_lines else [l.strip() for l in raw_text.splitlines() if l.strip()]

    # Group adjacent education lines into logical blocks
    blocks: List[List[str]] = []
    current_block: List[str] = []

    for line in text_to_scan:
        has_degree = any(any(re.search(p, line, re.I) for p in pats) for _, pats in DEGREE_LEVEL_PATTERNS)
        has_institution = any(re.search(rf"\b{m}\b", line, re.I) for m in INSTITUTION_MARKERS)

        if has_degree or has_institution:
            if current_block and (has_degree or len(current_block) >= 4):
                blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
        elif current_block:
            current_block.append(line)
            if len(current_block) >= 4:
                blocks.append(current_block)
                current_block = []

    if current_block:
        blocks.append(current_block)

    for block in blocks:
        block_text = " | ".join(block)
        degree_level = "Not specified"
        for level, pats in DEGREE_LEVEL_PATTERNS:
            if any(re.search(p, block_text, re.I) for p in pats):
                degree_level = level
                break

        # Degree name
        degree_name = "Degree"
        for line in block:
            for level, pats in DEGREE_LEVEL_PATTERNS:
                for p in pats:
                    m = re.search(rf"([^|,\n]*{p}[^|,\n]*)", line, re.I)
                    if m:
                        degree_name = m.group(1).strip()
                        break
                if degree_name != "Degree":
                    break
            if degree_name != "Degree":
                break

        # Field of study
        field_of_study = "Not specified"
        for f_pat in FIELD_OF_STUDY_PATTERNS:
            m = re.search(rf"\b({f_pat})\b", block_text, re.I)
            if m:
                field_of_study = m.group(1).title()
                break

        # Institution
        institution = "Not specified"
        for line in block:
            for marker in INSTITUTION_MARKERS:
                if re.search(rf"\b{marker}\b", line, re.I):
                    institution = line.strip("•-*–|, ")
                    break
            if institution != "Not specified":
                break

        # Graduation year
        grad_year = None
        years = YEAR_REGEX.findall(block_text)
        if years:
            grad_year = int(years[-1])

        # GPA
        gpa = None
        gpa_m = GPA_REGEX.search(block_text)
        if gpa_m:
            gpa = gpa_m.group(1).strip()

        records.append({
            "degree_level": degree_level,
            "degree_name": degree_name if degree_name != "Degree" else degree_level,
            "field_of_study": field_of_study,
            "institution": institution,
            "graduation_year": grad_year,
            "gpa": gpa,
            "raw_text": block_text
        })

    return records


def _extract_certifications(raw_text: str, cert_lines: List[str]) -> List[Dict[str, Any]]:
    records = []
    lines = cert_lines if cert_lines else []
    if not lines:
        # Search for explicit certification lines in raw text
        for line in raw_text.splitlines():
            s = line.strip()
            if any(k in s.lower() for k in ["certified", "certificate", "certification", "credential"]):
                lines.append(s)

    known_issuers = ["aws", "amazon", "google", "microsoft", "azure", "cisco", "oracle", "coursera", "udacity", "ibm", "deeplearning.ai", "meta"]

    for line in lines:
        s = line.strip("•-*–|, ")
        if not s or len(s) < 5:
            continue
        lower_line = s.lower()

        issuer = "Not specified"
        for iss in known_issuers:
            if iss in lower_line:
                issuer = iss.upper() if iss in ["aws", "ibm"] else iss.title()
                break

        year = None
        years = YEAR_REGEX.findall(s)
        if years:
            year = years[-1]

        records.append({
            "title": s,
            "issuer": issuer,
            "year": year,
            "raw_text": s
        })

    return records


def _detect_duplicate_skills(sections: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Identifies skills mentioned redundantly across multiple resume sections.
    """
    from src.preprocessing.skill_extractor import SkillEngine
    try:
        engine = SkillEngine()
    except Exception:
        return []

    section_skills: Dict[str, Set[str]] = {}
    for sec_name, lines in sections.items():
        if sec_name in ("header", "contact"):
            continue
        text = " ".join(lines)
        skills = {s for s in engine.extract_skills(text)}
        if skills:
            section_skills[sec_name] = skills

    # Count occurrences across sections
    skill_sec_map: Dict[str, List[str]] = {}
    for sec_name, skills in section_skills.items():
        for s in skills:
            skill_sec_map.setdefault(s, []).append(sec_name)

    duplicates = []
    for skill, secs in skill_sec_map.items():
        if len(secs) > 1:
            duplicates.append({
                "skill": skill,
                "sections": secs,
                "count": len(secs)
            })

    duplicates.sort(key=lambda x: x["count"], reverse=True)
    return duplicates


def _detect_conflicts(raw_text: str, education_records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Identifies contradictions or suspicious chronologies:
    - Future graduation year while claiming extensive full-time experience
    - Contradictory tenure dates
    """
    conflicts = []
    current_year = datetime.now().year

    for edu in education_records:
        grad_year = edu.get("graduation_year")
        if grad_year and grad_year > current_year:
            # Check if resume claims 5+ years of full-time experience
            from src.preprocessing.text_cleaner import extract_explicit_experience_years
            exp = extract_explicit_experience_years(raw_text)
            if exp >= 5.0:
                conflicts.append({
                    "conflict_type": "chronological_anomaly",
                    "description": (
                        f"Candidate has future graduation year ({grad_year}) but explicitly claims "
                        f"{exp} years of professional experience."
                    )
                })

    # Check for inverted date ranges e.g. "2024 - 2021"
    inverted_dates = re.findall(r"\b(20\d{2}|19\d{2})\s*[-–—]\s*(20\d{2}|19\d{2})\b", raw_text)
    for start_yr, end_yr in inverted_dates:
        if int(start_yr) > int(end_yr):
            conflicts.append({
                "conflict_type": "inverted_date_range",
                "description": f"Detected inverted chronological date range: {start_yr} - {end_yr}."
            })

    return conflicts

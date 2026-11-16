"""
Deterministic Job Description NLP Analyzer.
Extracts:
- Job title
- 3 mutually exclusive requirement categories:
  1. REQUIRED (Must have, mandatory, essential, minimum qualifications)
  2. PREFERRED (Preferred, nice to have, bonus, advantageous, desirable)
  3. UNSPECIFIED (Skills mentioned without explicit requirement strength)
- Required experience duration
- Minimum educational requirements
Zero LLM reliance. Fully deterministic.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import re
from src.preprocessing.text_cleaner import clean_text, extract_explicit_experience_years
from src.preprocessing.skill_extractor import SkillEngine, categorize_competency


# Section-level and local linguistic markers
REQUIRED_PATTERNS = [
    r"\bmust\s+(?:have|possess|demonstrate|exhibit|be|include)\b",
    r"\brequired\s*(?:skills|qualifications|experience|requirements)?\b",
    r"\b(?:is|are)\s+required\b",
    r"\brequire[ds]?\b",
    r"\bminimum\s*(?:qualifications|requirements)\b",
    r"\bbasic\s*qualifications\b",
    r"\bessential\s*(?:skills|requirements|qualifications)?\b",
    r"\bmandatory\b",
    r"\bprerequisites?\b",
    r"\bcore\s+requirements?\b",
    r"\bneed\s+to\s+have\b",
    r"\bshould\s+have\b",
    r"\bwhat\s+(?:you\s+need|you'll\s+need|we're\s+looking\s+for)\b",
    r"\bkey\s+skills?\b",
    r"\bqualifications?\b",
    r"\brequirements?\b"
]

PREFERRED_PATTERNS = [
    r"\bpreferred\s*(?:skills|qualifications|experience|requirements)?\b",
    r"\bnice\s*to\s*have\b",
    r"\bgood\s*to\s*have\b",
    r"\bbonus\s*(?:points|skills)?\b",
    r"\bplus(?:\s+if|\s+points)?\b",
    r"\b(?:a\s+)?plus\b",
    r"\bwould\s+be\s+(?:a\s+plus|nice|great|beneficial|advantageous)\b",
    r"\bdesired\s*(?:skills|qualifications|experience)?\b",
    r"\badvantageous\b",
    r"\bdesirable\b",
    r"\bbeneficial\b",
    r"\boptional\s*(?:skills|qualifications|requirements)?\b",
    r"\bideal(?:ly)?\b",
    r"\bnot\s+required\s+but\b"
]

# Disqualifying headings and phrases that must never be mistaken for job titles
DISQUALIFYING_TITLE_PHRASES = [
    r"\babout\s+(?:us|the\s+company|our\s+company|the\s+team|you)\b",
    r"\bcompany\s+overview\b",
    r"\bwho\s+we\s+are\b",
    r"\bour\s+mission\b",
    r"\bjob\s+(?:description|overview|summary|purpose)\b",
    r"\bposition\s+(?:overview|summary)\b",
    r"\brole\s+(?:overview|summary)\b",
    r"\bresponsibilities\b",
    r"\bduties\b",
    r"\bwhat\s+you(?:'ll|\s+will)\s+do\b",
    r"\bkey\s+responsibilities\b",
    r"\brequirements\b",
    r"\bqualifications\b",
    r"\bwhat\s+we(?:'re|\s+are)\s+looking\s+for\b",
    r"\bminimum\s+qualifications\b",
    r"\bbasic\s+qualifications\b",
    r"\bpreferred\s+qualifications\b",
    r"\bbenefits\b",
    r"\bperks\b",
    r"\bcompensation\b",
    r"\bequal\s+opportunity\b",
    r"\bhow\s+to\s+apply\b",
    r"\breporting\s+to\b",
    r"\bexperience\s+with\b",
    r"\bcollaborate\s+with\b",
    r"\byou\s+will\b",
    r"\bwe\s+are\s+a\b",
    r"\bcandidate\s+should\b",
    r"\blooking\s+for\s+a\s+qualified\s+candidate\b",
]

# Explicit role labels
EXPLICIT_ROLE_LABELS = [
    r"(?i)^[#*_\-\s]*(?:job\s+title|position\s+title|position|role\s+title|role|job\s+opening|opening\s+for|job\s+opportunity)[#*_\-\s]*[:\-–—]\s*(.+)$",
    r"(?i)^[#*_\-\s]*(?:we\s+are\s+hiring(?:\s+for)?|we'?re\s+hiring(?:\s+for)?|hiring\s+for)[#*_\-\s]*[:\-–—]?\s*(.+)$",
]

# Known core title nouns indicating genuine technical or professional roles
CORE_ROLE_NOUNS = {
    "engineer", "developer", "analyst", "architect", "scientist", "manager",
    "specialist", "intern", "consultant", "lead", "director", "administrator",
    "programmer", "technician", "designer", "officer", "coordinator", "expert"
}

# Acronyms to preserve in Title Casing
TITLE_ACRONYMS = {
    "AI", "ML", "NLP", "QA", "UI", "UX", "GCP", "AWS", "iOS", "CI/CD",
    "SRE", "DBA", "BI", "IT", "ETL", "API", "SDK", "PHP", "SQL", "CRM", "ERP"
}


def _clean_and_format_title(raw_title: str) -> str:
    """Sanitizes an extracted title, strips noise/salary/location, and normalizes casing."""
    t = raw_title.strip()
    # Strip markdown and bullet characters
    t = re.sub(r"^[#*_\-\s•:|~`]+", "", t)
    t = re.sub(r"[#*_\-\s•:|~`]+$", "", t).strip()

    # Remove parenthetical metadata like (Remote), (Full Time), (Hybrid), (US/Canada), (L5), etc.
    t = re.sub(r"\((?:remote|hybrid|on-?site|full-?time|part-?time|contract|permanent|fte|temp|freelance|l\d|level\s*\d|us|usa|uk|emea|apac|[a-z\s,/–—-]+)\)", "", t, flags=re.I).strip()

    # Remove salary expressions: e.g. - $140k-$160k, ($120,000 - $150,000), etc.
    t = re.sub(r"(?:[-–—|]\s*)?\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:k|kilo|usd|eur|gbp)?\s*(?:[-–—to]+\s*\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:k|kilo|usd|eur|gbp)?)?(?:\s*(?:per|/)\s*(?:year|yr|hour|hr|annum))?", "", t, flags=re.I).strip()

    # Remove trailing location metadata: e.g. - San Francisco, CA or | Remote
    t = re.sub(r"(?:[-–—|]\s*)(?:remote|hybrid|on-?site|san francisco|new york|london|seattle|austin|berlin|toronto|boston|chicago|bangalore|singapore).*$", "", t, flags=re.I).strip()

    # Remove trailing fluff: "to join our team...", "with Python..."
    t = re.sub(r"(?i)\s+(?:to\s+join\s+our\s+team|with\s+(?:strong\s+)?(?:python|java|c\+\+|sql|aws|experience|skills)).*$", "", t).strip()

    # Remove leading recruitment adjectives e.g. "talented", "passionate", "exceptional"
    t = re.sub(r"^(?:talented|motivated|passionate|dynamic|exceptional|enthusiastic|qualified|successful)\s+", "", t, flags=re.I).strip()

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip(" -–—|:,;.")

    if not t or len(t) < 3 or len(t) > 75:
        return ""

    # Disqualifying check
    t_lower = t.lower()
    for dp in DISQUALIFYING_TITLE_PHRASES:
        if re.search(dp, t_lower):
            return ""

    # Ensure it contains at least one core role noun or indicator
    words = set(re.findall(r"\b[a-z]{3,}\b", t_lower))
    if not words.intersection(CORE_ROLE_NOUNS) and not any(kw in t_lower for kw in ["devops", "fullstack", "full stack", "frontend", "front end", "backend", "back end"]):
        return ""

    # Sentence check: titles are noun phrases, not clauses with verbs/pronouns
    sentence_markers = {"you", "we", "our", "your", "they", "will", "responsible", "qualification", "requirement", "description"}
    if len(words.intersection(sentence_markers)) >= 2:
        return ""

    # Nicely title case while preserving acronyms
    parts = t.split()
    formatted = []
    for w in parts:
        clean_w = re.sub(r"[^\w/]", "", w)
        upper_w = clean_w.upper()
        if upper_w in TITLE_ACRONYMS:
            formatted.append(upper_w)
        elif upper_w == "DEVOPS":
            formatted.append("DevOps")
        elif upper_w == "FULLSTACK":
            formatted.append("Full Stack")
        elif clean_w.lower() in {"and", "of", "in", "for", "the", "to", "with"}:
            formatted.append(clean_w.lower())
        else:
            formatted.append(w.capitalize())

    # Ensure first word is capitalized (preserving acronyms and DevOps)
    if formatted:
        if formatted[0].upper() not in TITLE_ACRONYMS and formatted[0] != "DevOps":
            formatted[0] = formatted[0][0].upper() + formatted[0][1:]

    return " ".join(formatted)

EDUCATION_PATTERNS = [
    # 1. Degrees with major (e.g., Bachelor's in Computer Science, Master's degree in Engineering)
    r"(?i)\b(?:bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|associate'?s?)\s+(?:degree\s+)?(?:in\s+)?([a-z\s,/]+?)(?:\.|\n|;|,|\s+or\s+(?:equivalent|related)|\s*$)",
    # 2. Tech-specific degrees (B.Tech, M.Tech, B.E., M.E., B.Sc., M.Sc., BCA, MCA)
    r"(?i)\b(?:b\.?tech|m\.?tech|b\.?e\.?|m\.?e\.?|b\.?sc\.?|m\.?sc\.?|bca|mca)\b(?:\s+(?:degree\s+)?(?:in\s+)?([a-z\s,/]+?))?(?:\.|\n|;|,|\s+or\s+(?:equivalent|related)|\s*$)",
    # 3. Strict B.S. / M.S. (MUST have 'degree' or 'in <field>' to avoid MS Word / MS Excel false positives)
    r"(?i)\b(?:b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?a\.?)\s+(?:degree(?:\s+in\s+([a-z\s,/]+?))?|in\s+([a-z\s,/]+?))(?:\.|\n|;|,|\s+or\s+(?:equivalent|related)|\s*$)",
    # 4. Field followed by degree (e.g., Computer Science degree, Engineering degree)
    r"(?i)\b(computer\s+science|software\s+engineering|information\s+technology|data\s+science|electrical\s+engineering|computer\s+engineering|engineering|mathematics|statistics)\s+degree\b",
    # 5. Generic degree in field
    r"(?i)\b(?:degree|diploma)\s+in\s+([a-z\s,/]+?)(?:\.|\n|;|,|\s+or\s+(?:equivalent|related)|\s*$)"
]

EXCLUDED_EDUCATION_KEYWORDS = {
    "word", "excel", "powerpoint", "office", "access", "visio", "teams", "outlook",
    "project", "sharepoint", "dynamics", "azure", "intune", "suite", "google docs",
    "google sheets", "photoshop", "illustrator", "tools", "sql", "python", "java",
    "c++", "c#", "javascript", "linux", "aws", "docker", "years", "experience"
}


class JobDescriptionAnalyzer:
    """
    Deterministic rule-based NLP analyzer for job descriptions.
    Classifies qualifications into REQUIRED, PREFERRED, and UNSPECIFIED tiers.
    """

    def __init__(self):
        self.skill_engine = SkillEngine()

    def extract_job_title(self, text: str) -> str:
        """
        Attempts to identify the job position title from document headers or explicit tags.
        Returns 'Target role not specified' if no reliable title is detected.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return "Target role not specified"

        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            return "Target role not specified"

        # Strategy 1: Check explicit role labels in the first 12 lines
        for line in lines[:12]:
            clean_l = re.sub(r"^[#*_\-\s]+", "", line).strip()
            for pat in EXPLICIT_ROLE_LABELS:
                m = re.match(pat, clean_l)
                if m:
                    extracted = _clean_and_format_title(m.group(1))
                    if extracted:
                        return extracted

        # Strategy 2: Check intro recruitment sentences in first 6 lines
        # e.g. "We are looking for a Senior Machine Learning Engineer to join our team"
        for line in lines[:6]:
            clean_l = re.sub(r"^[#*_\-\s]+", "", line).strip()
            m_intro = re.search(
                r"(?i)\b(?:we\s+are\s+hiring|we'?re\s+hiring|we\s+are\s+looking\s+for|we'?re\s+looking\s+for|is\s+seeking|are\s+seeking)\s+(?:a|an)?\s+([A-Za-z0-9\s/–—#-]+?\b(?:engineer|developer|analyst|architect|scientist|manager|specialist|consultant|designer|administrator|lead|programmer))\b",
                clean_l
            )
            if m_intro:
                extracted = _clean_and_format_title(m_intro.group(1))
                if extracted:
                    return extracted

        # Strategy 3: Check lines with pipe/hyphen/colon separators in first 8 lines
        # e.g. "Acme Corp | Machine Learning Engineer | Remote" or "Netflix — DevOps Engineer ($160k - $190k)"
        for line in lines[:8]:
            clean_l = re.sub(r"^[#*_\-\s]+", "", line).strip()
            # Strip parenthetical expressions (metadata, salaries, locations) before splitting to avoid broken fragments
            clean_no_paren = re.sub(r"\([^)]*\)", "", clean_l).strip()
            if any(sep in clean_no_paren for sep in [" | ", " - ", " – ", " — ", " : "]) or ":" in clean_no_paren:
                parts = re.split(r"\s*[|–—:]\s*|\s+-\s+", clean_no_paren)
                for part in parts:
                    extracted = _clean_and_format_title(part)
                    if extracted:
                        return extracted

        # Strategy 4: Standalone role title in top 5 lines
        # e.g. Line 1: "Senior Full Stack Developer"
        for line in lines[:5]:
            clean_l = re.sub(r"^[#*_\-\s]+", "", line).strip()
            if 3 <= len(clean_l) <= 70:
                extracted = _clean_and_format_title(clean_l)
                if extracted:
                    return extracted

        return "Target role not specified"

    def classify_requirement_tiers(self, job_text: str) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Extracts and partitions skills into 3 strictly mutually exclusive categories:
        1. required_skills
        2. preferred_skills
        3. unspecified_skills
        """
        # Split by newlines and logical clause/sentence boundaries
        raw_units = [u.strip() for u in re.split(r"\n|(?<=[.!?])\s+", job_text) if u.strip()]
        current_section = "unspecified"  # "required", "preferred", "general", or "unspecified"

        required_found: Set[str] = set()
        preferred_found: Set[str] = set()
        unspecified_found: Set[str] = set()

        for unit_str in raw_units:
            if not unit_str:
                continue

            lower_unit = unit_str.lower()

            # Check if this unit is a section heading
            clean_heading = re.sub(r"^[#*_\-\s]+", "", unit_str).strip()
            lower_clean_heading = clean_heading.lower()
            is_pref_header = any(re.search(p, lower_clean_heading) for p in PREFERRED_PATTERNS) and (len(clean_heading) < 70 or ":" in clean_heading)
            is_req_header = any(re.search(p, lower_clean_heading) for p in REQUIRED_PATTERNS) and (len(clean_heading) < 70 or ":" in clean_heading) and not is_pref_header
            is_general_header = bool(re.search(r"(?i)^(?:responsibilities|duties|what\s+you'?ll\s+do|about\s+us|benefits|overview|who\s+we\s+are|company\s+overview|job\s+summary|our\s+mission)\b", lower_clean_heading)) and len(clean_heading) < 70

            if is_req_header and not is_pref_header:
                current_section = "required"
                skills = self.skill_engine.extract_skills(unit_str)
                required_found.update(skills)
                continue
            elif is_pref_header and not is_req_header:
                current_section = "preferred"
                skills = self.skill_engine.extract_skills(unit_str)
                preferred_found.update(skills)
                continue
            elif is_general_header:
                current_section = "unspecified"
                continue

            # Extract skills in this unit
            line_skills = self.skill_engine.extract_skills(unit_str)
            if not line_skills:
                continue

            # Check local modifiers within the sentence/clause
            has_local_req = any(re.search(p, lower_unit) for p in REQUIRED_PATTERNS)
            has_local_pref = any(re.search(p, lower_unit) for p in PREFERRED_PATTERNS)

            if has_local_req and not has_local_pref:
                required_found.update(line_skills)
            elif has_local_pref and not has_local_req:
                preferred_found.update(line_skills)
            elif current_section == "required":
                required_found.update(line_skills)
            elif current_section == "preferred":
                preferred_found.update(line_skills)
            else:
                unspecified_found.update(line_skills)

        # Enforce strict mutual exclusivity across categories:
        preferred_found = preferred_found - required_found
        unspecified_found = unspecified_found - required_found - preferred_found

        return required_found, preferred_found, unspecified_found

    def extract_education_requirements(self, text: str) -> List[str]:
        """
        Extracts explicitly stated degree requirements.
        Rejects false extractions from productivity software (e.g. MS Word, MS Excel)
        and validates genuine degrees (B.Tech, B.E., B.Sc., BCA, MCA, M.Tech, Bachelor's, Master's, etc.).
        """
        edu_found = []
        for pat in EDUCATION_PATTERNS:
            matches = re.finditer(pat, text)
            for m in matches:
                matched_str = m.group(0).strip(".,; \n\t")
                # Remove trailing conjunctions/prepositions
                matched_str = re.sub(r"(?i)\s+(?:or|and|in|with|of)\s*$", "", matched_str).strip()
                if not matched_str or len(matched_str) < 3 or len(matched_str) > 85:
                    continue

                lower_str = matched_str.lower()
                # Check for productivity software mentions (e.g., MS Word, Office, etc.)
                if re.search(r"\bms\s*(?:word|excel|office|powerpoint|teams|access|project|visio)\b", lower_str):
                    continue

                # Check for excluded keywords
                words = set(re.findall(r"\b[a-z]{2,}\b", lower_str))
                if words.intersection(EXCLUDED_EDUCATION_KEYWORDS) - {"engineering", "science"}:
                    continue

                # Must contain at least one authentic academic indicator
                valid_academic = any(deg in lower_str for deg in [
                    "bachelor", "master", "degree", "ph.d", "phd", "doctorate",
                    "b.tech", "m.tech", "btech", "mtech", "b.e", "m.e", "b.sc", "m.sc",
                    "bca", "mca", "b.s", "m.s", "b.a", "m.a", "diploma", "associate"
                ])
                if not valid_academic:
                    continue

                if matched_str and matched_str not in edu_found:
                    edu_found.append(matched_str)

        return edu_found if edu_found else ["No explicit education requirement identified."]

    def extract_requirement_intelligence(
        self,
        job_text: str,
        req_skills: Set[str],
        pref_skills: Set[str],
        unspec_skills: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured intelligence for each extracted skill requirement:
        - Requirement name and canonical form
        - Exact supporting sentence from JD
        - Mandatory / Preferred tier
        - Requirement category
        - Role relevance
        - Related co-occurring requirements from the same clause
        """
        from src.mentor.mentor_engine import classify_mentor_category
        from src.common.evidence_registry import resolve_canonical_skill, CANONICAL_SKILL_ALIASES

        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", job_text) if s.strip()]
        all_skills = req_skills.union(pref_skills).union(unspec_skills)
        intel_list = []

        for skill in sorted(list(all_skills)):
            canonical = resolve_canonical_skill(skill)
            tier = "Required" if skill in req_skills else ("Preferred" if skill in pref_skills else "Unspecified")

            # Find exact supporting sentence with alias awareness
            supporting_sentence = "Exact JD evidence unavailable."
            related = []
            search_terms = {skill.lower(), canonical.lower()}
            for alias, canon in CANONICAL_SKILL_ALIASES.items():
                if canon.lower() == canonical.lower():
                    search_terms.add(alias.lower())

            for sent in sentences:
                clean_sent = sent.strip(" \t\n*-•")
                if any(re.search(rf"\b{re.escape(term)}\b", clean_sent.lower()) for term in search_terms):
                    supporting_sentence = clean_sent
                    # Co-occurring skills
                    for other in all_skills:
                        if other != skill:
                            other_canon = resolve_canonical_skill(other)
                            other_terms = {other.lower(), other_canon.lower()}
                            for a, c in CANONICAL_SKILL_ALIASES.items():
                                if c.lower() == other_canon.lower():
                                    other_terms.add(a.lower())
                            if any(re.search(rf"\b{re.escape(ot)}\b", clean_sent.lower()) for ot in other_terms):
                                related.append(other_canon)
                    break

            cat = classify_mentor_category(canonical)
            role_rel = f"Essential {cat.lower()} requirement for target position." if tier == "Required" else f"Preferred {cat.lower()} qualification providing competitive differentiation."

            # Calculate defensible extraction confidence score
            skill_low = skill.lower()
            canon_low = canonical.lower()
            if skill_low == canon_low:
                confidence = 1.0
            elif skill_low in CANONICAL_SKILL_ALIASES:
                confidence = 0.95
            else:
                confidence = 0.90

            intel_list.append({
                "name": skill,
                "canonical_name": canonical,
                "extracted_phrase": skill,
                "supporting_sentence": supporting_sentence,
                "source_text": supporting_sentence,
                "tier": tier,
                "priority": tier,
                "category": cat,
                "role_relevance": role_rel,
                "related_requirements": sorted(list(set(related))),
                "confidence": confidence
            })

        return intel_list

    def extract_responsibilities(self, job_text: str) -> List[str]:
        """Extracts candidate responsibilities and duties listed in job description."""
        resps = []
        lines = [l.strip() for l in job_text.splitlines() if l.strip()]
        in_resp_section = False

        resp_header_re = re.compile(
            r"(?i)^[#*_\-\s]*(?:key\s+|core\s+|essential\s+|job\s+|primary\s+)?(?:responsibilities|duties|tasks|what\s+you(?:'ll|\s+will)\s+do|role\s+overview)[#*_\-\s]*[:\-–—]?$"
        )
        other_header_re = re.compile(
            r"(?i)^[#*_\-\s]*(?:qualifications|requirements|skills|education|benefits|about\s+us|who\s+we\s+are|perks|how\s+to\s+apply)[#*_\-\s]*[:\-–—]?$"
        )

        for line in lines:
            if resp_header_re.match(line):
                in_resp_section = True
                continue
            elif in_resp_section and other_header_re.match(line):
                in_resp_section = False
                break

            if in_resp_section:
                clean_l = re.sub(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—\d+\.]\s*", "", line).strip()
                if len(clean_l) >= 10:
                    resps.append(clean_l)

        return resps

    def extract_qualifications(self, job_text: str) -> List[str]:
        """Extracts candidate qualifications and prerequisites listed in job description."""
        quals = []
        lines = [l.strip() for l in job_text.splitlines() if l.strip()]
        in_qual_section = False

        qual_header_re = re.compile(
            r"(?i)^[#*_\-\s]*(?:minimum\s+|basic\s+|key\s+|preferred\s+|required\s+)?(?:qualifications|requirements|prerequisites|what\s+we(?:'re|\s+are)\s+looking\s+for|what\s+you(?:'ll|\s+will)\s+need)[#*_\-\s]*[:\-–—]?$"
        )
        other_header_re = re.compile(
            r"(?i)^[#*_\-\s]*(?:responsibilities|duties|benefits|about\s+us|who\s+we\s+are|perks|how\s+to\s+apply)[#*_\-\s]*[:\-–—]?$"
        )

        for line in lines:
            if qual_header_re.match(line):
                in_qual_section = True
                continue
            elif in_qual_section and other_header_re.match(line):
                in_qual_section = False
                break

            if in_qual_section:
                clean_l = re.sub(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—\d+\.]\s*", "", line).strip()
                if len(clean_l) >= 10:
                    quals.append(clean_l)

        return quals

    def extract_tools_and_technologies(self, all_skills: Set[str]) -> List[str]:
        """Extracts concrete tools, platforms, databases, and technologies from extracted skills."""
        tools = []
        target_categories = {
            "Cloud and infrastructure",
            "Developer tools",
            "Databases",
            "Frameworks and libraries",
            "Productivity software"
        }
        for s in all_skills:
            cat = categorize_competency(s)
            if cat in target_categories:
                tools.append(s)
        return sorted(tools)

    def extract_structured_experience_requirements(self, job_text: str, exp_years: float) -> Dict[str, Any]:
        """Extracts structured experience requirements with context sentences."""
        from src.preprocessing.text_cleaner import EXPERIENCE_PATTERN
        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", job_text) if s.strip()]
        exp_sentence = None
        for sent in sentences:
            if EXPERIENCE_PATTERN.search(sent) or re.search(r"\b(?:years|yrs)\s+(?:of\s+)?(?:experience|exp)\b", sent, re.I):
                exp_sentence = sent
                break

        return {
            "min_years": exp_years if exp_years > 0.0 else None,
            "max_years": None,
            "context_sentence": exp_sentence or "No explicit experience duration requirement stated in job description.",
            "is_explicit": exp_years > 0.0
        }

    def analyze(self, job_text: Optional[str]) -> Dict:
        """
        Executes complete deterministic analysis on job description.
        """
        if not job_text or not isinstance(job_text, str) or not job_text.strip():
            return {
                "job_title": "Target role not specified",
                "required_skills": [],
                "preferred_skills": [],
                "unspecified_skills": [],
                "all_skills": [],
                "responsibilities": [],
                "qualifications": [],
                "tools_and_technologies": [],
                "requirement_intelligence": [],
                "required_years_exp": None,
                "has_explicit_exp": False,
                "experience_requirements": {
                    "min_years": None,
                    "max_years": None,
                    "context_sentence": "No explicit experience duration requirement stated in job description.",
                    "is_explicit": False
                },
                "education_requirements": [],
                "total_skills_count": 0,
                "status": "empty_input"
            }

        title = self.extract_job_title(job_text)
        req_skills, pref_skills, unspec_skills = self.classify_requirement_tiers(job_text)
        all_skills = req_skills.union(pref_skills).union(unspec_skills)

        # Explicit experience years and structured experience requirements
        exp_years = extract_explicit_experience_years(job_text)
        has_explicit_exp = exp_years > 0.0
        exp_req_dict = self.extract_structured_experience_requirements(job_text, exp_years)

        # Education requirements
        education = self.extract_education_requirements(job_text)

        # Requirement Intelligence
        req_intel = self.extract_requirement_intelligence(job_text, req_skills, pref_skills, unspec_skills)

        # Alternative Requirement Groups (e.g. "Power BI or Tableau", "Java or Python")
        alt_groups = self.detect_alternative_skill_groups(job_text, all_skills)

        # Responsibilities, Qualifications, and Tools
        responsibilities = self.extract_responsibilities(job_text)
        qualifications = self.extract_qualifications(job_text)
        tools_and_tech = self.extract_tools_and_technologies(all_skills)

        return {
            "job_title": title,
            "required_skills": sorted(list(req_skills)),
            "preferred_skills": sorted(list(pref_skills)),
            "unspecified_skills": sorted(list(unspec_skills)),
            "all_skills": sorted(list(all_skills)),
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "tools_and_technologies": tools_and_tech,
            "alternative_groups": alt_groups,
            "requirement_intelligence": req_intel,
            "required_years_exp": exp_years if has_explicit_exp else None,
            "has_explicit_exp": has_explicit_exp,
            "experience_requirements": exp_req_dict,
            "education_requirements": education,
            "total_skills_count": len(all_skills),
            "status": "success"
        }

    def detect_alternative_skill_groups(self, job_text: str, all_skills: Set[str]) -> List[Dict[str, Any]]:
        """
        Detects disjunctive skill requirements (e.g. 'Power BI or Tableau', 'Java or Python', 'AWS or Azure or GCP').
        Returns list of alternative requirement groups so matching engine does not penalize
        candidates who satisfy one of the accepted alternatives.
        """
        from src.common.evidence_registry import resolve_canonical_skill, CANONICAL_SKILL_ALIASES

        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", job_text) if s.strip()]
        groups = []

        for sent in sentences:
            lower_sent = sent.lower()
            if " or " not in lower_sent and " / " not in lower_sent and "either " not in lower_sent:
                continue

            # Identify skills present in this sentence
            skills_in_sent = []
            for s in all_skills:
                canonical = resolve_canonical_skill(s)
                terms = {s.lower(), canonical.lower()}
                for a, c in CANONICAL_SKILL_ALIASES.items():
                    if c.lower() == canonical.lower():
                        terms.add(a.lower())
                if any(re.search(rf"\b{re.escape(t)}\b", lower_sent) for t in terms):
                    skills_in_sent.append(s)

            if len(skills_in_sent) < 2:
                continue

            # Check if skills are joined by 'or' / '/'
            linked_skills = []
            for i, s1 in enumerate(skills_in_sent):
                for s2 in skills_in_sent[i+1:]:
                    s1_terms = [s1.lower(), resolve_canonical_skill(s1).lower()]
                    s2_terms = [s2.lower(), resolve_canonical_skill(s2).lower()]
                    is_linked = False
                    for t1 in s1_terms:
                        for t2 in s2_terms:
                            pat1 = rf"\b{re.escape(t1)}\b.*?\b(?:or|/)\b.*?\b{re.escape(t2)}\b"
                            pat2 = rf"\b{re.escape(t2)}\b.*?\b(?:or|/)\b.*?\b{re.escape(t1)}\b"
                            if re.search(pat1, lower_sent) or re.search(pat2, lower_sent):
                                is_linked = True
                                break
                        if is_linked:
                            break
                    if is_linked:
                        if s1 not in linked_skills:
                            linked_skills.append(s1)
                        if s2 not in linked_skills:
                            linked_skills.append(s2)

            if len(linked_skills) >= 2:
                has_req = any(re.search(p, lower_sent) for p in REQUIRED_PATTERNS)
                tier = "Required" if has_req else "Preferred"
                groups.append({
                    "skills": sorted(linked_skills),
                    "canonical_skills": sorted(list({resolve_canonical_skill(s) for s in linked_skills})),
                    "tier": tier,
                    "sentence": sent
                })

        return groups

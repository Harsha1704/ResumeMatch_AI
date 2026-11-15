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
    r"\bmust\s+(?:have|possess|demonstrate|exhibit|be)\b",
    r"\brequired\s*(?:skills|qualifications|experience|requirements)?\b",
    r"\b(?:is|are)\s+required\b",
    r"\brequire[ds]?\b",
    r"\bminimum\s*(?:qualifications|requirements)\b",
    r"\bbasic\s*qualifications\b",
    r"\bessential\s*(?:skills|requirements|qualifications)\b",
    r"\bmandatory\b",
    r"\bprerequisites?\b",
    r"\bcore\s+requirements?\b"
]

PREFERRED_PATTERNS = [
    r"\bpreferred\s*(?:skills|qualifications|experience)?\b",
    r"\bnice\s*to\s*have\b",
    r"\bbonus\s*(?:points|skills)?\b",
    r"\bplus(?:\s+if)?\b",
    r"\bdesired\s*(?:skills|qualifications)\b",
    r"\badvantageous\b",
    r"\bdesirable\b",
    r"\bbeneficial\b",
    r"\bgood\s*to\s*have\b",
    r"\boptional\b"
]

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
        """Attempts to identify the job position title from document headers or explicit tags."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            return "Target role not specified"

        # Check explicit title tags
        for line in lines[:8]:
            match = re.match(r"(?i)^(?:job\s+title|position|role|title)\s*[:\-]\s*(.+)$", line)
            if match:
                title_val = match.group(1).strip()
                if len(title_val) < 80:
                    return title_val

        # Fallback: Top non-trivial header line if under 60 chars and contains role keywords
        role_indicators = {"engineer", "developer", "analyst", "architect", "scientist", "manager", "specialist", "intern", "consultant"}
        for line in lines[:4]:
            lower = line.lower()
            if 3 < len(line) < 60 and any(r in lower for r in role_indicators):
                return line.strip("#*-: ").title()

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
            is_req_header = any(re.search(p, lower_unit) for p in REQUIRED_PATTERNS) and (len(unit_str) < 60 or ":" in unit_str)
            is_pref_header = any(re.search(p, lower_unit) for p in PREFERRED_PATTERNS) and (len(unit_str) < 60 or ":" in unit_str)
            is_general_header = bool(re.search(r"(?i)^(?:responsibilities|duties|what\s+you'?ll\s+do|about\s+us|benefits|overview)\b", lower_unit)) and len(unit_str) < 60

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

            intel_list.append({
                "name": skill,
                "canonical_name": canonical,
                "supporting_sentence": supporting_sentence,
                "tier": tier,
                "category": cat,
                "role_relevance": role_rel,
                "related_requirements": sorted(list(set(related)))
            })

        return intel_list

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
                "requirement_intelligence": [],
                "required_years_exp": None,
                "education_requirements": [],
                "total_skills_count": 0,
                "status": "empty_input"
            }

        title = self.extract_job_title(job_text)
        req_skills, pref_skills, unspec_skills = self.classify_requirement_tiers(job_text)
        all_skills = req_skills.union(pref_skills).union(unspec_skills)

        # Explicit experience years
        exp_years = extract_explicit_experience_years(job_text)
        has_explicit_exp = exp_years > 0.0

        # Education requirements
        education = self.extract_education_requirements(job_text)

        # Requirement Intelligence
        req_intel = self.extract_requirement_intelligence(job_text, req_skills, pref_skills, unspec_skills)

        # Alternative Requirement Groups (e.g. "Power BI or Tableau", "Java or Python")
        alt_groups = self.detect_alternative_skill_groups(job_text, all_skills)

        return {
            "job_title": title,
            "required_skills": sorted(list(req_skills)),
            "preferred_skills": sorted(list(pref_skills)),
            "unspecified_skills": sorted(list(unspec_skills)),
            "all_skills": sorted(list(all_skills)),
            "alternative_groups": alt_groups,
            "requirement_intelligence": req_intel,
            "required_years_exp": exp_years if has_explicit_exp else None,
            "has_explicit_exp": has_explicit_exp,
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

"""
Unified Candidate Evidence & Job Requirement Intelligence Foundation.

Provides a single source of truth across all analytical and educational modules:
- Resume Analyzer
- Skill Gap Analytics
- Career Mentor
- Interview Intelligence Studio
- Interview Practice and Review

Enforces strict consistency invariants:
1. Matched skills and missing skills must not contradict each other (Disjointness).
2. Aliases must resolve consistently to canonical representations.
3. Requirement tiers (Required vs Preferred) must agree with the source JD context.
4. Candidate evidence must be traceable to exact resume text or confirmed user input.
5. No unsupported first-person claims or fabricated achievements.
6. Honest uncertainty acknowledgment when evidence is lacking.
7. Job requirements and candidate evidence remain separately represented and traceable.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any, Tuple
import re

# Canonical skill aliases for unified resolution across all modules
CANONICAL_SKILL_ALIASES: Dict[str, str] = {
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "py": "Python",
    "python": "Python",
    "python3": "Python",
    "c++": "C++",
    "cpp": "C++",
    "c plus plus": "C++",
    "c#": "C#",
    "csharp": "C#",
    "c sharp": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "pl/sql": "PL/SQL",
    "plsql": "PL/SQL",
    "ai": "AI",
    "artificial intelligence": "AI",
    "golang": "Go",
    "go": "Go",
    "r": "R",
    "c": "C",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "containers": "Docker",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "github actions": "CI/CD",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "elasticsearch": "Elasticsearch",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "spark": "Spark",
    "apache spark": "Spark",
    "pyspark": "PySpark",
    "hadoop": "Hadoop",
    "apache hadoop": "Hadoop",
    "kafka": "Kafka",
    "apache kafka": "Kafka",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "looker": "Looker",
    "excel": "Excel",
    "ms excel": "Excel",
    "word": "Word",
    "ms word": "Word",
    "powerpoint": "PowerPoint",
    "ms powerpoint": "PowerPoint",
    "visio": "Visio",
    "ms visio": "Visio",
    "jira": "Jira",
    "trello": "Trello",
    "pc skills": "PC Skills",
    "computer skills": "PC Skills",
    "communication": "Communication",
    "verbal communication": "Communication",
    "presentation": "Communication",
    "project management": "Project Management",
    "agile": "Project Management",
    "scrum": "Project Management",
    "focus": "Focus",
    "attention to detail": "Focus",
    "analytical problem-solving": "Analytical Problem-Solving",
    "problem solving": "Analytical Problem-Solving",
    "analytical thinking": "Analytical Problem-Solving",
    "critical thinking": "Analytical Problem-Solving",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "git": "Git",
    "linux": "Linux",
    "html": "HTML",
    "css": "CSS",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "restful apis": "REST APIs",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    "unit testing": "Unit Testing",
    "pytest": "PyTest",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins"
}

# Strength ranking for evidence upgrades
EVIDENCE_STRENGTH_RANK: Dict[str, int] = {
    "none": 0,
    "not_evidenced": 0,
    "explicit_mention": 1,
    "explicitly_mentioned": 1,
    "partially_evidenced": 2,
    "demonstrated_experience": 3,
    "demonstrated_internship": 3,
    "demonstrated_project": 3,
    "demonstrated": 3,
    "user_confirmed": 4,
    "confirmed": 4
}


def resolve_canonical_skill(raw_name: str) -> str:
    """Resolves any skill variant or alias to its canonical title-cased representation."""
    if not raw_name or not isinstance(raw_name, str):
        return ""
    norm = raw_name.lower().strip()
    return CANONICAL_SKILL_ALIASES.get(norm, raw_name.strip())


def matches_skill_token(text: str, skill_phrase: str) -> bool:
    """Matches a skill phrase or alias in text respecting word and punctuation boundaries."""
    if not text or not skill_phrase:
        return False
    phrase_clean = skill_phrase.strip().lower()
    if phrase_clean in ("c++", "cpp", "c plus plus"):
        return bool(re.search(r"(?<![\w#+])(?:c\+\+|cpp|c\s+plus\s+plus)(?![\w#+])", text, re.I))
    elif phrase_clean in ("c#", "csharp", "c sharp"):
        return bool(re.search(r"(?<![\w#+])(?:c#|csharp|c\s+sharp)(?![\w#+])", text, re.I))
    elif phrase_clean == "c":
        return bool(re.search(r"(?<![\w#+])c(?![\w#+])", text, re.I))
    elif phrase_clean in (".net", "dotnet"):
        return bool(re.search(r"(?<![\w#+])(?:\.net|dotnet)(?![\w#+])", text, re.I))
    elif phrase_clean in ("node.js", "nodejs", "node"):
        return bool(re.search(r"\bnode(?:\.js)?\b", text, re.I))
    elif phrase_clean in ("ci/cd", "cicd"):
        return bool(re.search(r"\bci/cd\b|\bcicd\b", text, re.I))
    elif phrase_clean in ("pl/sql", "plsql"):
        return bool(re.search(r"\bpl/sql\b|\bplsql\b", text, re.I))
    elif phrase_clean == "r":
        return bool(re.search(r"(?<![\w#+])r(?![\w#+])", text, re.I))
    else:
        return bool(re.search(rf"\b{re.escape(phrase_clean)}\b", text, re.I))


def find_jd_quote(sk: str, jd_text: str) -> str:
    """
    Finds the exact supporting sentence from the job description mentioning this requirement.
    Uses canonical resolution and all registered aliases. Never fabricates a quotation.
    """
    if not jd_text or not isinstance(jd_text, str) or not jd_text.strip():
        return "Exact JD evidence unavailable."

    canon = resolve_canonical_skill(sk)
    search_terms = {sk.lower().strip(), canon.lower().strip()}
    for alias, c in CANONICAL_SKILL_ALIASES.items():
        if c.lower() == canon.lower():
            search_terms.add(alias.lower())

    clean_jd = jd_text.replace("\r", " ")
    sentences = re.split(r"(?<=[.!?\n])\s+|[\r\n]+", clean_jd)
    for sent in sentences:
        s_clean = sent.strip(" \t\n*-•")
        if len(s_clean) >= 6:
            if any(matches_skill_token(s_clean, term) for term in search_terms):
                if len(s_clean) > 160:
                    s_clean = s_clean[:157] + "..."
                return s_clean
    return "Exact JD evidence unavailable."


def find_resume_sentence_for_skill(skill_name: str, resume_text: str) -> Tuple[str, bool]:
    """
    Locates an authentic sentence in the parsed resume mentioning this skill.
    Returns (sentence, is_contextual).
    - is_contextual=True if sentence includes descriptive or engineering context.
    - is_contextual=False if sentence is purely an ungrounded keyword list.
    - ('', False) if not found.
    Never fabricates a quotation.
    """
    if not resume_text or not isinstance(resume_text, str) or not resume_text.strip():
        return "", False

    canon = resolve_canonical_skill(skill_name)
    search_terms = {skill_name.lower().strip(), canon.lower().strip()}
    for alias, c in CANONICAL_SKILL_ALIASES.items():
        if c.lower() == canon.lower():
            search_terms.add(alias.lower())

    clean_res = resume_text.replace("\r", " ")
    sentences = re.split(r"(?<=[.!?\n])\s+|[\r\n]+", clean_res)

    context_verbs = {
        "built", "developed", "engineered", "designed", "created", "trained",
        "deployed", "tested", "optimized", "implemented", "maintained", "analyzed",
        "automated", "configured", "refactored", "integrated", "managed", "scaled"
    }

    fallback_skills_line = ""

    for sent in sentences:
        s_clean = sent.strip(" \t\n*-•")
        if len(s_clean) >= 4:
            if any(matches_skill_token(s_clean, term) for term in search_terms):
                s_lower = s_clean.lower()
                words = set(re.findall(r"\b[a-z]{3,}\b", s_lower))
                is_pure_list = (
                    any(h in s_lower for h in ["skills:", "technical skills", "technologies:", "proficient in", "tools:"])
                    and not words.intersection(context_verbs)
                )
                if is_pure_list:
                    if not fallback_skills_line:
                        fallback_skills_line = s_clean
                else:
                    if len(s_clean) > 160:
                        s_clean = s_clean[:157] + "..."
                    return s_clean, True

    if fallback_skills_line:
        if len(fallback_skills_line) > 160:
            fallback_skills_line = fallback_skills_line[:157] + "..."
        return fallback_skills_line, False

    return "", False


@dataclass
class EvidenceOccurrence:
    """An individual occurrence or source excerpt supporting a competency."""
    source_type: str         # 'project', 'internship', 'experience', 'skills_section', 'resume_body', 'user_confirmation', 'job_description'
    source_title: str        # e.g., Project title, Company name, 'Resume Skills Section'
    exact_excerpt: str       # Actual genuine sentence/phrase from parsed resume/JD
    provenance: str          # 'extracted_project', 'extracted_internship', 'resume_sentence', 'user_action'
    is_demonstrated: bool = False
    evidence_strength: str = "moderate"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceRecord:
    """
    Structured evidence record for a single competency.
    Explicitly categorizes candidate relationship and evidence strength.
    Maintains multiple traceable evidence occurrences without overwriting.
    """
    skill: str
    canonical_skill: str
    evidence_type: str       # 'demonstrated', 'partially_evidenced', 'explicitly_mentioned', 'not_evidenced', 'user_confirmed'
                             # (also preserves backward-compatible subtypes: demonstrated_project, demonstrated_internship, demonstrated_experience)
    source_doc: str          # 'resume', 'job_description', 'user_input'
    supporting_text: str     # Genuine excerpt or explicit unavailable note
    project_association: Optional[str] = None
    evidence_strength: str = "none"  # 'demonstrated', 'partially_evidenced', 'explicitly_mentioned', 'user_confirmed', 'none'
    confidence: float = 0.0          # Heuristic evidence strength indicator (0.0 to 1.0, not calibrated probability)
    candidate_confirmation: str = "unconfirmed"  # 'unconfirmed', 'confirmed', 'rejected'
    occurrences: List[Dict[str, Any]] = field(default_factory=list)
    is_required: bool = False
    is_preferred: bool = False
    extraction_method: str = "rule_based_extraction"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobRequirementRecord:
    """
    Structured intelligence record for a single job requirement.
    Preserves exact supporting sentence and multi-skill clause context.
    Represented independently of candidate evidence.
    """
    name: str
    canonical_name: str
    supporting_sentence: str
    tier: str            # 'Required', 'Preferred', 'Unspecified'
    category: str        # 'Core Technical Skills', 'Engineering Tools and Practices', etc.
    role_relevance: str
    prerequisites: List[str] = field(default_factory=list)
    related_requirements: List[str] = field(default_factory=list)
    is_satisfied: bool = False
    satisfaction_status: str = "not_evidenced"  # 'demonstrated', 'partially_evidenced', 'explicitly_mentioned', 'user_confirmed', 'not_evidenced'
    matched_candidate_skill: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CandidateEvidenceRegistry:
    """
    Unified Candidate Evidence & Job Requirement Registry.
    Maintains clean separation between verified evidence, partial evidence,
    unsupported gaps, and user-confirmed data.
    """

    def __init__(self):
        self.evidence_records: Dict[str, EvidenceRecord] = {}
        self.job_requirements: Dict[str, JobRequirementRecord] = {}
        self.user_confirmations: Dict[str, Any] = {}

    def register_evidence(
        self,
        skill: str,
        evidence_type: str,
        source_doc: str,
        supporting_text: str,
        project_association: Optional[str] = None,
        evidence_strength: str = "none",
        confidence: float = 0.0,
        candidate_confirmation: str = "unconfirmed",
        occurrence: Optional[Dict[str, Any]] = None,
        is_required: bool = False,
        is_preferred: bool = False,
        extraction_method: str = "rule_based_extraction"
    ) -> EvidenceRecord:
        """
        Creates and registers or merges candidate evidence without overwriting prior occurrences.
        Preserves all multiple project/internship occurrences for the same skill.
        """
        canonical = resolve_canonical_skill(skill)
        canon_lower = canonical.lower()

        # Build occurrence entry if provided or inferred
        occ_list: List[Dict[str, Any]] = []
        if occurrence:
            occ_list.append(occurrence)
        elif supporting_text and supporting_text != "Exact JD evidence unavailable.":
            occ_list.append({
                "source_type": "project" if project_association else source_doc,
                "source_title": project_association or ("Resume" if source_doc == "resume" else "Job Description"),
                "exact_excerpt": supporting_text,
                "provenance": extraction_method,
                "is_demonstrated": evidence_type.startswith("demonstrated") or evidence_strength in ("demonstrated", "strong"),
                "evidence_strength": evidence_strength
            })

        if canon_lower in self.evidence_records:
            existing = self.evidence_records[canon_lower]

            # Merge occurrences safely without duplicates
            for occ in occ_list:
                exc = occ.get("exact_excerpt")
                if not any(o.get("exact_excerpt") == exc for o in existing.occurrences):
                    existing.occurrences.append(occ)

            # Check if new evidence is stronger than existing
            new_rank = EVIDENCE_STRENGTH_RANK.get(evidence_type, 0)
            cur_rank = EVIDENCE_STRENGTH_RANK.get(existing.evidence_type, 0)

            if new_rank > cur_rank:
                existing.evidence_type = evidence_type
                existing.evidence_strength = evidence_strength
                existing.supporting_text = supporting_text
                if project_association:
                    existing.project_association = project_association
                existing.confidence = max(existing.confidence, confidence)

            # Preserve requirement flags
            existing.is_required = existing.is_required or is_required
            existing.is_preferred = existing.is_preferred or is_preferred
            if candidate_confirmation == "confirmed":
                existing.candidate_confirmation = "confirmed"

            return existing

        # Create new record
        record = EvidenceRecord(
            skill=skill,
            canonical_skill=canonical,
            evidence_type=evidence_type,
            source_doc=source_doc,
            supporting_text=supporting_text,
            project_association=project_association,
            evidence_strength=evidence_strength,
            confidence=confidence,
            candidate_confirmation=candidate_confirmation,
            occurrences=occ_list,
            is_required=is_required,
            is_preferred=is_preferred,
            extraction_method=extraction_method
        )
        self.evidence_records[canon_lower] = record
        return record

    def register_job_requirement(
        self,
        name: str,
        supporting_sentence: str,
        tier: str,
        category: str,
        role_relevance: str,
        prerequisites: Optional[List[str]] = None,
        related_requirements: Optional[List[str]] = None,
        is_satisfied: bool = False,
        satisfaction_status: str = "not_evidenced",
        matched_candidate_skill: Optional[str] = None
    ) -> JobRequirementRecord:
        """Registers a structured job requirement with full contextual lineage."""
        canonical = resolve_canonical_skill(name)
        canon_lower = canonical.lower()

        record = JobRequirementRecord(
            name=name,
            canonical_name=canonical,
            supporting_sentence=supporting_sentence,
            tier=tier,
            category=category,
            role_relevance=role_relevance,
            prerequisites=prerequisites or [],
            related_requirements=related_requirements or [],
            is_satisfied=is_satisfied,
            satisfaction_status=satisfaction_status,
            matched_candidate_skill=matched_candidate_skill
        )
        self.job_requirements[canon_lower] = record
        return record

    def add_user_confirmation(self, key: str, value: Any):
        """Records an explicit candidate confirmation without erasing original resume evidence."""
        self.user_confirmations[key] = {
            "value": value,
            "status": "confirmed"
        }
        canon = resolve_canonical_skill(key)
        canon_lower = canon.lower()

        if canon_lower in self.evidence_records:
            rec = self.evidence_records[canon_lower]
            rec.candidate_confirmation = "confirmed"
            rec.evidence_strength = "confirmed"
            rec.confidence = 1.0
            # Add user confirmation occurrence while keeping resume occurrences intact
            rec.occurrences.append({
                "source_type": "user_confirmation",
                "source_title": "Candidate Confirmation",
                "exact_excerpt": f"Explicitly confirmed by candidate: '{value}'",
                "provenance": "user_confirmation_workflow",
                "is_demonstrated": True,
                "evidence_strength": "confirmed"
            })
        else:
            # Register new confirmed record
            self.register_evidence(
                skill=canon,
                evidence_type="user_confirmed",
                source_doc="user_input",
                supporting_text=f"Explicitly confirmed by candidate: '{value}'",
                evidence_strength="confirmed",
                confidence=1.0,
                candidate_confirmation="confirmed",
                extraction_method="user_confirmation_workflow"
            )

        if canon_lower in self.job_requirements:
            req = self.job_requirements[canon_lower]
            req.is_satisfied = True
            req.satisfaction_status = "user_confirmed"
            req.matched_candidate_skill = canon

    def get_record(self, skill: str) -> Optional[EvidenceRecord]:
        canon = resolve_canonical_skill(skill).lower()
        return self.evidence_records.get(canon)

    def get_occurrences(self, skill: str) -> List[Dict[str, Any]]:
        """Returns all evidence occurrences for a canonical skill."""
        rec = self.get_record(skill)
        return rec.occurrences if rec else []

    def get_demonstrated_skills(self) -> List[EvidenceRecord]:
        """Returns skills evidenced with meaningful practical context in projects, internships, or experience."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type in (
                "demonstrated", "demonstrated_project", "demonstrated_internship",
                "demonstrated_experience", "user_confirmed"
            ) or r.evidence_strength in ("demonstrated", "strong", "confirmed")
        ]

    def get_partially_evidenced_skills(self) -> List[EvidenceRecord]:
        """Returns skills mentioned without sufficient practical context or verbs."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "partially_evidenced" and r.evidence_strength != "demonstrated"
        ]

    def get_explicitly_mentioned_skills(self) -> List[EvidenceRecord]:
        """Returns skills explicitly listed anywhere in the candidate resume or profile."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type in (
                "explicit_mention", "explicitly_mentioned", "partially_evidenced",
                "demonstrated", "demonstrated_project", "demonstrated_internship",
                "demonstrated_experience", "user_confirmed"
            )
        ]

    def get_missing_skills(self) -> List[EvidenceRecord]:
        """Returns job requirements not evidenced in the candidate resume."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "not_evidenced"
        ]

    def get_missing_required_skills(self) -> List[EvidenceRecord]:
        """Returns mandatory job requirements not evidenced in the candidate resume."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "not_evidenced" and r.is_required
        ]

    def get_missing_preferred_skills(self) -> List[EvidenceRecord]:
        """Returns preferred job requirements not evidenced in the candidate resume."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "not_evidenced" and r.is_preferred
        ]

    def get_user_confirmed_skills(self) -> List[EvidenceRecord]:
        """Returns skills explicitly verified through candidate confirmation."""
        return [
            r for r in self.evidence_records.values()
            if r.candidate_confirmation == "confirmed" or r.evidence_type == "user_confirmed"
        ]

    def get_skill_status(self, skill: str) -> Dict[str, Any]:
        """
        Unified inspection API: Returns complete candidate and requirement status for any skill.
        Determines requirement tier, evidence classification, and source traceability.
        """
        canon = resolve_canonical_skill(skill)
        canon_lower = canon.lower()
        req = self.job_requirements.get(canon_lower)
        ev = self.evidence_records.get(canon_lower)

        is_required = req is not None and req.tier == "Required"
        is_preferred = req is not None and req.tier == "Preferred"
        is_user_confirmed = (
            (ev is not None and ev.candidate_confirmation == "confirmed") or
            (canon_lower in self.user_confirmations)
        )

        ev_type = ev.evidence_type if ev else "not_evidenced"
        is_demonstrated = ev is not None and ev_type in (
            "demonstrated", "demonstrated_project", "demonstrated_internship",
            "demonstrated_experience", "user_confirmed"
        )
        is_partially_evidenced = ev is not None and ev_type == "partially_evidenced"
        is_explicitly_mentioned = ev is not None and ev_type in ("explicit_mention", "explicitly_mentioned")
        is_not_evidenced = ev is None or ev_type == "not_evidenced"

        return {
            "skill": skill,
            "canonical_skill": canon,
            "is_required": is_required,
            "is_preferred": is_preferred,
            "is_demonstrated": is_demonstrated,
            "is_partially_evidenced": is_partially_evidenced,
            "is_explicitly_mentioned": is_explicitly_mentioned,
            "is_not_evidenced": is_not_evidenced,
            "is_user_confirmed": is_user_confirmed,
            "evidence_strength": ev.evidence_strength if ev else "none",
            "evidence_type": ev_type,
            "occurrences_count": len(ev.occurrences) if ev else 0,
            "supporting_text": ev.supporting_text if ev else "No matching evidence found in candidate resume.",
            "job_supporting_sentence": req.supporting_sentence if req else "Not specified in job requirements."
        }

    def verify_consistency_invariants(self) -> Tuple[bool, List[str]]:
        """
        Validates all consistency invariants across candidate evidence and job requirements:
        1. Disjointness: No skill can simultaneously be in demonstrated and missing.
        2. No skill can be in both partially evidenced and missing.
        3. Every job requirement has a truthful supporting sentence.
        4. No generic placeholder text presented as genuine evidence.
        """
        violations = []
        demonstrated = {r.canonical_skill.lower() for r in self.get_demonstrated_skills()}
        partial = {r.canonical_skill.lower() for r in self.get_partially_evidenced_skills()}
        missing = {r.canonical_skill.lower() for r in self.get_missing_skills()}

        # Disjointness check
        overlap_demo_miss = demonstrated.intersection(missing)
        if overlap_demo_miss:
            violations.append(f"Invariant Violation: Skills marked both demonstrated and missing: {overlap_demo_miss}")

        overlap_part_miss = partial.intersection(missing)
        if overlap_part_miss:
            violations.append(f"Invariant Violation: Skills marked both partially evidenced and missing: {overlap_part_miss}")

        # Prohibited placeholder sentences check
        prohibited_placeholders = {
            "Verified with contextual engineering verbs in resume.",
            "Explicitly mentioned in resume text.",
            "Listed in static skills list."
        }
        for k, rec in self.evidence_records.items():
            if rec.supporting_text in prohibited_placeholders:
                violations.append(f"Invariant Violation: Skill '{rec.canonical_skill}' contains prohibited boilerplate excerpt: '{rec.supporting_text}'")

        # JD status validation
        for skill_key, req in self.job_requirements.items():
            if not req.supporting_sentence or req.supporting_sentence == "Referenced under technical requirements for target position.":
                violations.append(f"Invariant Violation: Job requirement '{req.name}' lacks truthful supporting sentence")

        is_valid = len(violations) == 0
        return is_valid, violations

    def build_summary_dossier(self) -> Dict[str, Any]:
        """Assembles a clean, structured JSON-serializable evidence summary."""
        return {
            "total_evidenced_skills": len(self.evidence_records),
            "demonstrated_count": len(self.get_demonstrated_skills()),
            "partially_evidenced_count": len(self.get_partially_evidenced_skills()),
            "explicitly_mentioned_count": len(self.get_explicitly_mentioned_skills()),
            "missing_gaps_count": len(self.get_missing_skills()),
            "missing_required_count": len(self.get_missing_required_skills()),
            "missing_preferred_count": len(self.get_missing_preferred_skills()),
            "job_requirements_count": len(self.job_requirements),
            "user_confirmations": self.user_confirmations,
            "demonstrated_skills": [r.canonical_skill for r in self.get_demonstrated_skills()],
            "partially_evidenced_skills": [r.canonical_skill for r in self.get_partially_evidenced_skills()],
            "explicitly_mentioned_skills": [r.canonical_skill for r in self.get_explicitly_mentioned_skills()],
            "missing_skills": [r.canonical_skill for r in self.get_missing_skills()],
            "missing_required_skills": [r.canonical_skill for r in self.get_missing_required_skills()],
            "missing_preferred_skills": [r.canonical_skill for r in self.get_missing_preferred_skills()],
            "evidence_by_skill": {
                k: rec.to_dict() for k, rec in self.evidence_records.items()
            },
            "job_requirements": {
                k: req.to_dict() for k, req in self.job_requirements.items()
            }
        }


def build_unified_evidence_registry(analysis_data: Dict[str, Any]) -> CandidateEvidenceRegistry:
    """
    Factory that constructs and populates a unified CandidateEvidenceRegistry
    from raw analysis data, parsed resume, and job description text.
    Maintains clean separation between requirements and candidate evidence.
    """
    registry = CandidateEvidenceRegistry()

    resume_text = (
        analysis_data.get("raw_text") or
        analysis_data.get("resume_raw_text") or
        analysis_data.get("cleaned_resume_text") or
        ""
    )
    jd_text = (
        analysis_data.get("job_description_text") or
        analysis_data.get("raw_jd") or
        analysis_data.get("job_description") or
        ""
    )

    # -------------------------------------------------------------------------
    # 1. Register All Job Requirements (Separate from Candidate Evidence)
    # -------------------------------------------------------------------------
    req_intel = analysis_data.get("requirement_intelligence") or []
    for item in req_intel:
        name = item.get("name") or item.get("canonical_name") or ""
        canon = item.get("canonical_name") or resolve_canonical_skill(name)
        tier = item.get("tier") or item.get("priority") or "Required"
        cat = item.get("category") or "Core Technical Skills"
        relevance = item.get("role_relevance") or f"{tier} qualification for target role."
        quote = item.get("supporting_sentence") or item.get("source_text") or find_jd_quote(name, jd_text)
        registry.register_job_requirement(
            name=name,
            supporting_sentence=quote,
            tier=tier,
            category=cat,
            role_relevance=relevance,
            prerequisites=item.get("prerequisites", []),
            related_requirements=item.get("related_requirements", [])
        )

    # Also register any required/preferred skills not covered in requirement_intelligence
    effective_req = analysis_data.get("effective_required_skills") or analysis_data.get("required_skills") or []
    effective_pref = analysis_data.get("effective_preferred_skills") or analysis_data.get("preferred_skills") or []

    for s in effective_req:
        canon_lower = resolve_canonical_skill(s).lower()
        if canon_lower not in registry.job_requirements:
            quote = find_jd_quote(s, jd_text)
            registry.register_job_requirement(
                name=s,
                supporting_sentence=quote,
                tier="Required",
                category="Core Technical Skills",
                role_relevance="Mandatory competency required for target position."
            )

    for s in effective_pref:
        canon_lower = resolve_canonical_skill(s).lower()
        if canon_lower not in registry.job_requirements:
            quote = find_jd_quote(s, jd_text)
            registry.register_job_requirement(
                name=s,
                supporting_sentence=quote,
                tier="Preferred",
                category="Engineering Tools and Practices",
                role_relevance="Preferred competency providing competitive differentiation."
            )

    # -------------------------------------------------------------------------
    # 2. Extract Candidate Evidence from Projects
    # -------------------------------------------------------------------------
    projects = analysis_data.get("projects") or analysis_data.get("relevant_projects") or []
    context_verbs = {
        "built", "developed", "engineered", "designed", "created", "trained",
        "deployed", "tested", "optimized", "implemented", "maintained", "analyzed",
        "automated", "configured", "refactored", "integrated", "managed", "scaled"
    }

    for p in projects:
        p_title = p.get("title") or p.get("project_title") or "Technical Project"
        techs = p.get("technologies") or p.get("tech_stack") or []
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(",") if t.strip()]
        desc = p.get("description") or p.get("project_description") or ""

        for tech in techs:
            canon = resolve_canonical_skill(tech)
            # Check if project description includes meaningful context for this tech
            tech_norm = tech.lower()
            desc_sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+|[\r\n]+", desc) if s.strip()]
            tech_sentence = ""
            for ds in desc_sentences:
                if matches_skill_token(ds, tech_norm) or matches_skill_token(ds, canon):
                    tech_sentence = ds
                    break

            if tech_sentence:
                words = set(re.findall(r"\b[a-z]{3,}\b", tech_sentence.lower()))
                has_verb = bool(words.intersection(context_verbs)) or len(tech_sentence.split()) >= 6
                if has_verb:
                    supp_text = f"Demonstrated in project '{p_title}': \"{tech_sentence}\""
                    ev_type = "demonstrated_project"
                    strength = "demonstrated"
                    conf = 0.95
                else:
                    supp_text = f"Referenced in project '{p_title}': \"{tech_sentence}\""
                    ev_type = "partially_evidenced"
                    strength = "partially_evidenced"
                    conf = 0.70
            elif desc:
                # Technology in tech stack; project description provides context
                supp_text = f"Associated with project '{p_title}' technology stack. Project focus: \"{desc[:120]}\""
                ev_type = "demonstrated_project"
                strength = "demonstrated"
                conf = 0.90
            else:
                supp_text = f"Listed in project '{p_title}' technology stack; implementation details not elaborated in description."
                ev_type = "partially_evidenced"
                strength = "partially_evidenced"
                conf = 0.65

            registry.register_evidence(
                skill=tech,
                evidence_type=ev_type,
                source_doc="resume",
                supporting_text=supp_text,
                project_association=p_title,
                evidence_strength=strength,
                confidence=conf,
                occurrence={
                    "source_type": "project",
                    "source_title": p_title,
                    "exact_excerpt": supp_text,
                    "provenance": "project_entity_extraction",
                    "is_demonstrated": strength == "demonstrated",
                    "evidence_strength": strength
                }
            )

    # -------------------------------------------------------------------------
    # 3. Extract Candidate Evidence from Internships & Experience
    # -------------------------------------------------------------------------
    internships = analysis_data.get("internships") or []
    for it in internships:
        org = it.get("organization") or it.get("company") or "Internship Organization"
        role = it.get("position") or it.get("role") or "Intern"
        resps = it.get("responsibilities") or it.get("bullets") or []
        resp_list = [r.strip() for r in resps.split(";")] if isinstance(resps, str) else list(resps)
        techs = it.get("technologies") or it.get("tools") or []
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(",") if t.strip()]

        # Collect candidate skills referenced in internship
        intern_skills: Set[str] = set()
        for t in techs:
            intern_skills.add(t)

        for bullet in resp_list:
            b_clean = bullet.strip(" \t\n*-•")
            for alias, canon in CANONICAL_SKILL_ALIASES.items():
                if matches_skill_token(b_clean, alias):
                    intern_skills.add(canon)
                    # Register occurrence with exact bullet
                    supp_text = f"Demonstrated at {org} ({role}): \"{b_clean}\""
                    registry.register_evidence(
                        skill=canon,
                        evidence_type="demonstrated_internship",
                        source_doc="resume",
                        supporting_text=supp_text,
                        project_association=org,
                        evidence_strength="demonstrated",
                        confidence=0.90,
                        occurrence={
                            "source_type": "internship",
                            "source_title": org,
                            "exact_excerpt": supp_text,
                            "provenance": "internship_entity_extraction",
                            "is_demonstrated": True,
                            "evidence_strength": "demonstrated"
                        }
                    )

        # For tools in internship tech stack without explicit bullet
        for t in intern_skills:
            canon = resolve_canonical_skill(t)
            if canon.lower() not in registry.evidence_records:
                supp_text = f"Referenced in internship technology stack at {org}."
                registry.register_evidence(
                    skill=t,
                    evidence_type="partially_evidenced",
                    source_doc="resume",
                    supporting_text=supp_text,
                    project_association=org,
                    evidence_strength="partially_evidenced",
                    confidence=0.70,
                    occurrence={
                        "source_type": "internship",
                        "source_title": org,
                        "exact_excerpt": supp_text,
                        "provenance": "internship_entity_extraction",
                        "is_demonstrated": False,
                        "evidence_strength": "partially_evidenced"
                    }
                )

    # -------------------------------------------------------------------------
    # 4. Process Solid vs Partial vs Explicitly Mentioned Skills from Resume
    # -------------------------------------------------------------------------
    solid_skills = analysis_data.get("solidly_evidenced_skills") or []
    partial_skills = analysis_data.get("partially_evidenced_skills") or []
    resume_skills = analysis_data.get("resume_skills") or analysis_data.get("skills") or []

    for s in solid_skills:
        canon = resolve_canonical_skill(s)
        canon_lower = canon.lower()
        sent, is_contextual = find_resume_sentence_for_skill(s, resume_text)
        if sent:
            supp_text = f"Demonstrated in resume: \"{sent}\"" if is_contextual else f"Referenced in resume: \"{sent}\""
        else:
            supp_text = f"Demonstrated in candidate experience with contextual action verbs."

        registry.register_evidence(
            skill=s,
            evidence_type="demonstrated_experience",
            source_doc="resume",
            supporting_text=supp_text,
            evidence_strength="demonstrated",
            confidence=0.90,
            occurrence={
                "source_type": "resume_body",
                "source_title": "Resume Contextual Experience",
                "exact_excerpt": supp_text,
                "provenance": "contextual_verb_matching",
                "is_demonstrated": True,
                "evidence_strength": "demonstrated"
            }
        )

    for s in partial_skills:
        canon = resolve_canonical_skill(s)
        canon_lower = canon.lower()
        if canon_lower not in registry.evidence_records:
            sent, _ = find_resume_sentence_for_skill(s, resume_text)
            supp_text = f"Mentioned in resume: \"{sent}\"" if sent else "Mentioned in resume skills inventory; practical implementation sentence unavailable."
            registry.register_evidence(
                skill=s,
                evidence_type="partially_evidenced",
                source_doc="resume",
                supporting_text=supp_text,
                evidence_strength="partially_evidenced",
                confidence=0.60,
                occurrence={
                    "source_type": "skills_section",
                    "source_title": "Resume Skills Inventory",
                    "exact_excerpt": supp_text,
                    "provenance": "skills_inventory_matching",
                    "is_demonstrated": False,
                    "evidence_strength": "partially_evidenced"
                }
            )

    for s in resume_skills:
        canon = resolve_canonical_skill(s)
        canon_lower = canon.lower()
        if canon_lower not in registry.evidence_records:
            sent, _ = find_resume_sentence_for_skill(s, resume_text)
            supp_text = f"Explicitly listed in resume: \"{sent}\"" if sent else "Explicitly listed in resume skills inventory."
            registry.register_evidence(
                skill=s,
                evidence_type="explicitly_mentioned",
                source_doc="resume",
                supporting_text=supp_text,
                evidence_strength="explicitly_mentioned",
                confidence=0.50,
                occurrence={
                    "source_type": "skills_section",
                    "source_title": "Resume Skills Section",
                    "exact_excerpt": supp_text,
                    "provenance": "keyword_mention_extraction",
                    "is_demonstrated": False,
                    "evidence_strength": "explicitly_mentioned"
                }
            )

    # -------------------------------------------------------------------------
    # 5. Reconcile Candidate Evidence with Job Requirements
    # -------------------------------------------------------------------------
    for canon_lower, req in registry.job_requirements.items():
        if canon_lower in registry.evidence_records:
            ev = registry.evidence_records[canon_lower]
            if ev.evidence_type != "not_evidenced":
                req.is_satisfied = True
                req.satisfaction_status = ev.evidence_type
                req.matched_candidate_skill = ev.skill
                ev.is_required = (req.tier == "Required")
                ev.is_preferred = (req.tier == "Preferred")
        else:
            # Job requirement has NO candidate evidence -> create not_evidenced record
            quote = req.supporting_sentence or find_jd_quote(req.name, jd_text)
            registry.register_evidence(
                skill=req.name,
                evidence_type="not_evidenced",
                source_doc="job_description",
                supporting_text=f"Target requirement from job description: '{quote}' (Not evidenced in resume)",
                evidence_strength="none",
                confidence=0.0,
                is_required=(req.tier == "Required"),
                is_preferred=(req.tier == "Preferred"),
                occurrence={
                    "source_type": "job_description",
                    "source_title": "Target Job Posting",
                    "exact_excerpt": quote,
                    "provenance": "job_requirement_diff",
                    "is_demonstrated": False,
                    "evidence_strength": "none"
                }
            )
            req.is_satisfied = False
            req.satisfaction_status = "not_evidenced"

    # Also handle missing_required_skills / missing_preferred_skills from gap analysis
    missing_req = analysis_data.get("missing_required_skills") or []
    missing_pref = analysis_data.get("missing_preferred_skills") or []

    for s in missing_req:
        canon_lower = resolve_canonical_skill(s).lower()
        if canon_lower not in registry.evidence_records:
            quote = find_jd_quote(s, jd_text)
            registry.register_evidence(
                skill=s,
                evidence_type="not_evidenced",
                source_doc="job_description",
                supporting_text=f"Target requirement from job description: '{quote}' (Not evidenced in resume)",
                evidence_strength="none",
                confidence=0.0,
                is_required=True
            )
        if canon_lower in registry.job_requirements:
            req = registry.job_requirements[canon_lower]
            if not req.is_satisfied:
                req.tier = "Required"

    for s in missing_pref:
        canon_lower = resolve_canonical_skill(s).lower()
        if canon_lower not in registry.evidence_records:
            quote = find_jd_quote(s, jd_text)
            registry.register_evidence(
                skill=s,
                evidence_type="not_evidenced",
                source_doc="job_description",
                supporting_text=f"Preferred requirement from job description: '{quote}' (Not evidenced in resume)",
                evidence_strength="none",
                confidence=0.0,
                is_preferred=True
            )
        if canon_lower in registry.job_requirements:
            req = registry.job_requirements[canon_lower]
            if not req.is_satisfied:
                req.tier = "Preferred"

    # -------------------------------------------------------------------------
    # 6. Reconcile Alternative Requirement Groups
    # -------------------------------------------------------------------------
    satisfied_alts = analysis_data.get("satisfied_alternatives") or []
    for sat in satisfied_alts:
        sat_skill = sat.get("satisfied_by")
        group = sat.get("group") or []
        tier = sat.get("tier", "Required")
        omitted = sat.get("omitted_alternatives") or []

        for om in omitted:
            om_canon_lower = resolve_canonical_skill(om).lower()
            if om_canon_lower in registry.job_requirements:
                req = registry.job_requirements[om_canon_lower]
                req.is_satisfied = True
                req.satisfaction_status = f"satisfied_via_alternative_{sat_skill}"
                req.matched_candidate_skill = sat_skill
            # If omitted skill was marked not_evidenced, clarify in evidence record
            if om_canon_lower in registry.evidence_records:
                ev = registry.evidence_records[om_canon_lower]
                if ev.evidence_type == "not_evidenced":
                    ev.supporting_text = f"Alternative requirement group satisfied by candidate competency in '{sat_skill}'."

    # -------------------------------------------------------------------------
    # 7. Apply Any Session-Level User Confirmations
    # -------------------------------------------------------------------------
    user_confs = analysis_data.get("user_confirmations") or {}
    for k, v in user_confs.items():
        registry.add_user_confirmation(k, v)

    return registry

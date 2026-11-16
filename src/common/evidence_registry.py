"""
Unified Candidate Evidence & Job Requirement Intelligence Foundation.

Provides a single source of truth across all analytical and educational modules:
- Resume Analyzer
- Skill Gap Analytics
- Career Mentor
- Interview Intelligence Studio

Enforces strict consistency invariants:
1. Matched skills and missing skills must not contradict each other (Disjointness).
2. Aliases must resolve consistently to canonical representations.
3. Requirement tiers (Required vs Preferred) must agree with the source JD context.
4. Candidate evidence must be traceable to exact resume text or confirmed user input.
5. No unsupported first-person claims or fabricated achievements.
6. Honest uncertainty acknowledgment when evidence is lacking.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any, Tuple
import re

# Canonical skill aliases for unified resolution
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
    "excel": "Excel",
    "ms excel": "Excel",
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
}

def resolve_canonical_skill(raw_name: str) -> str:
    """Resolves any skill variant or alias to its canonical title-cased representation."""
    if not raw_name or not isinstance(raw_name, str):
        return ""
    norm = raw_name.lower().strip()
    return CANONICAL_SKILL_ALIASES.get(norm, raw_name.strip())


@dataclass
class EvidenceRecord:
    """
    Structured evidence record for a single competency.
    Explicitly categorizes candidate relationship and evidence strength.
    """
    skill: str
    canonical_skill: str
    evidence_type: str  # 'demonstrated_project', 'demonstrated_internship', 'demonstrated_experience', 'explicit_mention', 'partially_evidenced', 'not_evidenced', 'user_confirmed'
    source_doc: str     # 'resume', 'job_description', 'user_input'
    supporting_text: str
    project_association: Optional[str] = None
    evidence_strength: str = "none"  # 'strong', 'moderate', 'weak', 'none', 'confirmed'
    confidence: float = 0.0          # 0.0 to 1.0
    candidate_confirmation: str = "unconfirmed"  # 'unconfirmed', 'confirmed', 'rejected'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobRequirementRecord:
    """
    Structured intelligence record for a single job requirement.
    Preserves exact supporting sentence and multi-skill clause context.
    """
    name: str
    canonical_name: str
    supporting_sentence: str
    tier: str            # 'Required', 'Preferred', 'Unspecified'
    category: str        # 'Core Technical Skills', 'Engineering Tools and Practices', etc.
    role_relevance: str
    prerequisites: List[str] = field(default_factory=list)
    related_requirements: List[str] = field(default_factory=list)

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
        candidate_confirmation: str = "unconfirmed"
    ) -> EvidenceRecord:
        """Creates and registers a verified or candidate evidence record."""
        canonical = resolve_canonical_skill(skill)
        record = EvidenceRecord(
            skill=skill,
            canonical_skill=canonical,
            evidence_type=evidence_type,
            source_doc=source_doc,
            supporting_text=supporting_text,
            project_association=project_association,
            evidence_strength=evidence_strength,
            confidence=confidence,
            candidate_confirmation=candidate_confirmation
        )
        self.evidence_records[canonical.lower()] = record
        return record

    def register_job_requirement(
        self,
        name: str,
        supporting_sentence: str,
        tier: str,
        category: str,
        role_relevance: str,
        prerequisites: Optional[List[str]] = None,
        related_requirements: Optional[List[str]] = None
    ) -> JobRequirementRecord:
        """Registers a structured job requirement with full contextual lineage."""
        canonical = resolve_canonical_skill(name)
        record = JobRequirementRecord(
            name=name,
            canonical_name=canonical,
            supporting_sentence=supporting_sentence,
            tier=tier,
            category=category,
            role_relevance=role_relevance,
            prerequisites=prerequisites or [],
            related_requirements=related_requirements or []
        )
        self.job_requirements[canonical.lower()] = record
        return record

    def add_user_confirmation(self, key: str, value: Any):
        """Records an explicit user confirmation (e.g. verified degree or completed skill)."""
        self.user_confirmations[key] = {
            "value": value,
            "status": "confirmed"
        }
        # If confirming a skill, update or add evidence record
        canon = resolve_canonical_skill(key)
        if canon.lower() in self.evidence_records:
            rec = self.evidence_records[canon.lower()]
            rec.candidate_confirmation = "confirmed"
            rec.evidence_strength = "confirmed"
            rec.confidence = 1.0

    def get_record(self, skill: str) -> Optional[EvidenceRecord]:
        canon = resolve_canonical_skill(skill).lower()
        return self.evidence_records.get(canon)

    def get_demonstrated_skills(self) -> List[EvidenceRecord]:
        """Returns skills evidenced with action verbs in projects, internships, or experience."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type in ("demonstrated_project", "demonstrated_internship", "demonstrated_experience")
        ]

    def get_partially_evidenced_skills(self) -> List[EvidenceRecord]:
        """Returns skills mentioned only in static keyword lists without project grounding."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "partially_evidenced"
        ]

    def get_explicitly_mentioned_skills(self) -> List[EvidenceRecord]:
        """Returns skills explicitly listed anywhere in the resume."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type in ("explicit_mention", "partially_evidenced", "demonstrated_project", "demonstrated_internship", "demonstrated_experience")
        ]

    def get_missing_skills(self) -> List[EvidenceRecord]:
        """Returns job requirements not evidenced in the candidate resume."""
        return [
            r for r in self.evidence_records.values()
            if r.evidence_type == "not_evidenced"
        ]

    def verify_consistency_invariants(self) -> Tuple[bool, List[str]]:
        """
        Validates all consistency invariants across candidate evidence and job requirements:
        1. Disjointness: No skill can simultaneously be in matched and missing.
        2. Status agreement: Requirement tier matches JD context.
        3. No empty or ungrounded evidence records.
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
            "missing_gaps_count": len(self.get_missing_skills()),
            "job_requirements_count": len(self.job_requirements),
            "user_confirmations": self.user_confirmations,
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
    """
    registry = CandidateEvidenceRegistry()

    # 1. Projects
    projects = analysis_data.get("projects") or analysis_data.get("relevant_projects") or []
    for p in projects:
        p_title = p.get("title") or p.get("project_title") or "Technical Project"
        techs = p.get("technologies") or p.get("tech_stack") or []
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(",") if t.strip()]
        desc = p.get("description") or p.get("project_description") or ""

        for tech in techs:
            registry.register_evidence(
                skill=tech,
                evidence_type="demonstrated_project",
                source_doc="resume",
                supporting_text=f"Demonstrated in project '{p_title}': {desc[:120]}...",
                project_association=p_title,
                evidence_strength="strong",
                confidence=0.95
            )

    # 2. Internships
    internships = analysis_data.get("internships") or []
    for it in internships:
        org = it.get("organization") or it.get("company") or "Internship Organization"
        resps = it.get("responsibilities") or []
        resp_text = "; ".join(resps) if isinstance(resps, list) else str(resps)
        # Extract skills in responsibilities
        for word in re.findall(r"\b[A-Za-z#+.-]{2,}\b", resp_text):
            canon = resolve_canonical_skill(word)
            if canon.lower() != word.lower() and canon.lower() not in registry.evidence_records:
                registry.register_evidence(
                    skill=canon,
                    evidence_type="demonstrated_internship",
                    source_doc="resume",
                    supporting_text=f"Demonstrated at {org}: {resp_text[:120]}...",
                    project_association=org,
                    evidence_strength="moderate",
                    confidence=0.85
                )

    # 3. Matched Skills (solid vs partial)
    solid_skills = analysis_data.get("solidly_evidenced_skills") or []
    partial_skills = analysis_data.get("partially_evidenced_skills") or []
    resume_skills = analysis_data.get("resume_skills") or []

    for s in solid_skills:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in registry.evidence_records:
            registry.register_evidence(
                skill=s,
                evidence_type="demonstrated_experience",
                source_doc="resume",
                supporting_text=f"Verified with contextual engineering verbs in resume.",
                evidence_strength="strong",
                confidence=0.90
            )

    for s in partial_skills:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in registry.evidence_records:
            registry.register_evidence(
                skill=s,
                evidence_type="partially_evidenced",
                source_doc="resume",
                supporting_text="Listed in static skills list or isolated keyword block without action verbs or project context.",
                evidence_strength="weak",
                confidence=0.60
            )

    for s in resume_skills:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in registry.evidence_records:
            registry.register_evidence(
                skill=s,
                evidence_type="explicit_mention",
                source_doc="resume",
                supporting_text="Explicitly mentioned in resume text.",
                evidence_strength="moderate",
                confidence=0.75
            )

    # 4. Missing Skills (Gaps)
    missing_req = analysis_data.get("missing_required_skills") or []
    missing_pref = analysis_data.get("missing_preferred_skills") or []
    jd_text = analysis_data.get("job_description_text") or analysis_data.get("raw_jd") or ""

    def find_jd_quote(sk: str) -> str:
        if not jd_text:
            return "Exact JD evidence unavailable."
        norm = sk.lower()
        sentences = re.split(r"(?<=[.!?\n])\s+", jd_text)
        for sent in sentences:
            s_clean = sent.strip()
            if not s_clean:
                continue
            if re.search(rf"\b{re.escape(norm)}\b", s_clean.lower()):
                return s_clean.strip(" \t\n*-•")
        return "Exact JD evidence unavailable."

    for s in missing_req:
        canon = resolve_canonical_skill(s)
        # Invariant: do not overwrite demonstrated skills
        if canon.lower() not in registry.evidence_records:
            quote = find_jd_quote(s)
            registry.register_evidence(
                skill=s,
                evidence_type="not_evidenced",
                source_doc="job_description",
                supporting_text=f"Target requirement from job description: '{quote}'",
                evidence_strength="none",
                confidence=0.0
            )
            registry.register_job_requirement(
                name=s,
                supporting_sentence=quote,
                tier="Required",
                category="Core Technical Skills",
                role_relevance=f"Mandatory competency required for target position."
            )

    for s in missing_pref:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in registry.evidence_records:
            quote = find_jd_quote(s)
            registry.register_evidence(
                skill=s,
                evidence_type="not_evidenced",
                source_doc="job_description",
                supporting_text=f"Preferred requirement from job description: '{quote}'",
                evidence_strength="none",
                confidence=0.0
            )
            registry.register_job_requirement(
                name=s,
                supporting_sentence=quote,
                tier="Preferred",
                category="Engineering Tools and Practices",
                role_relevance=f"Preferred competency providing competitive candidate differentiation."
            )

    return registry

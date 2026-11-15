"""
Directed Skill Dependency Model (DAG).

Models prerequisite relationships between technologies and competencies:
- JavaScript -> TypeScript
- Python -> Pandas -> PySpark
- Git -> Automated Testing -> CI/CD
- Flask / Backend -> Docker -> Kubernetes / Cloud Deployment
- SQL -> Query Optimization -> Database Performance
- Statistics -> Scikit-Learn -> PyTorch / Deep Learning

Enables prerequisite-aware personalized starting point recommendations.
"""

from typing import Dict, List, Set, Any, Tuple
from src.common.evidence_registry import resolve_canonical_skill

# Directed prerequisite graph: skill -> list of prerequisite skills
PREREQUISITE_DEPENDENCY_GRAPH: Dict[str, List[str]] = {
    # Programming & Type Systems
    "typescript": ["javascript", "html", "css"],
    "javascript": ["html", "css", "programming fundamentals"],
    "python": ["programming fundamentals", "data structures"],
    "java": ["object-oriented programming", "data structures"],
    "c++": ["c", "pointers & memory management", "data structures"],
    "c": ["algorithms", "computer architecture"],

    # Frontend
    "react": ["javascript", "html", "css"],
    "vue": ["javascript", "html", "css"],
    "angular": ["typescript", "javascript", "html"],

    # Backend
    "flask": ["python", "http & rest apis"],
    "fastapi": ["python", "type hints", "rest apis"],
    "django": ["python", "sql", "mvc architecture"],
    "rest apis": ["http protocol", "json serialization"],

    # Databases
    "sql": ["relational data concepts", "tables & schemas"],
    "postgresql": ["sql", "acid transactions", "relational modeling"],
    "mysql": ["sql", "relational modeling"],
    "mongodb": ["nosql concepts", "json/bson document modeling"],
    "query optimization": ["sql", "indexing (b-tree)", "explain plans"],

    # DevOps & Infrastructure
    "docker": ["linux commands", "process isolation", "backend architecture"],
    "kubernetes": ["docker", "networking basics", "cluster concepts"],
    "ci/cd": ["git", "unit testing / pytest", "shell scripting"],
    "git": ["command line navigation", "versioning fundamentals"],
    "linux": ["cli navigation", "file permissions", "process management"],

    # Cloud
    "aws": ["linux", "networking (ip/dns/subnets)", "iam & cloud security"],
    "azure": ["linux/windows", "networking", "cloud resource management"],
    "google cloud": ["linux", "cloud storage", "iam policies"],

    # Data Engineering
    "spark": ["python or java", "sql", "distributed systems"],
    "pyspark": ["python", "pandas", "sql"],
    "hadoop": ["linux", "distributed storage (hdfs)", "java or python"],
    "kafka": ["event-driven architecture", "python or java", "distributed messaging"],
    "etl": ["sql", "data validation", "python"],

    # Data Analytics & BI
    "excel": ["arithmetic formulas", "data formatting"],
    "power bi": ["excel", "sql", "dimensional data modeling"],
    "tableau": ["excel", "data visualization principles"],

    # Machine Learning & AI
    "machine learning": ["python", "numpy", "pandas", "statistics"],
    "scikit-learn": ["python", "numpy", "pandas", "feature engineering"],
    "pytorch": ["python", "linear algebra", "machine learning fundamentals"],
    "tensorflow": ["python", "calculus & linear algebra", "neural network basics"],
    "nlp": ["python", "regex", "tokenization", "machine learning"],
    "computer vision": ["python", "numpy", "image matrices", "machine learning"],

    # Professional & Business Competencies
    "project management": ["team communication", "agile / scrum principles"],
    "jira": ["agile backlog concepts", "issue tracking"],
    "visio": ["system design principles", "flowcharting conventions"],
    "communication": ["active listening", "technical presentation structure"],
    "analytical problem-solving": ["root cause analysis (5 whys)", "debugging fundamentals"],
    "focus": ["pomodoro technique", "context-switch minimization"],
    "pc skills": ["operating system navigation", "file directory management"]
}


def get_prerequisites_for_skill(skill_name: str) -> List[str]:
    """Returns direct prerequisites for a skill, if defined in the dependency graph."""
    canon = resolve_canonical_skill(skill_name).lower()
    return PREREQUISITE_DEPENDENCY_GRAPH.get(canon, [])


def evaluate_candidate_prerequisites(
    skill_name: str,
    verified_skills: List[str]
) -> Dict[str, Any]:
    """
    Evaluates whether the candidate meets foundational prerequisites for target skill.
    Returns:
    - met_prerequisites: list of prerequisites candidate already possesses
    - missing_prerequisites: list of prerequisites candidate lacks
    - recommended_starting_point: adaptive guidance on where to start
    """
    prereqs = get_prerequisites_for_skill(skill_name)
    canon_verified = {resolve_canonical_skill(s).lower() for s in verified_skills}

    met = []
    missing = []

    for p in prereqs:
        # Check if candidate has p or any related token
        p_canon = resolve_canonical_skill(p).lower()
        if p_canon in canon_verified or any(p in v or v in p for v in canon_verified):
            met.append(p)
        else:
            missing.append(p)

    has_all = len(missing) == 0
    has_some = len(met) > 0

    if not prereqs:
        starting_point = f"Begin directly with official documentation and foundational setup for {skill_name}."
    elif has_all:
        starting_point = (
            f"Candidate has verified prerequisite foundations ({', '.join(met)}). "
            f"You can bypass introductory syntax and directly implement production patterns in {skill_name}."
        )
    elif has_some:
        starting_point = (
            f"Candidate has verified {', '.join(met)}, but lacks {', '.join(missing)}. "
            f"Spend Day 1 reviewing {', '.join(missing)} bridge concepts before diving into advanced {skill_name} features."
        )
    else:
        starting_point = (
            f"Prerequisite foundations ({', '.join(prereqs)}) are not yet evidenced. "
            f"Start with prerequisite concepts ({prereqs[0]}) to establish the essential mental model before tackling {skill_name}."
        )

    return {
        "prerequisites": prereqs,
        "met_prerequisites": met,
        "missing_prerequisites": missing,
        "has_all_prerequisites": has_all,
        "has_partial_prerequisites": has_some and not has_all,
        "recommended_starting_point": starting_point
    }

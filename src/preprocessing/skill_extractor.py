"""
Skill Dictionary, Taxonomy, Alias Normalization, and Extraction Engine.
High-performance phrase matching using n-gram set hashing, context-aware boundary validation,
and competency taxonomy classification.
Zero LLM reliance. Fully deterministic and fast.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import ast
import re
import pandas as pd
from src.preprocessing.text_cleaner import clean_text


# Competency Taxonomy Categories (8-Category Standardized Taxonomy)
TAXONOMY_PROGRAMMING_LANGUAGES = "Programming languages"
TAXONOMY_FRAMEWORKS_LIBRARIES = "Frameworks and libraries"
TAXONOMY_DATABASES = "Databases"
TAXONOMY_DEVELOPER_TOOLS = "Developer tools"
TAXONOMY_CLOUD_INFRASTRUCTURE = "Cloud and infrastructure"
TAXONOMY_PRODUCTIVITY = "Productivity software"
TAXONOMY_PROFESSIONAL = "Professional competencies"
TAXONOMY_SOFT = "Soft skills"
TAXONOMY_GENERIC = "Generic / Ambiguous"

# Backward compatibility aliases
TAXONOMY_TECHNICAL = TAXONOMY_PROGRAMMING_LANGUAGES
TAXONOMY_TOOL = TAXONOMY_DEVELOPER_TOOLS

# Generic terms that must NEVER become standalone required technical skills
FILTERED_GENERIC_SKILLS = {
    "applications", "application", "application software", "applications software",
    "software", "hardware", "technology", "technologies", "computer software",
    "tools", "commitment", "enthusiasm", "ownership",
    "opportunity", "environment", "responsibilities", "requirements",
    "candidate", "role", "team", "experience", "work", "job", "skills",
    "knowledge", "ability", "background", "field", "degree", "solutions",
    "services", "products", "performance", "delivery", "quality", "support",
    "operations", "management", "processes", "process", "systems", "system",
    "travel", "zoom", "linkedin", "training", "innovation", "screening",
    "learning solutions", "solution", "learning", "scheduling", "reporting",
    "programming", "persistence", "modeling", "dashboards", "execution",
    "writing", "satisfaction", "customer satisfaction", "cloud environments",
    "web applications", "sql queries", "agile scrum", "scripting",
    "reliability", "microsoft", "networks", "cloud software", "predictive modeling"
}

# Ambiguous skills requiring contextual verification
AMBIGUOUS_SKILLS = {"r", "c", "go", "sql", "ai", "ml"}

# Canonical technical skill aliases mapping
TECHNICAL_ALIAS_MAP: Dict[str, str] = {
    # Programming Languages
    "cpp": "c++",
    "c++": "c++",
    "c plus plus": "c++",
    "c#": "c#",
    "csharp": "c#",
    "c sharp": "c#",
    "dotnet": ".net",
    ".net": ".net",
    ".net core": ".net",
    "asp.net": ".net",
    "python": "python",
    "py": "python",
    "python3": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "golang": "go",
    "go lang": "go",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "kotlin": "kotlin",
    "scala": "scala",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "objective-c": "objective-c",
    "matlab": "matlab",
    "sql": "sql",
    "pl/sql": "pl/sql",
    "t-sql": "sql",
    "bash": "bash",
    "shell": "shell",
    "powershell": "powershell",
    "c": "c",
    "c programming": "c",
    "c language": "c",
    "r": "r",
    "r programming": "r",
    "r language": "r",
    "rstudio": "rstudio",

    # Web & Application Frameworks
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react native": "react native",
    "angular": "angular",
    "angularjs": "angular",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "vue.js": "vue.js",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "express": "express.js",
    "expressjs": "express.js",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "spring": "spring boot",
    "spring boot": "spring boot",
    "rails": "ruby on rails",
    "ruby on rails": "ruby on rails",
    "html": "html",
    "html5": "html",
    "css": "css",
    "css3": "css",
    "sass": "sass",
    "bootstrap": "bootstrap",
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",

    # Databases & Storage
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "oracle": "oracle database",
    "mssql": "sql server",
    "sql server": "sql server",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "redis": "redis",
    "cassandra": "cassandra",
    "dynamodb": "dynamodb",
    "elasticsearch": "elasticsearch",

    # Cloud & DevOps
    "aws": "amazon web services",
    "amazon web services": "amazon web services",
    "gcp": "google cloud platform",
    "google cloud": "google cloud platform",
    "azure": "microsoft azure",
    "microsoft azure": "microsoft azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "terraform": "terraform",
    "ansible": "ansible",
    "jenkins": "jenkins",
    "ci/cd": "ci/cd",
    "git": "git",
    "github": "github",
    "gitlab": "gitlab",
    "linux": "linux",
    "unix": "unix",

    # Machine Learning & Data Science
    "machine learning": "machine learning",
    "ml": "machine learning",
    "deep learning": "deep learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "natural language processing": "natural language processing",
    "computer vision": "computer vision",
    "cv": "computer vision",
    "opencv": "opencv",
    "nginx": "nginx",
    "rest apis": "rest api",
    "restful apis": "rest api",
    "restful api": "rest api",
    "code reviews": "code review",
    "code review": "code review",
    "unit test": "unit testing",
    "unit tests": "unit testing",
    "unit testing": "unit testing",
    "mediapipe": "mediapipe",
    "media pipe": "mediapipe",
    "zoom api": "zoom api",
    "pandas": "pandas",
    "numpy": "numpy",
    "scipy": "scipy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "keras": "keras",
    "spark": "apache spark",
    "apache spark": "apache spark",
    "hadoop": "hadoop",
    "tableau": "tableau",
    "power bi": "power bi",
    "data analysis": "data analysis",
    "data visualization": "data visualization",

    # Engineering & Methodologies
    "agile": "agile",
    "scrum": "scrum",
    "jira": "jira",
    "rest api": "rest api",
    "restful": "rest api",
    "graphql": "graphql",
    "microservices": "microservices",
    "unit testing": "unit testing",
    "pytest": "pytest",
    "object-oriented programming": "oop",
    "oop": "oop",

    # Productivity Software
    "microsoft word": "word",
    "ms word": "word",
    "msword": "word",
    "word": "word",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "msexcel": "excel",
    "excel": "excel",
    "microsoft powerpoint": "powerpoint",
    "ms powerpoint": "powerpoint",
    "mspowerpoint": "powerpoint",
    "powerpoint": "powerpoint",
    "microsoft office": "office",
    "ms office": "office",
    "office": "office",

    # Soft Skills & Communication
    "communication skills": "communication",
    "communication": "communication",
    "communications": "communication",
    "verbal communication": "communication",
    "written communication": "communication"
}

# 8-Category Taxonomy Membership Sets
KNOWN_PROGRAMMING_LANGUAGES = {
    "python", "java", "c++", "c#", "c", "go", "rust", "ruby", "php", "swift",
    "kotlin", "scala", "javascript", "typescript", "r", "matlab", "bash", "shell",
    "powershell", "pl/sql", "objective-c", "dart", "perl"
}

KNOWN_FRAMEWORKS_AND_LIBRARIES = {
    "react", "react native", "angular", "vue.js", "node.js", "express.js",
    "django", "flask", "fastapi", "spring boot", "ruby on rails", "html", "css",
    "sass", "bootstrap", "tailwind css", "pandas", "numpy", "scipy",
    "scikit-learn", "tensorflow", "pytorch", "keras", "jquery", ".net"
}

KNOWN_DATABASES = {
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "elasticsearch", "sql server", "oracle database", "sql",
    "mariadb", "couchdb", "neo4j"
}

KNOWN_DEVELOPER_TOOLS = {
    "git", "github", "gitlab", "jira", "pytest", "rstudio", "postman",
    "vs code", "vim", "eclipse", "gradle", "maven", "webpack", "npm", "yarn"
}

KNOWN_CLOUD_AND_INFRASTRUCTURE = {
    "amazon web services", "google cloud platform", "microsoft azure", "docker",
    "kubernetes", "terraform", "ansible", "jenkins", "ci/cd", "linux", "unix",
    "aws", "gcp", "azure", "apache spark", "hadoop"
}

KNOWN_PRODUCTIVITY_SOFTWARE = {
    "word", "excel", "powerpoint", "office", "outlook", "ms word", "ms excel",
    "ms powerpoint", "ms office", "microsoft word", "microsoft excel",
    "microsoft powerpoint", "microsoft office", "spreadsheets", "google sheets",
    "google docs", "notion", "slack", "trello", "zoom", "teams"
}

KNOWN_PROFESSIONAL_SKILLS = {
    "agile", "scrum", "microservices", "rest api", "graphql", "unit testing",
    "system architecture", "code review", "quality assurance", "devops",
    "user research", "market research", "data analysis", "data visualization",
    "project management", "product management", "software development lifecycle",
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "oop", "tableau", "power bi"
}

KNOWN_SOFT_SKILLS = {
    "communication", "communication skills", "teamwork", "leadership",
    "problem solving", "critical thinking", "collaboration", "adaptability",
    "time management", "interpersonal skills", "presentation", "mentoring",
    "negotiation", "creativity", "work ethic", "verbal communication",
    "written communication"
}

KNOWN_TOOLS_AND_TECH = (
    KNOWN_PROGRAMMING_LANGUAGES
    | KNOWN_FRAMEWORKS_AND_LIBRARIES
    | KNOWN_DATABASES
    | KNOWN_DEVELOPER_TOOLS
    | KNOWN_CLOUD_AND_INFRASTRUCTURE
)


def categorize_competency(skill_name: str) -> str:
    """
    Classifies a normalized skill into the 8-category competency taxonomy:
    1. Programming languages
    2. Frameworks and libraries
    3. Databases
    4. Developer tools
    5. Cloud and infrastructure
    6. Productivity software
    7. Professional competencies
    8. Soft skills
    (or Generic / Ambiguous if filtered)
    """
    s = skill_name.strip().lower()
    if s in FILTERED_GENERIC_SKILLS or "application software" in s:
        return TAXONOMY_GENERIC
    if s in KNOWN_SOFT_SKILLS or "communication" in s or "leadership" in s or "teamwork" in s:
        return TAXONOMY_SOFT
    if s in KNOWN_PRODUCTIVITY_SOFTWARE or any(k in s for k in ["word", "excel", "powerpoint", "office"]):
        return TAXONOMY_PRODUCTIVITY
    if s in KNOWN_DATABASES:
        return TAXONOMY_DATABASES
    if s in KNOWN_CLOUD_AND_INFRASTRUCTURE:
        return TAXONOMY_CLOUD_INFRASTRUCTURE
    if s in KNOWN_DEVELOPER_TOOLS:
        return TAXONOMY_DEVELOPER_TOOLS
    if s in KNOWN_FRAMEWORKS_AND_LIBRARIES:
        return TAXONOMY_FRAMEWORKS_LIBRARIES
    if s in KNOWN_PROGRAMMING_LANGUAGES:
        return TAXONOMY_PROGRAMMING_LANGUAGES
    if s in KNOWN_PROFESSIONAL_SKILLS:
        return TAXONOMY_PROFESSIONAL
    # Language/framework heuristical checks
    if any(k in s for k in ["python", "java", "c++", "c#", "ruby", "golang", "rust", "php", "swift", "kotlin", "scala"]):
        return TAXONOMY_PROGRAMMING_LANGUAGES
    if any(k in s for k in ["learning", "processing", "vision", "analysis", "intelligence", "architecture"]):
        return TAXONOMY_PROFESSIONAL
    if any(k in s for k in ["sql", "database", "query"]):
        return TAXONOMY_DATABASES
    if any(k in s for k in ["cloud", "server", "deploy"]):
        return TAXONOMY_CLOUD_INFRASTRUCTURE
    # Default to developer tools
    return TAXONOMY_DEVELOPER_TOOLS


CANONICAL_SKILL_NAMES: Dict[str, str] = {
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "mediapipe": "MediaPipe",
    "media pipe": "MediaPipe",
    "excel": "Excel",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud platform": "GCP",
    "rest api": "REST APIs",
    "restful api": "REST APIs",
    "restful apis": "REST APIs",
    "rest apis": "REST APIs",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "opencv": "OpenCV",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "fastapi": "FastAPI",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "docker": "Docker",
    "github": "GitHub",
    "gitlab": "GitLab",
    "ci/cd": "CI/CD",
    "html": "HTML",
    "css": "CSS",
    "node.js": "Node.js",
    "react": "React",
    "vue.js": "Vue.js",
    "power bi": "Power BI",
    "c++": "C++",
    "c#": "C#",
    ".net": ".NET",
    "php": "PHP",
    "sql": "SQL",
    "pl/sql": "PL/SQL",
    "hadoop": "Hadoop",
    "spark": "Spark",
    "kafka": "Kafka",
    "linux": "Linux",
    "python": "Python",
    "java": "Java",
    "django": "Django",
    "flask": "Flask",
    "spring boot": "Spring Boot",
    "pandas": "Pandas",
    "numpy": "NumPy"
}


def get_canonical_skill_name(skill: str) -> str:
    """Returns official canonical casing for a skill name."""
    s_low = skill.strip().lower()
    if s_low in CANONICAL_SKILL_NAMES:
        return CANONICAL_SKILL_NAMES[s_low]
    return skill.strip().title()


def get_canonical_taxonomy_category(skill_name: str) -> str:
    """
    Classifies a skill into the 9 canonical taxonomy tiers:
    1. Programming Languages
    2. Web Frameworks & Libraries
    3. Machine Learning & AI
    4. Cloud & DevOps
    5. Databases & Big Data
    6. Operating Systems & Tooling
    7. System Architecture & Concepts
    8. Core Computer Science
    9. Professional & Collaborative
    """
    s = skill_name.strip().lower()

    # 1. Programming Languages
    if s in {
        "python", "java", "c++", "c#", "c", "go", "rust", "ruby", "php", "swift",
        "kotlin", "scala", "javascript", "typescript", "r", "matlab", "bash", "shell",
        "powershell", "pl/sql", "objective-c", "dart", "perl"
    } or any(s == lang for lang in ["python", "java", "c++", "c#", "golang", "rust"]):
        return "Programming Languages"

    # 2. Machine Learning & AI
    if s in {
        "scikit-learn", "sklearn", "pytorch", "tensorflow", "keras", "opencv", "mediapipe",
        "nlp", "natural language processing", "nltk", "spacy", "huggingface", "xgboost",
        "lightgbm", "pandas", "numpy", "scipy", "machine learning", "deep learning",
        "computer vision", "transformers", "llm"
    } or any(k in s for k in ["machine learning", "deep learning", "neural", "vision", "nlp"]):
        return "Machine Learning & AI"

    # 3. Web Frameworks & Libraries
    if s in {
        "flask", "django", "fastapi", "react", "angular", "vue.js", "vue", "node.js",
        "node", "express.js", "express", "spring boot", "spring", "ruby on rails", "rails",
        "html", "css", "sass", "bootstrap", "tailwind css", "tailwind", "jquery", ".net",
        "asp.net", "nextjs", "svelte"
    }:
        return "Web Frameworks & Libraries"

    # 4. Databases & Big Data
    if s in {
        "sql", "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra",
        "sqlite", "dynamodb", "elasticsearch", "hadoop", "spark", "apache spark",
        "kafka", "hive", "oracle", "mariadb", "sql server"
    } or any(k in s for k in ["database", "big data", "spark", "hadoop", "kafka"]):
        return "Databases & Big Data"

    # 5. Cloud & DevOps
    if s in {
        "aws", "amazon web services", "azure", "microsoft azure", "gcp", "google cloud platform",
        "docker", "kubernetes", "k8s", "ci/cd", "terraform", "ansible", "jenkins",
        "github actions", "nginx", "apache", "prometheus", "grafana"
    } or any(k in s for k in ["cloud", "devops", "ci/cd", "container"]):
        return "Cloud & DevOps"

    # 6. Operating Systems & Tooling
    if s in {
        "linux", "unix", "windows", "git", "github", "gitlab", "postman", "jira",
        "vs code", "vim", "docker cli", "bash", "shell", "powershell", "eclipse",
        "word", "excel", "powerpoint", "office"
    }:
        return "Operating Systems & Tooling"

    # 7. System Architecture & Concepts
    if s in {
        "rest apis", "rest api", "rest", "restful", "microservices", "system design",
        "object-oriented programming", "oop", "multithreading", "concurrency",
        "asynchronous programming", "caching", "event-driven architecture",
        "graphql", "system architecture"
    }:
        return "System Architecture & Concepts"

    # 8. Core Computer Science
    if s in {
        "data structures", "algorithms", "dsa", "operating systems", "computer networks",
        "database management systems", "dbms", "compiler design", "distributed systems",
        "software engineering", "tcp/ip"
    }:
        return "Core Computer Science"

    # 9. Professional & Collaborative
    if s in {
        "agile", "scrum", "code review", "technical documentation", "mentorship",
        "mentoring", "team collaboration", "teamwork", "communication", "communication skills",
        "problem solving", "continuous learning", "critical thinking", "leadership",
        "adaptability", "time management"
    } or any(k in s for k in ["communication", "team", "agile", "leadership"]):
        return "Professional & Collaborative"

    return "Professional & Collaborative"


def build_skill_evidence_record(
    skill: str,
    resume_text: str = "",
    projects: Optional[List[Dict[str, Any]]] = None,
    internships: Optional[List[Dict[str, Any]]] = None,
    is_gap: bool = False,
    is_partially_evidenced: bool = False
) -> Dict[str, Any]:
    """
    Builds a complete evidence traceability record for an extracted skill.
    Enforces Section 2.3 Evidence Traceability.
    """
    canonical_name = get_canonical_skill_name(skill)
    taxonomy_category = get_canonical_taxonomy_category(skill)

    if is_gap:
        return {
            "canonical_skill_name": canonical_name,
            "taxonomy_category": taxonomy_category,
            "evidence_source": "Target Job Description",
            "supporting_sentence": "Skill requested in job description but not evidenced in resume.",
            "evidence_strength": "Not evidenced in resume",
            "detection_method": "job_requirement_diff"
        }

    skill_lower = skill.lower()
    projects = projects or []
    internships = internships or []

    # 1. Check Projects for Implementation Evidence
    for proj in projects:
        p_techs = [t.lower() for t in proj.get("technologies", [])]
        p_desc = proj.get("description", "")
        p_title = proj.get("title", proj.get("project_title", "Project"))
        if skill_lower in p_techs or re.search(rf"\b{re.escape(skill_lower)}\b", p_desc, re.I):
            sentences = [s.strip() for s in re.split(r"[.\n;]", p_desc) if s.strip()]
            support = next((s for s in sentences if re.search(rf"\b{re.escape(skill_lower)}\b", s, re.I)), p_desc[:120])
            return {
                "canonical_skill_name": canonical_name,
                "taxonomy_category": taxonomy_category,
                "evidence_source": f"Project: {p_title}",
                "supporting_sentence": support or f"Implemented in project '{p_title}'.",
                "evidence_strength": "Demonstrated in project",
                "detection_method": "project_entity_extraction"
            }

    # 2. Check Internships for Implementation Evidence
    for intern in internships:
        i_techs = [t.lower() for t in intern.get("technologies", [])]
        i_resps = " ".join(intern.get("responsibilities", []))
        i_org = intern.get("organization") or intern.get("position") or "Internship"
        if skill_lower in i_techs or re.search(rf"\b{re.escape(skill_lower)}\b", i_resps, re.I):
            sentences = [s.strip() for s in re.split(r"[.\n;]", i_resps) if s.strip()]
            support = next((s for s in sentences if re.search(rf"\b{re.escape(skill_lower)}\b", s, re.I)), i_resps[:120])
            return {
                "canonical_skill_name": canonical_name,
                "taxonomy_category": taxonomy_category,
                "evidence_source": f"Internship: {i_org}",
                "supporting_sentence": support or f"Utilized during internship at {i_org}.",
                "evidence_strength": "Demonstrated in project",
                "detection_method": "internship_entity_extraction"
            }

    # 3. Check Sentence Mentions in Resume
    sentences = [s.strip() for s in re.split(r"[.\n;]", resume_text) if s.strip()]
    pat = re.compile(rf"(?<![\w#+.]){re.escape(skill_lower)}(?![\w#+.])", re.I)
    matching_sentence = next((s for s in sentences if pat.search(s)), "")

    if is_partially_evidenced:
        return {
            "canonical_skill_name": canonical_name,
            "taxonomy_category": taxonomy_category,
            "evidence_source": "Resume Skills List",
            "supporting_sentence": matching_sentence or "Mentioned in resume skill inventory without project context.",
            "evidence_strength": "Partially evidenced",
            "detection_method": "isolated_keyword_match"
        }

    return {
        "canonical_skill_name": canonical_name,
        "taxonomy_category": taxonomy_category,
        "evidence_source": "Resume Content",
        "supporting_sentence": matching_sentence or "Referenced in parsed resume text.",
        "evidence_strength": "Mentioned in resume",
        "detection_method": "phrase_boundary_match"
    }


class SkillEngine:
    """
    High-performance Skill Extraction, Normalization, and Taxonomy Engine.
    Uses n-gram set hashing with strict token boundary validation for ambiguous skills.
    """

    def __init__(self, raw_skills_path: Optional[Union[str, Path]] = None):
        self.raw_skills_path = Path(raw_skills_path) if raw_skills_path else (
            Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "job_skill_set.csv"
        )
        self.alias_map: Dict[str, str] = dict(TECHNICAL_ALIAS_MAP)
        self.skill_set: Set[str] = set()
        self.max_ngram_len: int = 4
        self._build_lexicon()

    def _build_lexicon(self) -> None:
        """Loads dataset skills into an in-memory hash set, filtering generic false skills."""
        # 1. Add canonical aliases
        for alias, canonical in self.alias_map.items():
            if alias not in FILTERED_GENERIC_SKILLS:
                self.skill_set.add(alias)
            if canonical not in FILTERED_GENERIC_SKILLS:
                self.skill_set.add(canonical)

        # 2. Add raw dataset skills if available, filtering out generic nouns
        if self.raw_skills_path.exists():
            try:
                df = pd.read_csv(self.raw_skills_path)
                for entry in df["job_skill_set"].dropna():
                    try:
                        skills = ast.literal_eval(entry) if isinstance(entry, str) and entry.startswith("[") else [entry]
                        for s in skills:
                            cleaned = str(s).strip().lower()
                            # Reject generic words, standalone single characters, and purely numeric tokens
                            noise_words = {"training", "screening", "innovation", "travel", "zoom", "linkedin", "learning solution", "scheduling", "reporting", "satisfaction"}
                            has_noise = any(nw in cleaned for nw in noise_words) and "zoom api" not in cleaned
                            if (2 <= len(cleaned) <= 45 and
                                cleaned not in FILTERED_GENERIC_SKILLS and
                                not has_noise and
                                not cleaned.isdigit()):
                                self.skill_set.add(cleaned)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Warning: Could not load skills from {self.raw_skills_path}: {e}")

        # Compute max words per skill phrase
        for sk in self.skill_set:
            words_in_skill = len(sk.split())
            if words_in_skill > self.max_ngram_len:
                self.max_ngram_len = min(words_in_skill, 5)

    def normalize_skill(self, skill: str) -> str:
        """Returns the canonical name for a given skill phrase."""
        cleaned = skill.strip().lower()
        return self.alias_map.get(cleaned, cleaned)

    def _is_valid_ambiguous_skill(self, skill: str, word_idx: int, words: List[str], raw_text: str) -> bool:
        """
        Validates ambiguous short tokens (r, c, go, sql, ai, ml) against surrounding context.
        Prevents matching arbitrary characters inside words or irrelevant prose.
        """
        # Context window: 5 words before and after
        start = max(0, word_idx - 5)
        end = min(len(words), word_idx + 6)
        context_words = set(words[start:end])

        if skill == "r":
            # Valid indicators for R statistical programming language
            r_indicators = {
                "programming", "language", "rstudio", "python", "sql", "matlab",
                "sas", "stata", "spss", "statistics", "statistical", "data",
                "analytics", "biostatistics", "tidyverse", "ggplot", "cran"
            }
            return bool(context_words.intersection(r_indicators))

        elif skill == "c":
            # Valid indicators for C language
            c_indicators = {
                "programming", "language", "c++", "c#", "java", "assembly",
                "embedded", "linux", "unix", "kernel", "compilers", "pointer",
                "pointers", "operating", "firmware", "microcontroller"
            }
            return bool(context_words.intersection(c_indicators))

        elif skill == "go":
            go_indicators = {
                "golang", "programming", "language", "backend", "microservices",
                "rust", "python", "kubernetes", "docker", "goroutines", "concurrency",
                "distributed", "rest", "api", "developer", "engineer"
            }
            if word_idx + 1 < len(words) and words[word_idx + 1] in {"to", "through", "above", "beyond", "for"}:
                return False
            if word_idx > 0 and words[word_idx - 1] in {"the", "a", "will", "can", "to", "and", "must", "should", "would", "let", "lets"}:
                return False
            return bool(context_words.intersection(go_indicators))

        elif skill in {"ai", "ml"}:
            # Standalone AI/ML should not be parts of other words
            return True

        elif skill == "sql":
            return True

        return True

    def extract_skills(self, text: Optional[str]) -> Set[str]:
        """
        Extracts matched, deduplicated, and alias-normalized skills using n-gram set hashing.
        Validates token boundaries and ambiguous contexts deterministically.
        """
        if not text or not isinstance(text, str):
            return set()

        cleaned = clean_text(text).lower()

        # Check explicit compound phrases first
        extracted: Set[str] = set()

        # Explicit regex check for ambiguous skills with explicit wording
        if re.search(r"\b(?:r\s+programming|r\s+language|rstudio)\b", cleaned):
            extracted.add("r")
        if re.search(r"\b(?:c\s+programming|c\s+language)\b|\bc/c\+\+", cleaned) or re.search(r"(?i)\bc/c\+\+", text):
            extracted.add("c")
            extracted.add("c++")
        if re.search(r"\b(?:golang|go\s+programming|go\s+language)\b", cleaned):
            extracted.add("go")
        if re.search(r"(?<![\w#+.])c\+\+(?![\w#+.])", cleaned):
            extracted.add("c++")
        if re.search(r"(?<![\w#+.])c#(?![\w#+.])", cleaned):
            extracted.add("c#")
        if re.search(r"(?<![\w#+.])\.net(?![\w#+.])", cleaned):
            extracted.add(".net")
        if re.search(r"\bnode(?:\.js)?\b", cleaned):
            extracted.add("node.js")
        if re.search(r"\bci/cd\b", cleaned):
            extracted.add("ci/cd")
        if re.search(r"\bpl/sql\b", cleaned):
            extracted.add("pl/sql")

        # Replace non-essential punctuation with spaces while keeping technical characters
        token_str = re.sub(r"[,;:\(\)\[\]\{\}\<\>\"\']", " ", cleaned)
        raw_words = token_str.split()
        if not raw_words:
            return extracted

        preserved_tokens = {".net", "node.js", "vue.js", "react.js", "angular.js", "pl/sql", "tcp/ip", "ci/cd"}
        words = []
        for w in raw_words:
            if w in preserved_tokens:
                words.append(w)
            else:
                stripped = w.strip(".!?,;:~`")
                if stripped:
                    words.append(stripped)

        n = len(words)
        if n == 0:
            return extracted

        # Check 1-grams up to max_ngram_len
        for length in range(1, min(self.max_ngram_len + 1, n + 1)):
            for i in range(n - length + 1):
                phrase = " ".join(words[i:i + length])

                # Skip filtered generic terms
                if phrase in FILTERED_GENERIC_SKILLS:
                    continue

                canonical = None
                if phrase in self.alias_map:
                    canonical = self.alias_map[phrase]
                elif phrase in self.skill_set:
                    canonical = self.normalize_skill(phrase)

                if canonical:
                    # Filter generic terms again after canonicalization
                    if canonical in FILTERED_GENERIC_SKILLS:
                        continue

                    # Ambiguous skill verification
                    if canonical in AMBIGUOUS_SKILLS and length == 1:
                        if self._is_valid_ambiguous_skill(canonical, i, words, cleaned):
                            extracted.add(canonical)
                    else:
                        extracted.add(canonical)

        # Context-sensitive check for "research":
        # Only keep "research" if explicitly qualified (user research, market research, academic research, etc.)
        if "research" in extracted:
            if not re.search(r"\b(?:user|market|academic|clinical|scientific|operations|ux)\s+research\b|\bresearch\s+(?:engineer|scientist|analyst|associate|methodology)\b", cleaned):
                extracted.discard("research")

        return extracted

    def analyze_skill_gap(
        self,
        resume_text: Optional[str],
        job_text: Optional[str]
    ) -> Dict[str, Union[List[str], float, int]]:
        """
        Performs transparent skill gap analysis between resume and job description.
        """
        resume_skills = self.extract_skills(resume_text)
        job_skills = self.extract_skills(job_text)

        matched_skills = sorted(list(resume_skills.intersection(job_skills)))
        missing_skills = sorted(list(job_skills - resume_skills))
        extra_skills = sorted(list(resume_skills - job_skills))

        n_resume = len(resume_skills)
        n_job = len(job_skills)
        n_matched = len(matched_skills)
        n_missing = len(missing_skills)

        union_size = len(resume_skills.union(job_skills))
        jaccard = float(n_matched / union_size) if union_size > 0 else 0.0
        coverage = float(n_matched / n_job) if n_job > 0 else 0.0
        relevance = float(n_matched / n_resume) if n_resume > 0 else 0.0

        return {
            "resume_skills": sorted(list(resume_skills)),
            "job_skills": sorted(list(job_skills)),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "extra_skills": extra_skills,
            "resume_skill_count": n_resume,
            "job_skill_count": n_job,
            "matched_skill_count": n_matched,
            "missing_skill_count": n_missing,
            "jaccard_similarity": round(jaccard, 4),
            "job_coverage_ratio": round(coverage, 4),
            "resume_relevance_ratio": round(relevance, 4)
        }

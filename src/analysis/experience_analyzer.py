"""
Deterministic Experience, Project, and Internship Analyzer.
Extracts:
- Section-aware parsing with strict boundary enforcement
- Multi-line project extraction with attached dates, tech stacks, links, and descriptions
- Dedicated internship and practical industrial training extraction
- Explicit professional experience tenure classification (Full-time, Internships, Projects, Unestablished)
- Clean distinction between unestablished experience vs explicit zero
Zero LLM reliance. Fully deterministic.
"""

from typing import Dict, List, Optional, Set, Tuple
import re
from src.preprocessing.text_cleaner import extract_explicit_experience_years
from src.preprocessing.skill_extractor import SkillEngine


# ---------------------------------------------------------------------------
# Date Extraction & Normalization Regular Expressions
# ---------------------------------------------------------------------------
MONTHS_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
YEAR_PATTERN = r"(?:20\d{2}|19\d{2}|'?\d{2}\b)"
DASH_PATTERN = r"(?:\s*(?:-|–|—|to|till|until|~)\s*)"
PRESENT_PATTERN = r"(?:present|current|ongoing|till\s+date|now)"

DATE_TOKEN_PATTERN = rf"(?:{MONTHS_PATTERN}\.?\s*{YEAR_PATTERN}|{YEAR_PATTERN}|{MONTHS_PATTERN})"
DATE_RANGE_REGEX = re.compile(
    rf"(?i)\b({DATE_TOKEN_PATTERN}){DASH_PATTERN}(({DATE_TOKEN_PATTERN}|{PRESENT_PATTERN})\b|\b{PRESENT_PATTERN})"
)
SINGLE_DATE_REGEX = re.compile(rf"(?i)\b({DATE_TOKEN_PATTERN}|{PRESENT_PATTERN})\b")

# ---------------------------------------------------------------------------
# Section Boundary Patterns
# ---------------------------------------------------------------------------
SECTION_PATTERNS: Dict[str, List[str]] = {
    "projects": [
        r"^projects$",
        r"^personal\s+projects$",
        r"^academic\s+projects$",
        r"^technical\s+projects$",
        r"^key\s+projects$",
        r"^notable\s+projects$",
        r"^selected\s+projects$",
        r"^capstone\s+projects?$",
        r"^course\s+projects?$",
        r"^project\s+experience$"
    ],
    "internships": [
        r"^internships?$",
        r"^internship\s+experience$",
        r"^internships?\s*(&|and)\s*practical\s+experience$",
        r"^virtual\s+internships?$",
        r"^industrial\s+training$",
        r"^training\s*(&|and)\s*internships?$",
        r"^apprenticeships?$",
        r"^summer\s+internships?$",
        r"^training$",
        r"^experience\s*(&|and)\s*internships?$",
        r"^internships?\s*(&|and)\s*experience$"
    ],
    "experience": [
        r"^work\s+experience$",
        r"^professional\s+experience$",
        r"^employment(?:\s+history)?$",
        r"^experience$",
        r"^career\s+history$",
        r"^work\s+history$",
        r"^experience\s*(&|and)\s*internships?$",
        r"^internships?\s*(&|and)\s*experience$"
    ],
    "education": [
        r"^education$",
        r"^academic\s+(?:background|qualifications|details)$",
        r"^educational\s+qualifications$",
        r"^qualifications$"
    ],
    "skills": [
        r"^skills$",
        r"^technical\s+skills$",
        r"^skills\s+summary$",
        r"^core\s+competencies$",
        r"^areas\s+of\s+expertise$",
        r"^technologies$",
        r"^programming\s+languages$",
        r"^tools\s*(&|and)\s*technologies$"
    ],
    "certifications": [
        r"^certifications?$",
        r"^certificates?$",
        r"^licenses?(?:\s*(&|and)\s*certifications?)?$",
        r"^courses\s*(&|and)\s*certifications?$"
    ],
    "achievements": [
        r"^achievements?$",
        r"^honors?\s*(&|and)\s*awards?$",
        r"^awards?$",
        r"^accomplishments?$",
        r"^extra-?curricular(?:\s+activities)?$",
        r"^co-?curricular(?:\s+activities)?$",
        r"^volunteering$",
        r"^leadership(?:\s+activities)?$"
    ],
    "publications": [
        r"^publications?$",
        r"^research(?:\s+papers?)?$",
        r"^patents?$"
    ],
    "summary": [
        r"^summary$",
        r"^professional\s+summary$",
        r"^career\s+objective$",
        r"^objective$",
        r"^profile$",
        r"^about\s+me$"
    ]
}

EXCLUDED_SECTION_HEADERS: Set[str] = {
    "projects", "academic projects", "personal projects", "notable projects",
    "key projects", "selected projects", "technical projects", "experience",
    "work experience", "professional experience", "employment", "internships",
    "internship", "internship experience", "training", "industrial training",
    "experience & internships", "internships & experience",
    "education", "skills", "technical skills", "certifications", "certificates",
    "awards", "publications", "interests", "languages", "coursework", "summary",
    "profile", "contact", "references", "volunteer", "activities", "objective",
    "professional summary", "hobbies", "achievements", "skills summary"
}

TECH_STACK_REGEX = re.compile(
    r"(?i)^(?:tech(?:nology|nologies)?\s*stack|technologies|tech|tools(?:\s+used)?|built\s+with|key\s+technologies|skills\s+used)\s*[:\-]\s*(.+)$"
)
GITHUB_URL_REGEX = re.compile(r"(?i)\b(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+")
URL_REGEX = re.compile(r"(?i)\bhttps?://\S+")

# Canonical skill display names for clean, professional presentation
CANONICAL_DISPLAY_NAMES: Dict[str, str] = {
    "python": "Python",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "opencv": "OpenCV",
    "mediapipe": "MediaPipe",
    "media pipe": "MediaPipe",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "git": "Git",
    "github": "GitHub",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "svg": "SVG",
    "nlp": "NLP",
    "eda": "EDA",
    "nids": "NIDS",
    "cnn": "CNN",
    "rnn": "RNN",
    "lstm": "LSTM",
    "svm": "SVM",
    "api": "API",
    "apis": "APIs",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "isolation forest": "Isolation Forest",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "computer vision": "Computer Vision",
    "feature engineering": "Feature Engineering",
    "data preprocessing": "Data Preprocessing",
    "data normalization": "Data Normalization",
    "data visualization": "Data Visualization",
    "exploratory data analysis": "Exploratory Data Analysis (EDA)",
    "data analysis": "Data Analysis",
    "anomaly detection": "Anomaly Detection",
    "cybersecurity": "Cybersecurity",
    "network security": "Network Security",
    "network intrusion detection": "Network Intrusion Detection (NIDS)",
    "threat detection": "Threat Detection",
    "hyperparameter tuning": "Hyperparameter Tuning",
    "unsupervised learning": "Unsupervised Learning",
    "supervised learning": "Supervised Learning",
}


def canonicalize_tech_list(tech_items: List[str], skill_engine: Optional[SkillEngine] = None) -> List[str]:
    """
    Deduplicates technologies using canonical skill normalization while preserving
    clean, readable display names.
    Eliminates casing variants (e.g. NumPy vs Numpy), action-verb prefixes
    (e.g. 'Implemented Data Preprocessing' -> 'Data Preprocessing'), and redundant substrings
    (e.g. standalone 'Engineering' when 'Feature Engineering' exists).
    """
    if not tech_items:
        return []

    if skill_engine is None:
        try:
            skill_engine = SkillEngine()
        except Exception:
            skill_engine = None

    action_prefix_regex = re.compile(
        r"^(?:implemented|developed|built|trained|applied|performed|optimized|conducted|designed|using|used|learning|working\s+with)\s+",
        re.I
    )

    cleaned_tokens: List[str] = []
    for item in tech_items:
        clean = item.strip().strip("•-*–:,; ")
        clean = action_prefix_regex.sub("", clean).strip()
        if not clean or len(clean) < 2:
            continue
        # Filter purely generic competency words without technical qualifier
        if clean.lower() in {
            "engineering", "normalization", "algorithms", "tools", "platform",
            "system", "models", "datasets", "applications", "technologies"
        }:
            continue
        cleaned_tokens.append(clean)

    seen_canonical: Dict[str, str] = {}
    for token in cleaned_tokens:
        norm = token.lower()
        canon = skill_engine.normalize_skill(norm) if skill_engine else norm

        if canon in CANONICAL_DISPLAY_NAMES:
            disp = CANONICAL_DISPLAY_NAMES[canon]
        elif norm in CANONICAL_DISPLAY_NAMES:
            disp = CANONICAL_DISPLAY_NAMES[norm]
        else:
            if token.isupper() and len(token) <= 4:
                disp = token
            elif any(c.isupper() for c in token[1:]):
                disp = token
            else:
                disp = token.title()

        primary_key = canon if canon else norm
        if primary_key not in seen_canonical:
            seen_canonical[primary_key] = disp
        else:
            if disp in CANONICAL_DISPLAY_NAMES.values():
                seen_canonical[primary_key] = disp

    # Deduplicate by lowercase display representation to prevent any alias repetition
    deduped_display: Dict[str, str] = {}
    for val in seen_canonical.values():
        key = val.lower()
        if key not in deduped_display:
            deduped_display[key] = val
        elif val in CANONICAL_DISPLAY_NAMES.values():
            deduped_display[key] = val

    results = list(deduped_display.values())
    results_lower = [r.lower() for r in results]
    final_techs: List[str] = []
    for r in results:
        r_l = r.lower()
        if r_l in {"data", "engineering", "analysis"} and any(
            other != r_l and r_l in other for other in results_lower
        ):
            continue
        final_techs.append(r)

    return sorted(final_techs, key=lambda x: x.lower())


def normalize_date_token(token: str) -> str:
    """Normalizes abbreviations like 'Feb 26' -> 'Feb 2026', 'July 25' -> 'July 2025'."""
    clean = token.strip(".,;()[] ")
    clean = re.sub(rf"({MONTHS_PATTERN})(\d{{2,4}})", r"\1 \2", clean, flags=re.I)
    m4 = re.search(r"([A-Za-z]+)?\.?\s*(20\d{2}|19\d{2})\b", clean, re.I)
    if m4:
        month = m4.group(1)
        yr = m4.group(2)
        return f"{month.title()} {yr}" if month else yr

    m2 = re.search(r"([A-Za-z]+)?\.?\s*(?:\'|\b)?(\d{2})$", clean, re.I)
    if m2:
        month = m2.group(1)
        yr = int(m2.group(2))
        full_yr = f"20{yr:02d}" if yr <= 40 else f"19{yr:02d}"
        return f"{month.title()} {full_yr}" if month else full_yr

    if clean.lower() in ("present", "current", "ongoing", "now", "till date"):
        return "Present"
    return clean.title()


def extract_dates(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
    """Extracts date range string, start date, end date, and ongoing boolean."""
    if not text:
        return None, None, None, False
    # Normalize cases like Jan26 -> Jan 26
    norm = re.sub(rf"({MONTHS_PATTERN})(\d{{2,4}})", r"\1 \2", text, flags=re.I)
    m = DATE_RANGE_REGEX.search(norm)
    if m:
        start = normalize_date_token(m.group(1))
        end = normalize_date_token(m.group(2))
        is_ongoing = bool(re.search(r"(?i)\b(?:present|current|ongoing|now|till\s+date)\b", m.group(2)))
        return f"{start} – {end}", start, end, is_ongoing
    return None, None, None, False


def is_pure_date(text: str) -> bool:
    """Returns True if the line consists essentially of only a date or date range."""
    full_d, s, e, _ = extract_dates(text)
    if full_d:
        norm = re.sub(rf"({MONTHS_PATTERN})(\d{{2,4}})", r"\1 \2", text, flags=re.I)
        rem = DATE_RANGE_REGEX.sub("", norm)
        rem = re.sub(r"[()\[\]|\-–—~,.\s\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o]", "", rem)
        return len(rem) <= 4
    return False


def identify_section_header(line: str) -> Optional[str]:
    """Deterministically identifies section headers across uppercase and mixed case formats."""
    clean = re.sub(r"^[#*•❖◆■\-=_~:|\s]+", "", line).strip()
    clean = re.sub(r"[:\-=_~|\s]+$", "", clean).strip()
    if not clean or len(clean) > 40 or len(clean) < 3:
        return None
    lower = clean.lower()
    for sec, patterns in SECTION_PATTERNS.items():
        for pat in patterns:
            if re.match(pat, lower):
                return sec
    return None


def split_resume_into_sections(text: str) -> Dict[str, List[str]]:
    """Partitions resume text into labeled sections based on strict heading transitions."""
    sections: Dict[str, List[str]] = {}
    current_sec = "header"
    sections[current_sec] = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        detected_sec = identify_section_header(line)
        if detected_sec:
            current_sec = detected_sec
            if current_sec not in sections:
                sections[current_sec] = []
        else:
            sections[current_sec].append(line)
    return sections


def clean_section_lines(raw_lines: List[str]) -> List[str]:
    """
    Cleans raw section lines:
    1. Removes empty or bullet-character-only lines (e.g. standalone bullets \\uf0b7, \\u2022).
    2. Merges wrapped sentence continuations from PDF line wrapping while respecting dates, links, and titles.
    """
    non_empty = []
    bullet_chars_only = re.compile(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—\s]+$")
    for l in raw_lines:
        s = l.strip()
        if not s or bullet_chars_only.match(s):
            continue
        non_empty.append(s)

    joined: List[str] = []
    wrap_endings = {
        "the", "and", "to", "with", "for", "of", "in", "by", "from", "a", "an", "or",
        "detect", "using", "learning", "airplane", "through", "performing", "implementing"
    }

    for line in non_empty:
        if joined:
            prev = joined[-1]
            prev_last_word = prev.split()[-1].lower().strip(".,:;()[]") if prev.split() else ""
            is_special = bool(
                is_pure_date(line) or
                re.match(r"(?i)^(?:github|repo|https?://|tech\s+stack|tools|technologies)\b", line) or
                re.match(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—]\s*", line)
            )

            is_continuation = (
                not is_special and
                not prev.endswith(('.', ';', ':')) and
                (line[0].islower() or prev_last_word in wrap_endings or (
                    len(line.split()) <= 3 and
                    not line.isupper() and
                    not any(k in line.lower() for k in ["intern", "training", "engineer", "developer", "analyst", "tech"])
                ))
            )

            if is_continuation:
                joined[-1] = prev + " " + line
                continue

        joined.append(line)
    return joined


class ExperienceAnalyzer:
    """
    Analyzes professional experience alignment and extracts evidence of projects, internships,
    and achievements with strict section and record boundaries.
    """

    def __init__(self):
        self.skill_engine = SkillEngine()

    def _extract_tech_and_focus(self, text: str) -> List[str]:
        """Extracts technical skills and capitalized technical focus domains from text."""
        skills = {s for s in self.skill_engine.extract_skills(text)}
        # Comma-separated technical terms
        for chunk in re.split(r"[,|;]+", text):
            clean = chunk.strip().strip("•-*– ")
            if 1 <= len(clean.split()) <= 4 and 3 <= len(clean) <= 40 and not clean.endswith("."):
                lower = clean.lower()
                if any(w in lower for w in [
                    "detection", "analysis", "learning", "network", "security", "forest",
                    "evaluation", "visualization", "preprocessing", "engineering", "model",
                    "intelligence", "vision", "tracking", "gesture", "map", "svg", "api",
                    "classification", "system", "pipeline"
                ]):
                    skills.add(clean)
        return canonicalize_tech_list(list(skills), self.skill_engine)

    def detect_projects(
        self,
        resume_text: str,
        sections: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict]:
        """
        Extracts structured project records with strict boundary controls.
        Does NOT create projects from dates, tech stack lines, bullet descriptions,
        or section headings.
        """
        if not resume_text:
            return []

        if sections is None:
            sections = split_resume_into_sections(resume_text)

        raw_project_lines = sections.get("projects", [])
        if not raw_project_lines:
            raw_project_lines = resume_text.split("\n")

        project_lines = clean_section_lines(raw_project_lines)

        projects: List[Dict] = []
        current: Optional[Dict] = None

        action_verbs = {
            "developed", "built", "designed", "created", "implemented", "engineered",
            "trained", "evaluated", "deployed", "integrated", "constructed", "architected",
            "analyzed", "conducted", "enabled", "maintained", "formatted", "used", "utilized"
        }

        for i, raw_line in enumerate(project_lines):
            line = raw_line.strip()
            if not line:
                continue

            lower_line = line.lower().strip("#*-•: ")
            sec = identify_section_header(line)
            if sec and sec != "projects":
                break
            if lower_line in EXCLUDED_SECTION_HEADERS:
                continue

            # 1. Tech Stack line attaches to current project
            tech_match = re.match(
                r"(?i)^(?:tech(?:nology|nologies)?\s*stack|technologies|tools(?:\s+used)?|built\s+with|key\s+technologies|skills\s+used|tools)\s*[:\-]\s*(.+)$",
                line
            )
            if tech_match:
                raw_techs = tech_match.group(1)
                tech_list = [t.strip().rstrip('.') for t in re.split(r"[,|;/]+", raw_techs) if t.strip()]
                if current:
                    current["technologies"] = sorted(list(set(current.get("technologies", []) + tech_list)))
                continue

            # 2. Date line attaches to current project
            if is_pure_date(line):
                if current and not current.get("dates"):
                    d_str, s_d, e_d, is_on = extract_dates(line)
                    current["dates"] = d_str
                    current["start_date"] = s_d
                    current["end_date"] = e_d
                continue

            # 3. GitHub / external link attaches to current project
            gh = GITHUB_URL_REGEX.search(line)
            url_match = URL_REGEX.search(line)
            is_link_line = bool(
                re.match(r"(?i)^(?:github|repo|repository|code|link|url|demo|website)\s*[:\-]", line)
                or (gh and len(line.split()) <= 4)
                or (url_match and len(line.split()) <= 4)
            )
            if is_link_line:
                if current:
                    target_url = gh.group(0) if gh else (url_match.group(0) if url_match else None)
                    if target_url:
                        if target_url not in current.get("links", []):
                            current["links"].append(target_url)
                        if not current.get("github_url") and gh:
                            current["github_url"] = target_url
                continue

            # 4. Description label attaches to current project
            if re.match(r"(?i)^(?:description|overview|details|summary|note)\s*[:\-]", line):
                if current:
                    clean_desc = re.sub(r"(?i)^(?:description|overview|details|summary|note)\s*[:\-]\s*", "", line).strip()
                    if clean_desc:
                        current["description_snippets"].append(clean_desc)
                continue

            clean_line = re.sub(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—\s]+", "", line).strip()
            words = clean_line.split()
            first_w = words[0].lower().strip(".,:;•*") if words else ""
            starts_with_action = first_w in action_verbs

            next_is_date = False
            if i + 1 < len(project_lines):
                nxt = project_lines[i+1].strip()
                if is_pure_date(nxt):
                    next_is_date = True

            # 5. Project title candidate
            is_title = (
                (next_is_date or not starts_with_action) and
                (2 <= len(words) <= 12) and
                (4 <= len(clean_line) <= 85) and
                not clean_line.endswith(('.', ';', ':')) and
                not bool(re.match(r"(?i)^(?:github|repo|http|demo|website)", clean_line)) and
                first_w not in {"bachelor", "master", "intermediate", "matriculation", "education", "internship", "certifications", "achievements"}
            )

            if is_title:
                if current:
                    projects.append(current)

                d_str, s_d, e_d, on = extract_dates(clean_line)
                if d_str:
                    clean_line = DATE_RANGE_REGEX.sub("", clean_line).strip(" |-,()[]")

                # Strip repository metadata, URLs, and labels from project title
                clean_title = re.sub(
                    r"(?i)\s*(?:\|\s*|\s*-\s*|\s*–\s*|\s*—\s*)?(?:github(?:\.com)?|repo|repository|code|demo|website|url)\s*[:\-]?\s*(?:https?://\S+)?",
                    "",
                    clean_line
                ).strip(" |-,()[]")
                clean_title = re.sub(r"https?://\S+|www\.\S+", "", clean_title).strip(" |-,()[]")
                if not clean_title or len(clean_title) < 2:
                    clean_title = clean_line

                p_type = "Academic/Student Project" if any(w in clean_title.lower() for w in ["course", "class", "thesis", "capstone", "lab"]) else "Technical Project"
                current = {
                    "project_title": clean_title,
                    "title": clean_title,
                    "start_date": s_d,
                    "end_date": e_d,
                    "dates": d_str,
                    "description": "",
                    "technologies": [],
                    "links": [gh.group(0)] if gh else [],
                    "github_url": gh.group(0) if gh else None,
                    "evidence_source": line,
                    "type": p_type,
                    "description_snippets": []
                }
            elif current:
                current["description_snippets"].append(clean_line)

        if current:
            projects.append(current)

        for p in projects:
            p["description"] = " ".join(p["description_snippets"])
            p["technologies"] = canonicalize_tech_list(p.get("technologies", []), self.skill_engine)

        deduped: List[Dict] = []
        seen_titles: Set[str] = set()
        for p in projects:
            t_norm = p["project_title"].strip().lower()
            if t_norm not in seen_titles and len(t_norm) >= 3 and t_norm not in EXCLUDED_SECTION_HEADERS:
                seen_titles.add(t_norm)
                deduped.append(p)

        return deduped

    def detect_internships(
        self,
        resume_text: str,
        sections: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict]:
        """
        Extracts structured internship and industrial training entries.
        Recognizes organization, program/position, date ranges, ongoing status,
        and technical focus areas.
        """
        if not resume_text:
            return []

        if sections is None:
            sections = split_resume_into_sections(resume_text)

        raw_intern_lines = sections.get("internships", [])
        if not raw_intern_lines:
            exp_lines = sections.get("experience", [])
            has_intern_mention = any(
                re.search(r"(?i)\b(?:intern(?:ship)?|virtual\s+internship|industrial\s+training)\b", l)
                for l in exp_lines
            )
            if has_intern_mention:
                raw_intern_lines = exp_lines

        if not raw_intern_lines:
            for sec_name, sec_lines in sections.items():
                if sec_name in ("education", "skills", "certifications", "contact"):
                    continue
                if any(re.search(r"(?i)\b(?:intern(?:ship)?|virtual\s+internship|industrial\s+training)\b", l) for l in sec_lines):
                    raw_intern_lines = sec_lines
                    break

        if not raw_intern_lines:
            return []

        intern_lines = clean_section_lines(raw_intern_lines)

        internships: List[Dict] = []
        current: Optional[Dict] = None

        for raw_line in intern_lines:
            line = raw_line.strip()
            if not line:
                continue

            lower_line = line.lower().strip("#*-•: ")
            sec = identify_section_header(line)
            if sec and sec not in ("internships", "experience"):
                break
            if lower_line in EXCLUDED_SECTION_HEADERS:
                continue

            # 1. Tech stack / Tools line attaches to current internship
            tech_match = re.match(r"(?i)^(?:tools|technologies|tech\s+stack|environment)\s*[:\-]\s*(.*)", line)
            if tech_match:
                if current:
                    tools_text = tech_match.group(1)
                    tool_items = [t.strip().rstrip('.') for t in re.split(r"[,|;/]+", tools_text) if t.strip()]
                    current["technologies"] = sorted(list(set(current.get("technologies", []) + tool_items)))
                continue

            d_str, s_d, e_d, is_on = extract_dates(line)

            # 2. Pure date range attaches to current internship
            if is_pure_date(line):
                if current and not current.get("dates"):
                    current["dates"] = d_str
                    current["start_date"] = s_d
                    current["end_date"] = e_d
                    current["is_ongoing"] = is_on
                continue

            # 3. Bullet points / responsibility lines
            starts_with_bullet = bool(re.match(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—]\s*", line))
            words = line.split()
            first_w = words[0].lower().strip(".,:;•*") if words else ""
            starts_with_action = first_w in {
                "currently", "participating", "learning", "working", "developing", "evaluating",
                "implemented", "built", "trained", "applied", "performed", "optimized", "documented",
                "assisted", "supported", "collaborated", "managed", "designed"
            }
            is_bullet = starts_with_bullet or starts_with_action or (
                current is not None and not d_str and (
                    len(words) >= 8 or line.endswith('.') or line[0].islower()
                )
            )

            if is_bullet:
                if current:
                    clean_bullet = re.sub(r"^[\uf0b7\u2022\u25cf\u25aa\u25b6\u25c6\u27a4\u2765\u2023\u2043•*o\-–—\s]+", "", line).strip()
                    current["responsibilities"].append(clean_bullet)
                    techs = self._extract_tech_and_focus(clean_bullet)
                    current["technologies"] = sorted(list(set(current.get("technologies", []) + techs)))
                continue

            # Check if this line is a role/program for current internship
            is_position = bool(re.search(r"(?i)\b(?:intern(?:ship)?|trainee|apprentice|fellow|assistant|engineer|developer|analyst)\b", line))
            if current and is_position and not current.get("position") and not d_str:
                current["position"] = line.strip()
                if "virtual" in line.lower():
                    current["internship_type"] = "Virtual Internship"
                elif "industrial" in line.lower():
                    current["internship_type"] = "Industrial Training"
                elif "research" in line.lower():
                    current["internship_type"] = "Research Internship"
                continue

            # 4. Organization / Role / Program line
            line_clean = line
            if d_str:
                norm_line = re.sub(rf"({MONTHS_PATTERN})(\d{{2,4}})", r"\1 \2", line, flags=re.I)
                m_date = DATE_RANGE_REGEX.search(norm_line)
                if m_date:
                    line_clean = norm_line.replace(m_date.group(0), "").strip(" |-,()[]")
                    line_clean = re.sub(r"\s{2,}", " ", line_clean).strip()

            parts = [p.strip() for p in re.split(r"[–—|]", line_clean) if p.strip()]
            role_kw = re.compile(r"(?i)\b(?:intern(?:ship)?|trainee|apprentice|fellow|assistant|engineer|developer|analyst|associate|specialist|lead|architect)\b")
            org_kw = re.compile(r"(?i)\b(?:foundation|technologies|solutions|services|systems|corp|inc|ltd|labs?|institute|university|college|company|center|centre|group)\b")

            org = None
            pos = None
            prog = None

            if len(parts) >= 2:
                p0, p1 = parts[0], parts[1]
                p0_is_role = bool(role_kw.search(p0)) and not bool(org_kw.search(p0))
                p1_is_role = bool(role_kw.search(p1))

                if p0_is_role and not p1_is_role:
                    pos = p0
                    org = p1
                elif not p0_is_role and p1_is_role:
                    org = p0
                    pos = p1
                else:
                    org = p0
                    pos = p1

                if len(parts) > 2:
                    prog = parts[2]
            elif parts:
                p0 = parts[0]
                if bool(role_kw.search(p0)) and not bool(org_kw.search(p0)):
                    pos = p0
                    org = None
                else:
                    org = p0
                    pos = None

            # Clean any remaining date traces from pos
            if pos:
                pos = pos.strip(" |-,()[]")
                if "(" in pos and ")" not in pos:
                    pos = pos + ")"

            i_type = "Internship"
            type_target = f"{pos or ''} {org or ''}".lower()
            if "virtual" in type_target:
                i_type = "Virtual Internship"
            elif "industrial" in type_target:
                i_type = "Industrial Training"
            elif "research" in type_target:
                i_type = "Research Internship"

            if current:
                internships.append(current)

            current = {
                "organization": org,
                "role": pos,
                "position": pos,
                "program": prog,
                "internship_type": i_type,
                "start_date": s_d,
                "end_date": e_d,
                "dates": d_str,
                "is_ongoing": is_on,
                "responsibilities": [],
                "technologies": [],
                "evidence_source": line
            }

        if current:
            internships.append(current)

        for i in internships:
            i["technologies"] = canonicalize_tech_list(i.get("technologies", []), self.skill_engine)

        deduped: List[Dict] = []
        seen_keys: Set[str] = set()
        for i in internships:
            key_name = (i.get("organization") or i.get("position") or i.get("role") or "").strip().lower()
            if key_name and key_name not in seen_keys and len(key_name) >= 3 and key_name not in EXCLUDED_SECTION_HEADERS:
                seen_keys.add(key_name)
                deduped.append(i)

        return deduped

    def analyze_experience(
        self,
        resume_text: Optional[str],
        job_required_years: Optional[float] = None
    ) -> Dict:
        """
        Evaluates explicit experience duration, distinguishes full-time employment, internships,
        and student projects, ensuring honest reporting without false 'not established' messages
        when internships exist.
        """
        if not resume_text or not isinstance(resume_text, str) or not resume_text.strip():
            return {
                "resume_years_exp": 0.0,
                "has_resume_exp": False,
                "resume_exp_display": "Professional experience not established",
                "job_required_years": job_required_years or 0.0,
                "has_job_exp": bool(job_required_years and job_required_years > 0.0),
                "job_req_display": f"{job_required_years} yrs" if job_required_years else "No explicit minimum identified",
                "experience_gap_years": -job_required_years if job_required_years else 0.0,
                "alignment_status": "Professional experience not established",
                "meets_experience_requirement": False if job_required_years else True,
                "detected_projects": [],
                "projects": [],
                "projects_count": 0,
                "detected_internships": [],
                "internships": [],
                "internships_count": 0,
                "professional_experience": [],
                "experience_summary": {
                    "has_full_time": False,
                    "full_time_years": 0.0,
                    "has_internships": False,
                    "internships_count": 0,
                    "has_projects": False,
                    "projects_count": 0,
                    "primary_classification": "Experience not established",
                    "display_summary": "Professional experience not established"
                },
                "is_student_or_early_career": True
            }

        # 1. Section-aware partitioning
        sections = split_resume_into_sections(resume_text)

        # 2. Extract projects and internships
        projects = self.detect_projects(resume_text, sections=sections)
        internships = self.detect_internships(resume_text, sections=sections)

        # 3. Explicit experience years
        resume_exp = extract_explicit_experience_years(resume_text)
        has_resume_exp = resume_exp > 0.0
        has_job_exp = bool(job_required_years is not None and job_required_years > 0.0)

        has_internships = len(internships) > 0
        has_full_time = has_resume_exp and resume_exp > 0.0

        # 4. Determine display labels and alignment cleanly
        if has_internships and not has_full_time:
            resume_display = "Internship experience identified; full-time employment not established."
            if not has_job_exp:
                alignment = "Internship experience identified; full-time employment not established."
                meets_req = True
                gap = 0.0
            else:
                alignment = f"Internship experience identified; full-time employment not established (Job requests {job_required_years} yrs)"
                meets_req = False
                gap = -job_required_years
            primary_classification = "Internships"
        elif has_full_time:
            resume_display = f"{resume_exp} yrs"
            if not has_job_exp:
                alignment = f"Candidate documents {resume_exp} yrs (no minimum requested)"
                meets_req = True
                gap = resume_exp
            else:
                gap = round(resume_exp - job_required_years, 1)
                if gap >= 0:
                    alignment = f"Meets/Exceeds Requirement (+{gap} yrs)"
                    meets_req = True
                else:
                    alignment = f"Experience Deficit ({abs(gap)} yrs below required)"
                    meets_req = False
            primary_classification = "Full-time professional employment"
        elif len(projects) > 0:
            resume_display = "Academic/project experience documented; full-time employment not established."
            alignment = "Academic/project experience documented; full-time employment not established." if not has_job_exp else f"Experience requirement not verified (Job requests {job_required_years} yrs)"
            meets_req = True if not has_job_exp else False
            gap = 0.0 if not has_job_exp else -job_required_years
            primary_classification = "Academic projects"
        else:
            resume_display = "Professional experience not established"
            alignment = "No explicit experience requirement stated" if not has_job_exp else f"Experience requirement not verified (Job requests {job_required_years} yrs)"
            meets_req = True if not has_job_exp else False
            gap = 0.0 if not has_job_exp else -job_required_years
            primary_classification = "Experience not established"

        job_display = f"{job_required_years} yrs" if has_job_exp else "No explicit minimum identified"

        lower = resume_text.lower()
        is_student = (
            any(k in lower for k in ["bachelor", "student", "undergraduate", "gpa", "coursework", "intern", "internship"]) and
            (resume_exp <= 2.0 or not has_resume_exp)
        )

        experience_summary = {
            "has_full_time": has_full_time,
            "full_time_years": resume_exp if has_full_time else 0.0,
            "has_internships": has_internships,
            "internships_count": len(internships),
            "has_projects": len(projects) > 0,
            "projects_count": len(projects),
            "primary_classification": primary_classification,
            "display_summary": resume_display,
            "tenure_status": alignment
        }

        return {
            "resume_years_exp": resume_exp if has_resume_exp else 0.0,
            "has_resume_exp": has_resume_exp,
            "resume_exp_display": resume_display,
            "job_required_years": job_required_years if has_job_exp else 0.0,
            "has_job_exp": has_job_exp,
            "job_req_display": job_display,
            "experience_gap_years": gap,
            "alignment_status": alignment,
            "meets_experience_requirement": meets_req,
            "detected_projects": projects,
            "projects": projects,
            "projects_count": len(projects),
            "detected_internships": internships,
            "internships": internships,
            "internships_count": len(internships),
            "professional_experience": [],
            "experience_summary": experience_summary,
            "is_student_or_early_career": is_student
        }

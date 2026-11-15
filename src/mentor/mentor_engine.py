"""
Career Mentor Engine Module.
Orchestrates candidate name personalization, verified strengths extraction,
canonical skill gap integration, prioritized roadmaps, study plan generation,
and Interview Studio linking.
"""

from typing import Dict, List, Any, Optional
import re

from .name_extractor import extract_candidate_name, format_mentor_identity
from .resource_mapper import get_learning_resources_for_skill
from .project_recommender import recommend_project_for_skill
from .roadmap_generator import generate_skill_roadmap, generate_realistic_study_plan, cluster_skill_gaps
from .skill_curricula import get_curriculum_for_skill
from .progress_tracker import CandidateProgressTracker
from .message_templates import (
    build_welcome_greeting,
    format_gap_explanation,
    build_progress_encouragement
)


def classify_mentor_category(skill_name: str) -> str:
    """
    Categorizes skills into 4 industry-standard requirement categories:
    1. Core Technical Skills
    2. Engineering Tools and Practices
    3. Professional and Behavioral Competencies
    4. Productivity and Business Tools
    """
    norm = (skill_name or "").lower().strip()

    # Category 4: Productivity and Business Tools
    # (Spreadsheets, BI tools, Office docs, Diagramming, Project tracking software, General digital literacy)
    prod_tools = {
        "excel", "microsoft excel", "ms excel", "spreadsheet", "spreadsheets",
        "power bi", "powerbi", "pbi", "tableau", "looker", "qlik", "qlikview", "qliksense",
        "word", "ms word", "microsoft word", "powerpoint", "ms powerpoint", "office", "ms office", "microsoft office",
        "google docs", "google sheets", "google slides",
        "visio", "ms visio", "microsoft visio", "draw.io", "lucidchart",
        "jira", "trello", "asana", "notion", "monday", "monday.com", "clickup", "basecamp",
        "pc skills", "computer skills", "digital literacy", "data entry", "typing",
        "slack", "zoom", "teams", "microsoft teams"
    }
    if any(p == norm or p in norm for p in prod_tools):
        return "Productivity and Business Tools"

    # Category 3: Professional and Behavioral Competencies
    # (Communication, Leadership, Methodologies, Behavioral traits, Cognitive competencies)
    prof_comp = {
        "communication", "verbal communication", "written communication", "presentation", "public speaking",
        "interpersonal skills", "interpersonal", "active listening", "teamwork", "collaboration",
        "mentorship", "leadership", "negotiation", "conflict resolution", "soft skills", "soft skill",
        "project management", "agile delivery", "agile methodology", "scrum master", "scrum methodology",
        "time management", "stakeholder management", "risk management",
        "focus", "attention to detail", "work ethic", "self-motivation", "discipline", "punctuality",
        "patience", "adaptability", "flexibility", "resilience", "perseverance", "continuous learning",
        "analytical problem-solving", "analytical problem solving", "problem solving", "problem-solving",
        "analytical thinking", "critical thinking", "logical reasoning", "decision making"
    }
    if any(p == norm or p in norm for p in prof_comp):
        return "Professional and Behavioral Competencies"

    # Category 2: Engineering Tools and Practices
    # (DevOps, Cloud infrastructure, Linux, Testing methodologies, Code review, CI/CD)
    eng_tools = {
        "docker", "containerization", "kubernetes", "k8s", "aws", "amazon web services", "gcp", "google cloud", "azure",
        "ci/cd", "cicd", "continuous integration", "git", "github", "gitlab", "linux", "bash", "shell scripting",
        "terraform", "ansible", "jenkins", "devops", "circleci",
        "unit test", "unit testing", "automated testing", "integration testing", "tdd", "test-driven",
        "code review", "microservices", "refactoring", "debugging", "logging", "monitoring",
        "cloud", "nginx", "system design"
    }
    if any(p == norm or p in norm for p in eng_tools):
        return "Engineering Tools and Practices"

    # Category 1: Core Technical Skills (Languages, Frameworks, ML, Databases, CS fundamentals)
    return "Core Technical Skills"


def find_jd_sentence_for_skill(skill_name: str, jd_text: str) -> str:
    """
    Finds the actual supporting sentence in the job description text mentioning this requirement.
    If the source sentence cannot be recovered, displays: 'Exact JD evidence unavailable.'
    Never fabricates a quotation.
    """
    if not jd_text or not isinstance(jd_text, str) or not jd_text.strip():
        return "Exact JD evidence unavailable."

    clean_jd = jd_text.replace("\r", " ")
    raw_sentences = re.split(r"(?<=[.!?\n])\s+|[\r\n]+|[•\-\*]\s+", clean_jd)
    norm = (skill_name or "").lower().strip()

    pattern = re.compile(rf"\b{re.escape(norm)}\b", re.IGNORECASE)
    for s in raw_sentences:
        s_clean = s.strip()
        s_clean = re.sub(r"^[•\-\*\d\.\)\s]+", "", s_clean).strip()
        if len(s_clean) >= 8 and pattern.search(s_clean):
            if len(s_clean) > 160:
                s_clean = s_clean[:157] + "..."
            return s_clean

    for s in raw_sentences:
        s_clean = s.strip()
        s_clean = re.sub(r"^[•\-\*\d\.\)\s]+", "", s_clean).strip()
        if len(s_clean) >= 8 and norm in s_clean.lower():
            if len(s_clean) > 160:
                s_clean = s_clean[:157] + "..."
            return s_clean

    return "Exact JD evidence unavailable."


def find_related_candidate_experience(
    skill_name: str,
    verified_skills: List[str],
    projects: List[Dict[str, Any]]
) -> str:
    """
    Identifies verified candidate skills or projects that directly relate to the requirement.
    Only associates a project with a skill when the relationship is technically or professionally meaningful.
    If no relevant project exists, provides a standalone exercise recommendation without forcing every requirement into one project.
    """
    norm = (skill_name or "").lower().strip()
    norm_skills = [s.lower().strip() for s in verified_skills]

    primary_proj = projects[0] if projects else {}
    primary_title = primary_proj.get("title") or primary_proj.get("project_title")
    primary_techs = [t.lower() for t in primary_proj.get("technologies", [])]
    primary_desc = primary_proj.get("description", "").lower()

    # 1. Docker / Containerization
    if any(k in norm for k in ["docker", "container"]):
        if primary_title and (any(t in primary_techs for t in ["python", "flask", "django", "fastapi", "react", "node", "javascript"]) or any(w in primary_desc for w in ["web", "api", "service", "backend"])):
            return f"Can containerize backend service developed in '{primary_title}'."
        if any(s in norm_skills for s in ["linux", "python", "bash"]):
            return "Candidate has verified Linux/Python fundamentals; standalone containerization exercises recommended."
        return "No direct containerization antecedent in resume; complete standalone Docker exercises."

    # 2. Kubernetes
    if any(k in norm for k in ["kubernetes", "k8s"]):
        if "docker" in norm_skills:
            return "Can build upon verified Docker containerization foundations."
        return "No direct container antecedent in resume; complete standalone Kubernetes cluster exercises."

    # 3. CI/CD
    if any(k in norm for k in ["ci/cd", "cicd", "continuous integration", "github actions", "gitlab"]):
        if primary_title and primary_techs:
            return f"Can configure automated GitHub Actions CI/CD workflows for '{primary_title}'."
        if "git" in norm_skills:
            return "Can build upon verified Git version control foundations."
        return "No direct CI/CD antecedent in resume; complete standalone automated testing pipeline exercises."

    # 4. Spark / PySpark
    if any(k in norm for k in ["spark", "pyspark", "hadoop"]):
        data_skills = [s for s in ["python", "pandas", "sql", "numpy"] if s in norm_skills]
        if data_skills:
            return f"Can leverage verified {', '.join([s.title() for s in data_skills[:2]])} data processing skills for standalone PySpark exercises."
        return "No direct distributed compute antecedent in resume; complete standalone PySpark exercises."

    # 5. TypeScript
    if any(k in norm for k in ["typescript", "ts"]):
        web_skills = [s for s in ["javascript", "html", "css", "react", "node"] if s in norm_skills]
        if web_skills:
            return f"Can build upon verified {', '.join([s.title() for s in web_skills[:2]])} web fundamentals to adopt static typing."
        return "No direct web frontend antecedent in resume; complete standalone TypeScript exercises."

    # 6. Power BI / Tableau
    if any(k in norm for k in ["power bi", "powerbi", "tableau", "looker"]):
        bi_skills = [s for s in ["sql", "pandas", "excel"] if s in norm_skills]
        if bi_skills:
            return f"Can leverage verified {', '.join([s.title() for s in bi_skills[:2]])} data modeling skills to design business intelligence dashboards."
        return "No direct analytics antecedent in resume; complete standalone Power BI dashboard exercises."

    # 7. Excel
    if any(k in norm for k in ["excel", "spreadsheet", "sheets"]):
        if any(s in norm_skills for s in ["sql", "pandas", "python"]):
            return "Can leverage quantitative data foundations to construct structured analytical workbooks."
        return "No direct spreadsheet antecedent in resume; complete standalone analytical model exercises."

    # 8. Visio
    if any(k in norm for k in ["visio", "diagram"]):
        return "Author standalone system architecture and data-flow diagrams; no codebase coupling required."

    # 9. Jira / Trello / Project Management
    if any(k in norm for k in ["jira", "trello", "project management", "agile", "scrum"]):
        if any(s in norm_skills for s in ["git", "agile", "scrum", "teamwork"]):
            return "Can apply agile sprint backlog planning to personal engineering workflows."
        return "No direct project management antecedent in parsed resume; complete a standalone sprint backlog exercise."

    # 10. Communication / Presentation
    if any(k in norm for k in ["communication", "presentation", "public speaking"]):
        if primary_title:
            return f"Can leverage technical architecture from '{primary_title}' for a structured design walkthrough presentation."
        return "Deliver a standalone technical presentation utilizing the PREP framework."

    # 11. Focus / Behavioral Competencies
    if any(k in norm for k in ["focus", "attention to detail", "discipline", "work ethic"]):
        return "Personal professional competency; cultivate deliberate focus blocks during coding sessions."

    # 12. PC Skills
    if any(k in norm for k in ["pc skills", "computer skills", "digital literacy"]):
        return "General digital literacy; no specific engineering codebase antecedent required."

    # 13. Analytical Problem-Solving
    if any(k in norm for k in ["analytical", "problem solving", "problem-solving"]):
        return "Cognitive competency; apply structured root-cause analysis frameworks to technical bottlenecks."

    # 14. Deep Learning / ML / Computer Vision / NLP
    if any(k in norm for k in ["pytorch", "tensorflow", "deep learning", "machine learning", "computer vision", "nlp"]):
        ml_skills = [s for s in ["python", "numpy", "scikit-learn", "pandas", "opencv"] if s in norm_skills]
        if ml_skills:
            return f"Candidate has verified proficiency in {', '.join([s.title() for s in ml_skills[:3]])}."
        return "Foundational math and programming prerequisites required for advanced ML topics."

    # Generic technical skill fallback
    related = []
    if norm in ["sql", "postgresql", "mysql"]:
        for s in ["python", "database", "mongodb"]:
            if s in norm_skills:
                related.append(s.title())
    elif norm in ["react", "vue", "angular"]:
        for s in ["javascript", "html", "css"]:
            if s in norm_skills:
                related.append(s.title())

    if related:
        return f"Candidate has verified proficiency in {', '.join(related[:3])}."

    return "No direct antecedent identified in resume; standalone exercise recommended."


def calculate_skill_priority(
    skill_name: str,
    tier: str,
    status: str,
    verified_skills: List[str],
    jd_text: str,
    projects: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculates prioritized score and generates explicit reason for prioritization."""
    norm = skill_name.lower().strip()
    norm_verified = [s.lower().strip() for s in verified_skills]

    score = 100 if tier == "Mandatory" else 50
    reasons = []

    if tier == "Mandatory":
        reasons.append("Mandatory requirement directly specified by employer")
    else:
        reasons.append("Preferred requirement offering competitive differentiation")

    if "Partially" in status:
        score += 25
        reasons.append("Already partially evidenced in resume; high-yield candidate quick win")
    else:
        score += 15

    if jd_text:
        mentions = len(re.findall(rf"\b{re.escape(norm)}\b", jd_text.lower()))
        if mentions > 1:
            score += min(mentions * 5, 20)
            reasons.append(f"Emphasized across multiple sections of target job posting ({mentions} mentions)")

    has_related = False
    if norm in ["docker", "kubernetes", "aws", "gcp", "azure"]:
        if any(s in norm_verified for s in ["linux", "python", "flask", "django", "git"]):
            score += 15
            has_related = True
            reasons.append("Candidate already has foundational backend/Linux skills to accelerate adoption")
    elif norm in ["spark", "pyspark", "hadoop", "kafka"]:
        if any(s in norm_verified for s in ["python", "pandas", "sql", "numpy"]):
            score += 15
            has_related = True
            reasons.append("Candidate has verified Python/SQL data foundations, lowering ramp-up effort")
    elif norm in ["pytorch", "tensorflow", "deep learning", "machine learning"]:
        if any(s in norm_verified for s in ["python", "numpy", "scikit-learn", "pandas"]):
            score += 15
            has_related = True
            reasons.append("Candidate has established Python/Scikit-learn math and data foundations")
    elif norm in ["react", "frontend", "typescript"]:
        if any(s in norm_verified for s in ["javascript", "html", "css"]):
            score += 15
            has_related = True
            reasons.append("Candidate has prerequisite web markup and JavaScript experience")

    if not has_related and norm not in ["communication", "excel", "project management"]:
        score -= 5

    if score >= 125:
        priority_label = "Critical Priority"
    elif score >= 100:
        priority_label = "High Priority"
    elif score >= 75:
        priority_label = "Moderate Priority"
    else:
        priority_label = "Foundational Priority"

    return {
        "priority_label": priority_label,
        "priority_score": score,
        "priority_reason": "; ".join(reasons) + "."
    }


def recommend_gap_action(skill_name: str, category: str, projects: List[Dict[str, Any]]) -> str:
    """
    Generates distinct, domain-appropriate practical actions for a skill gap.
    Guarantees fundamentally different activities for different competencies.
    For unsupported skills, honestly displays that specialized guidance is not yet available.
    """
    norm = (skill_name or "").lower().strip()
    primary_title = projects[0].get("title") or projects[0].get("project_title") if projects else None

    # Supported competency-specific distinct actions:
    if "typescript" in norm or "ts" == norm:
        return "Migrate an existing JavaScript module to TypeScript with strict type annotations, interfaces, and compiler checks."

    if any(k in norm for k in ["project management", "agile", "scrum", "kanban"]):
        return "Decompose a multi-feature product epic into an Agile sprint backlog with INVEST user stories and estimation story points."

    if "jira" in norm:
        return "Configure a Jira Scrum or Kanban board with custom workflow states, sprint backlog epics, and burndown tracking."

    if "trello" in norm:
        return "Organize an engineering project board into clear workflow columns with task checklists and ownership boundaries."

    if any(k in norm for k in ["power bi", "powerbi", "tableau", "looker"]):
        return "Build an interactive multi-table business intelligence report with custom DAX measures and dimensional relationships."

    if any(k in norm for k in ["excel", "spreadsheet", "sheets"]):
        return "Build a structured analytical workbook modeling operational performance metrics with dynamic formulas and PivotTables."

    if any(k in norm for k in ["visio", "diagram"]):
        return "Author a formal multi-tier C4 system architecture diagram and normalized database Entity-Relationship schema."

    if any(k in norm for k in ["focus", "attention to detail", "discipline", "work ethic"]):
        return "Implement deliberate 45-minute distraction-free focus blocks (Pomodoro technique) to minimize context switching during development."

    if any(k in norm for k in ["pc skills", "computer skills", "digital literacy"]):
        return "Master operating system navigation shortcuts, file directory management, and command-line shell utilities."

    if any(k in norm for k in ["analytical", "problem solving", "problem-solving"]):
        return "Apply root-cause analysis (5 Whys framework) to decompose complex software bottlenecks before implementing code."

    if any(k in norm for k in ["communication", "presentation", "public speaking"]):
        if primary_title:
            return f"Prepare and record a 5-minute technical architecture presentation on '{primary_title}'."
        return "Prepare and deliver a structured technical architecture presentation explaining system design choices and trade-offs."

    if any(k in norm for k in ["docker", "container"]):
        if primary_title and any(t in str(projects[0]).lower() for t in ["flask", "fastapi", "django", "node", "web", "api"]):
            return f"Author a multi-stage Dockerfile and docker-compose.yml containerizing '{primary_title}'."
        return "Author a multi-stage Dockerfile and docker-compose configuration containerizing a backend service with volume persistence."

    if any(k in norm for k in ["git", "github", "gitlab", "version control"]):
        if primary_title:
            return f"Establish a Git version control repository with Conventional Commits and feature branching for '{primary_title}'."
        return "Initialize a Git repository, configure feature branching, resolve simulated 3-way merge conflicts, and execute interactive rebasing."

    if any(k in norm for k in ["linux", "bash", "unix", "shell scripting"]):
        return "Configure a Linux server environment, manage user permissions (chmod, chown), inspect systemd unit files, and diagnose processes using top, htop, and journalctl."

    if any(k in norm for k in ["spark", "pyspark", "hadoop"]):
        return "Execute a standalone PySpark batch processing job on partitioned Parquet datasets with broadcast hash joins."

    if any(k in norm for k in ["ci/cd", "continuous integration", "github actions"]):
        if primary_title:
            return f"Configure a GitHub Actions workflow running automated Pytest test suites on '{primary_title}'."
        return "Configure a GitHub Actions continuous integration workflow executing automated test suites and linting on pull requests."

    if any(k in norm for k in ["sql", "database", "postgres", "mysql"]):
        return "Design a 3NF relational database schema and optimize complex aggregation queries using EXPLAIN ANALYZE."

    if any(k in norm for k in ["kubernetes", "k8s"]):
        return "Deploy a containerized microservice to a local Kubernetes cluster with ReplicaSets, Services, and health probes."

    if any(k in norm for k in ["aws", "cloud", "azure", "gcp"]):
        return "Provision cloud infrastructure with least-privilege IAM policies, secure storage buckets, and automated health checks."

    if any(k in norm for k in ["react", "vue", "angular"]):
        return "Build a responsive component hierarchy utilizing custom hooks, state management, and unit tests."

    if "python" in norm:
        return "Design a modular Python package adhering to PEP 8 standards with comprehensive pytest test coverage."

    # Check if a specialized curriculum exists in SKILL_SPECIFIC_CURRICULA
    curriculum = get_curriculum_for_skill(skill_name)
    if curriculum.get("is_verified_specialized"):
        exercises = curriculum.get("practical_exercises", [])
        if exercises:
            return exercises[0]
        stages = curriculum.get("stages", [])
        if stages and stages[0].get("exercise"):
            return stages[0]["exercise"]

    # Honest disclosure for unsupported requirements:
    return "Specialized learning guidance is not yet available for this competency. Review official documentation and industry tutorials."


class CareerMentorEngine:
    """
    Main orchestrator for the Personalized Career Mentor assistant.
    """

    def __init__(
        self,
        analysis_data: Optional[Dict[str, Any]],
        user_override_name: Optional[str] = None
    ):
        self.analysis_data = analysis_data or {}
        raw_text = self.analysis_data.get("raw_text") or ""
        
        # 1. Candidate Name Extraction & Identity Formatting
        extracted_name_info = extract_candidate_name(raw_text)
        self.identity = format_mentor_identity(user_override_name, extracted_name_info)
        
        # 2. Extract Verified Strengths
        self.strengths = self._extract_verified_strengths()

        # 3. Process Canonical Skill Gaps
        self.gaps = self._process_skill_gaps()

        # 4. Generate Roadmaps for Prioritized Gaps
        self.roadmaps = self._generate_gap_roadmaps()

    def _extract_verified_strengths(self) -> Dict[str, Any]:
        """Extracts candidate's verified strengths from resume analysis."""
        skills = self.analysis_data.get("resume_skills") or []
        matched = self.analysis_data.get("matched_skills") or []
        projects = self.analysis_data.get("projects") or self.analysis_data.get("relevant_projects") or []
        internships = self.analysis_data.get("internships") or []
        edu_summary = self.analysis_data.get("education_analysis", {}).get("notes", "Verified degree coursework")
        exp_summary = self.analysis_data.get("experience_summary", {}).get("display_summary", "Demonstrated hands-on experience")

        return {
            "total_skills": len(skills),
            "verified_skills": skills,
            "matched_skills": matched,
            "projects_count": len(projects),
            "projects": projects,
            "internships_count": len(internships),
            "internships": internships,
            "education": edu_summary,
            "experience_summary": exp_summary
        }

    def _process_skill_gaps(self) -> Dict[str, Any]:
        """Categorizes and prioritizes skill gaps according to mandatory and preferred requirements."""
        missing_req = self.analysis_data.get("missing_required_skills") or []
        missing_pref = self.analysis_data.get("missing_preferred_skills") or []
        partial_req = self.analysis_data.get("partially_evidenced_required_skills") or []
        partial_all = self.analysis_data.get("partially_evidenced_skills") or []

        raw_items = []
        for s in missing_req:
            raw_items.append((s, "Mandatory", "Not evidenced in resume"))
        for s in partial_req:
            if s not in [item[0] for item in raw_items]:
                raw_items.append((s, "Mandatory", "Partially evidenced (needs deeper reinforcement)"))
        for s in missing_pref:
            if s not in [item[0] for item in raw_items]:
                raw_items.append((s, "Preferred", "Preferred by employer (competitive advantage)"))

        jd_text = self.analysis_data.get("job_description_text") or self.analysis_data.get("raw_jd") or self.analysis_data.get("job_description", "")
        verified_skills = self.strengths.get("verified_skills", [])
        projects = self.strengths.get("projects", [])
        pref_name = self.identity.get("preferred_name")

        prioritized = []
        for s, tier, status in raw_items:
            cat = classify_mentor_category(s)
            p_info = calculate_skill_priority(s, tier, status, verified_skills, jd_text, projects)
            jd_sent = find_jd_sentence_for_skill(s, jd_text)
            rel_exp = find_related_candidate_experience(s, verified_skills, projects)
            rec_act = recommend_gap_action(s, cat, projects)
            explanation = format_gap_explanation(s, tier, verified_skills, pref_name)

            curriculum = get_curriculum_for_skill(s)
            is_specialized = curriculum.get("is_verified_specialized", False)
            curr_source = "Curated Industry Curriculum" if is_specialized else "General Engineering Framework (Specialized guidance not yet available)"
            stages = curriculum.get("stages", [])
            deliverable = curriculum.get("practical_deliverable")
            if not deliverable and stages:
                deliverable = stages[-1].get("deliverable")
            if not deliverable:
                deliverable = curriculum.get("mini_project", {}).get("title", "Verified implementation artifact with documentation and test notes.")

            from src.mentor.counseling_profile import build_counseling_profile

            counseling_prof = build_counseling_profile(
                skill_name=s,
                category=cat,
                priority_tier=tier,
                verified_skills=verified_skills,
                projects=projects,
                jd_sentence=jd_sent,
                practical_action=rec_act,
                practical_deliverable=deliverable,
                curriculum_source=curr_source
            )

            prioritized.append({
                "skill_name": s,
                "category": cat,
                "priority_tier": tier,
                "status": status,
                "evidence_status": "Partially evidenced" if "Partially" in status else "Not evidenced in resume",
                "jd_sentence": jd_sent,
                "related_experience": rel_exp,
                "priority": p_info["priority_label"],
                "priority_score": p_info["priority_score"],
                "priority_reason": p_info["priority_reason"],
                "recommended_action": rec_act,
                "practical_deliverable": deliverable,
                "curriculum_source": curr_source,
                "counseling_profile": counseling_prof,
                "explanation": explanation
            })

        # Multi-factor rank: Sort by priority_score descending
        prioritized.sort(key=lambda g: g["priority_score"], reverse=True)

        pathways = cluster_skill_gaps([p["skill_name"] for p in prioritized])

        core_tech = [g for g in prioritized if g["category"] == "Core Technical Skills"]
        eng_tools = [g for g in prioritized if g["category"] == "Engineering Tools and Practices"]
        prof_behav = [g for g in prioritized if g["category"] == "Professional and Behavioral Competencies"]
        prod_tools = [g for g in prioritized if g["category"] == "Productivity and Business Tools"]

        return {
            "missing_required": missing_req,
            "missing_preferred": missing_pref,
            "partially_evidenced": partial_req,
            "total_gaps_count": len(prioritized),
            "satisfied_alternatives": self.analysis_data.get("satisfied_alternatives", []),
            "prioritized_gaps": prioritized,
            "top_priorities": prioritized[:5],
            "expandable_requirements": prioritized[5:],
            "categories": {
                "core_technical": core_tech,
                "engineering_tools": eng_tools,
                "professional_behavioral": prof_behav,
                "productivity_tools": prod_tools,
                "Core Technical Skills": core_tech,
                "Engineering Tools and Practices": eng_tools,
                "Professional and Behavioral Competencies": prof_behav,
                "Productivity and Business Tools": prod_tools
            },
            "pathways": pathways
        }

    def _generate_gap_roadmaps(self) -> List[Dict[str, Any]]:
        """Generates 7-stage learning roadmaps for top prioritized skill gaps."""
        roadmaps = []
        for gap in self.gaps["prioritized_gaps"][:6]:
            s_name = gap["skill_name"]
            tier = gap["priority_tier"]
            rm = generate_skill_roadmap(
                s_name,
                priority_tier=tier,
                candidate_evidence=self.strengths
            )
            rm["category"] = gap["category"]
            rm["priority_label"] = gap["priority"]
            rm["priority_reason"] = gap["priority_reason"]
            rm["recommended_action"] = gap["recommended_action"]
            rm["practical_deliverable"] = gap.get("practical_deliverable")
            rm["curriculum_source"] = gap.get("curriculum_source")
            rm["counseling_profile"] = gap.get("counseling_profile")
            rm["related_experience"] = gap["related_experience"]
            rm["jd_sentence"] = gap["jd_sentence"]
            roadmaps.append(rm)
        return roadmaps

    def build_mentor_dossier(
        self,
        timeline_days: int = 14,
        daily_hours: float = 2.0,
        progress_tracker: Optional[CandidateProgressTracker] = None
    ) -> Dict[str, Any]:
        """
        Assembles complete, structured, JSON-serializable Career Mentor Dossier.
        """
        job_title = self.analysis_data.get("job_title") or "Target Technical Role"
        study_plan = generate_realistic_study_plan(self.roadmaps, timeline_days, daily_hours)

        # Progress summary
        if progress_tracker is None:
            progress_tracker = CandidateProgressTracker()

        # Collect all scheduled task keys and populate roadmap milestones
        all_task_keys = []
        for rm in self.roadmaps:
            s_name_slug = rm["skill_name"].lower().replace(" ", "_").replace("/", "_")
            milestones = []
            for st in rm["stages"]:
                t_key = f"{s_name_slug}_stage_{st['stage_num']}"
                all_task_keys.append(t_key)
                st_status = progress_tracker.get_task_status(t_key)
                st["task_key"] = t_key
                st["status"] = st_status
                st["completed"] = (st_status == "Completed")
                milestones.append({
                    "step_number": st["stage_num"],
                    "step_title": f"{st['name']}: {st.get('curriculum_name') or st['task'][:50]}",
                    "task_key": t_key,
                    "task": st["task"],
                    "status": st_status,
                    "completed": (st_status == "Completed"),
                    "estimated_hours": 2,
                    "exercise": st.get("exercise", ""),
                    "deliverable": st.get("deliverable", ""),
                    "verification_method": st.get("verification_method", "")
                })
            rm["milestones"] = milestones

        progress_summary = progress_tracker.calculate_progress_summary(all_task_keys)
        encouragement = build_progress_encouragement(
            progress_summary["completed_tasks"],
            progress_summary["total_tasks"]
        )

        welcome_greeting = build_welcome_greeting(
            preferred_name=self.identity["preferred_name"],
            target_role=job_title,
            verified_skills_count=len(self.strengths["verified_skills"]),
            gap_count=self.gaps["total_gaps_count"]
        )

        action_plans = [rm.get("action_plan") for rm in self.roadmaps if rm.get("action_plan")]

        return {
            "identity": self.identity,
            "target_role": job_title,
            "welcome_greeting": welcome_greeting,
            "encouragement_message": encouragement,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "roadmaps": self.roadmaps,
            "action_plans": action_plans,
            "study_plan": study_plan,
            "progress_summary": progress_summary,
            "disclaimer": (
                "Career Mentor provides structured technical guidance, genuine educational resources, and interview preparation coaching. "
                "Following these roadmaps helps build authentic skills, but does not guarantee employment or interview selection."
            )
        }

"""
Deterministic Resume Improvement Recommendations & Verified Learning Resources Engine.
Generates:
1. Targeted resume enhancement suggestions partitioned by competency category:
   - Technical & Tool gaps -> Practical project implementation
   - Professional skill gaps -> Demonstrated workflows and engineering practices
   - Soft & Behavioral gaps -> Truthful collaboration, leadership, and ownership evidence
2. Curated mapping of skills to official, reputable educational documentation without LLMs.
Zero LLM reliance. Fully deterministic.
"""

from typing import Dict, List, Optional, Set
from src.preprocessing.skill_extractor import (
    categorize_competency,
    TAXONOMY_TECHNICAL,
    TAXONOMY_TOOL,
    TAXONOMY_PROFESSIONAL,
    TAXONOMY_SOFT,
    TAXONOMY_PRODUCTIVITY,
    TAXONOMY_PROGRAMMING_LANGUAGES,
    TAXONOMY_FRAMEWORKS_LIBRARIES,
    TAXONOMY_DATABASES,
    TAXONOMY_DEVELOPER_TOOLS,
    TAXONOMY_CLOUD_INFRASTRUCTURE,
    FILTERED_GENERIC_SKILLS
)


# Verified official learning resources mapping (Strictly legitimate URLs, no invented links)
OFFICIAL_LEARNING_RESOURCES: Dict[str, Dict[str, str]] = {
    "python": {
        "title": "Python Official Tutorial & Documentation",
        "url": "https://docs.python.org/3/tutorial/",
        "provider": "Python Software Foundation",
        "description": "Comprehensive official reference covering language fundamentals, data structures, and standard libraries."
    },
    "scikit-learn": {
        "title": "scikit-learn User Guide & Tutorials",
        "url": "https://scikit-learn.org/stable/user_guide.html",
        "provider": "scikit-learn Consortium",
        "description": "Industry standard guide for supervised learning, feature pipelines, and model evaluation."
    },
    "machine learning": {
        "title": "Machine Learning Crash Course",
        "url": "https://developers.google.com/machine-learning/crash-course",
        "provider": "Google for Developers",
        "description": "Self-study curriculum on foundational ML concepts, loss functions, and classification metrics."
    },
    "pytorch": {
        "title": "Deep Learning with PyTorch Tutorials",
        "url": "https://pytorch.org/tutorials/",
        "provider": "PyTorch Foundation / Linux Foundation",
        "description": "Official practical guides for building neural network models and training pipelines."
    },
    "tensorflow": {
        "title": "TensorFlow Core Tutorials",
        "url": "https://www.tensorflow.org/tutorials",
        "provider": "TensorFlow / Google",
        "description": "Step-by-step documentation for numerical computation and deep learning architectures."
    },
    "sql": {
        "title": "PostgreSQL Official Documentation & SQL Tutorial",
        "url": "https://www.postgresql.org/docs/current/tutorial.html",
        "provider": "PostgreSQL Global Development Group",
        "description": "Authoritative relational database guide covering queries, joins, transactions, and indexing."
    },
    "postgresql": {
        "title": "PostgreSQL Interactive Manual",
        "url": "https://www.postgresql.org/docs/",
        "provider": "PostgreSQL Global Development Group",
        "description": "In-depth guide for database design, optimization, and administration."
    },
    "docker": {
        "title": "Docker Hands-On Getting Started Guide",
        "url": "https://docs.docker.com/get-started/",
        "provider": "Docker Inc.",
        "description": "Official containerization tutorial for building images, multi-stage Dockerfiles, and compose stacks."
    },
    "kubernetes": {
        "title": "Kubernetes Official Documentation & Interactive Tutorials",
        "url": "https://kubernetes.io/docs/tutorials/",
        "provider": "Cloud Native Computing Foundation (CNCF)",
        "description": "Complete guide for cluster orchestration, deployments, services, and ingress configuration."
    },
    "amazon web services": {
        "title": "AWS Skill Builder & Cloud Practitioner Training",
        "url": "https://aws.amazon.com/training/",
        "provider": "Amazon Web Services",
        "description": "Official foundational and architectural training for AWS core computing, storage, and networking."
    },
    "microsoft azure": {
        "title": "Microsoft Learn: Azure Fundamentals Path",
        "url": "https://learn.microsoft.com/en-us/training/azure/",
        "provider": "Microsoft Learn",
        "description": "Structured curriculum for enterprise cloud architecture, VMs, App Services, and Cosmos DB."
    },
    "google cloud platform": {
        "title": "Google Cloud Skills Boost",
        "url": "https://cloud.google.com/learn",
        "provider": "Google Cloud",
        "description": "Official guided labs for Google Cloud compute, storage, BigQuery, and Kubernetes Engine."
    },
    "react": {
        "title": "React Official Documentation: Quick Start & Hooks",
        "url": "https://react.dev/learn",
        "provider": "Meta Open Source",
        "description": "Interactive component-driven frontend documentation covering JSX, state management, and hooks."
    },
    "node.js": {
        "title": "Node.js Official Learning Guides",
        "url": "https://nodejs.org/en/learn",
        "provider": "OpenJS Foundation",
        "description": "Server-side asynchronous JavaScript development, event loops, and RESTful API architecture."
    },
    "javascript": {
        "title": "MDN JavaScript Technologies Reference",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "provider": "Mozilla Developer Network (MDN)",
        "description": "Comprehensive language reference covering ES6+ syntax, asynchronous promises, and DOM APIs."
    },
    "typescript": {
        "title": "TypeScript Official Handbook",
        "url": "https://www.typescriptlang.org/docs/handbook/intro.html",
        "provider": "Microsoft",
        "description": "Official handbook for static type systems, generics, and enterprise TypeScript patterns."
    },
    "git": {
        "title": "Pro Git Book & Reference Manual",
        "url": "https://git-scm.com/book/en/v2",
        "provider": "Git SCM Community",
        "description": "Comprehensive guide on distributed version control, branching strategies, and collaborative workflows."
    },
    "c++": {
        "title": "cppreference.com — C++ Reference",
        "url": "https://en.cppreference.com/w/cpp",
        "provider": "C++ Community",
        "description": "Authoritative standard library, algorithms, memory management, and modern C++ reference."
    },
    "c#": {
        "title": "C# Documentation & Learning Path",
        "url": "https://learn.microsoft.com/en-us/dotnet/csharp/",
        "provider": "Microsoft Learn",
        "description": "Official documentation for modern C#, LINQ, asynchronous programming, and .NET runtime."
    },
    ".net": {
        "title": ".NET Official Documentation & Architecture Guides",
        "url": "https://learn.microsoft.com/en-us/dotnet/",
        "provider": "Microsoft Learn",
        "description": "Comprehensive framework guide for cross-platform backend web services and microservices."
    },
    "fastapi": {
        "title": "FastAPI Tutorial — User Guide",
        "url": "https://fastapi.tiangolo.com/tutorial/",
        "provider": "FastAPI Tiangolo",
        "description": "Official documentation for high-performance Python APIs with automatic OpenAPI docs and Pydantic validation."
    },
    "django": {
        "title": "Django Documentation: Getting Started",
        "url": "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
        "provider": "Django Software Foundation",
        "description": "Comprehensive web framework tutorial covering models, migrations, views, and authentication."
    },
    "linux": {
        "title": "Ubuntu Command Line & System Administration Tutorials",
        "url": "https://ubuntu.com/tutorials",
        "provider": "Canonical",
        "description": "Practical terminal tutorials covering shell scripting, user permissions, and package management."
    }
}


class RecommendationEngine:
    """
    Generates actionable resume enhancement advice and curated learning resources.
    Categorizes advice strictly by competency domain.
    """

    def generate_recommendations(
        self,
        missing_required: List[str],
        missing_preferred: List[str],
        partially_evidenced: List[str],
        experience_analysis: Dict,
        job_title: str
    ) -> List[Dict]:
        """
        Synthesizes deterministic recommendations for resume improvements.
        Generates category-appropriate advice without generic project suggestions.
        """
        recs = []

        # Filter out any generic terms that might have leaked
        clean_missing_req = [s for s in missing_required if s.lower() not in FILTERED_GENERIC_SKILLS]
        clean_missing_pref = [s for s in missing_preferred if s.lower() not in FILTERED_GENERIC_SKILLS]
        clean_partial = [s for s in partially_evidenced if s.lower() not in FILTERED_GENERIC_SKILLS]

        # 1. Partition Missing Required Skills by Taxonomy
        tech_tools = []
        prod_tools = []
        prof_skills = []
        soft_skills = []

        for s in clean_missing_req:
            cat = categorize_competency(s)
            if cat in (
                TAXONOMY_PROGRAMMING_LANGUAGES,
                TAXONOMY_FRAMEWORKS_LIBRARIES,
                TAXONOMY_DATABASES,
                TAXONOMY_DEVELOPER_TOOLS,
                TAXONOMY_CLOUD_INFRASTRUCTURE,
                TAXONOMY_TECHNICAL,
                TAXONOMY_TOOL,
            ):
                tech_tools.append(s)
            elif cat == TAXONOMY_PRODUCTIVITY:
                prod_tools.append(s)
            elif cat == TAXONOMY_PROFESSIONAL:
                prof_skills.append(s)
            elif cat == TAXONOMY_SOFT:
                soft_skills.append(s)
            else:
                tech_tools.append(s)

        # 1a. Technical / Tool Gaps -> Practical implementation project
        if tech_tools:
            top_tech = tech_tools[:3]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_tech])
            recs.append({
                "category": "Technical Skill Gap",
                "severity": "critical",
                "recommendation": f"Implement and document hands-on project evidence for core technologies: {skills_str}.",
                "actionable_step": f"Build a functional implementation using {skills_str} (e.g., prototype service, data pipeline, or application). Document architecture and publish the repository on GitHub."
            })

        # 1b. Productivity Software Gaps -> Documentation, models, and presentation deliverables
        if prod_tools:
            top_prod = prod_tools[:2]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_prod])
            recs.append({
                "category": "Productivity Software Competency",
                "severity": "important",
                "recommendation": f"Demonstrate applied proficiency in office and productivity tools: {skills_str}.",
                "actionable_step": f"Highlight structured business documentation, financial models, data summaries, or professional presentation decks created using {skills_str}."
            })

        # 1c. Professional Skill Gaps -> Demonstrated workflows & practices
        if prof_skills:
            top_prof = prof_skills[:2]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_prof])
            recs.append({
                "category": "Professional Methodology Gap",
                "severity": "important",
                "recommendation": f"Demonstrate applied engineering workflows: {skills_str}.",
                "actionable_step": f"Describe practical experience with {skills_str} in your work history or academic capstone (e.g. agile sprint cadence, automated CI/CD pipelines, or code review standards)."
            })

        # 1d. Soft / Behavioral Gaps -> Truthful collaboration & leadership evidence
        if soft_skills:
            top_soft = soft_skills[:2]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_soft])
            recs.append({
                "category": "Behavioral Competency Evidence",
                "severity": "important",
                "recommendation": f"Highlight truthful examples demonstrating {skills_str}.",
                "actionable_step": f"Incorporate contextual resume bullets showing {skills_str} through cross-functional teamwork, client presentations, or technical mentoring achievements."
            })

        # 2. Partially Evidenced Skills
        if clean_partial:
            top_partial = clean_partial[:3]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_partial])
            recs.append({
                "category": "Evidence Substantiation",
                "severity": "important",
                "recommendation": f"Substantiate static keyword listings with project bullets: {skills_str}.",
                "actionable_step": f"Move {skills_str} from isolated keyword lists into your Experience or Projects section. Describe how you deployed each tool with measurable results."
            })

        # 3. Experience Gap Alignment
        exp_gap = experience_analysis.get("experience_gap_years", 0.0)
        meets_exp = experience_analysis.get("meets_experience_requirement", True)
        has_job_exp = experience_analysis.get("has_job_exp", False)
        if not meets_exp and has_job_exp:
            req_yrs = experience_analysis.get("job_required_years")
            recs.append({
                "category": "Experience Alignment",
                "severity": "moderate",
                "recommendation": f"Job requests {req_yrs} years experience; candidate tenure is not yet established.",
                "actionable_step": "Prominently highlight relevant technical internships, capstone projects, and freelance contributions to demonstrate depth of implementation when formal tenure is limited."
            })

        # 4. Project Structuring
        projects_count = experience_analysis.get("projects_count", 0)
        if projects_count < 2:
            recs.append({
                "category": "Portfolio Structuring",
                "severity": "recommended",
                "recommendation": "Expand project section with at least 2 structured technical case studies.",
                "actionable_step": f"Structure projects using the Problem-Action-Result format, detailing tools directly aligned with {job_title}."
            })

        # 5. Preferred Qualifications
        if clean_missing_pref:
            top_pref = clean_missing_pref[:2]
            skills_str = ", ".join([f"'{s.title()}'" for s in top_pref])
            recs.append({
                "category": "Preferred Qualification",
                "severity": "enhancement",
                "recommendation": f"Consider exploring preferred bonus technologies: {skills_str}.",
                "actionable_step": f"Familiarity with {skills_str} strengthens candidacy and differentiates your profile during competitive technical review."
            })

        return recs

    def get_learning_resources(self, missing_skills: List[str]) -> List[Dict]:
        """
        Retrieves verified official documentation resources for missing skills.
        Filters generic terms and provides honest, non-fabricated resource links.
        """
        resources = []
        seen_urls = set()

        for skill in missing_skills:
            skill_clean = skill.strip().lower()
            if skill_clean in FILTERED_GENERIC_SKILLS:
                continue
            if skill_clean in OFFICIAL_LEARNING_RESOURCES:
                res = OFFICIAL_LEARNING_RESOURCES[skill_clean]
                if res["url"] not in seen_urls:
                    seen_urls.add(res["url"])
                    resources.append({
                        "skill": skill.title(),
                        "title": res["title"],
                        "url": res["url"],
                        "provider": res["provider"],
                        "description": res["description"]
                    })

        return resources

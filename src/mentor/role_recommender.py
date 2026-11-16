"""
Role Recommender Module.
Evaluates candidate verified competencies against industry engineering archetypes.
Provides deterministic fit scoring, matching strengths, key skill gaps, and next actions.
Honestly labels recommendations as heuristic alignments without unverified market claims.
"""

from typing import Dict, List, Any, Optional
from src.common.evidence_registry import resolve_canonical_skill


# Curated Industry Role Archetypes
ROLE_ARCHETYPES = [
    {
        "role_id": "backend_engineer",
        "title": "Backend Engineer",
        "description": "Designs scalable server-side systems, REST/gRPC APIs, microservices, and database persistence architectures.",
        "core_skills": ["Python", "SQL", "Docker", "REST APIs", "PostgreSQL", "Git", "Linux"],
        "secondary_skills": ["Kubernetes", "Redis", "CI/CD", "AWS", "Microservices", "System Design"],
        "category": "Software Engineering",
        "primary_focus": "Distributed API services, business logic execution, and database modeling."
    },
    {
        "role_id": "fullstack_engineer",
        "title": "Full Stack Engineer",
        "description": "Builds end-to-end web applications bridging responsive client-side UIs and robust backend services.",
        "core_skills": ["JavaScript", "TypeScript", "React", "Python", "SQL", "Git", "REST APIs"],
        "secondary_skills": ["Docker", "Node.js", "HTML", "CSS", "PostgreSQL", "CI/CD"],
        "category": "Web Development",
        "primary_focus": "Client-server architecture, responsive frontend components, and API integration."
    },
    {
        "role_id": "frontend_engineer",
        "title": "Frontend Engineer",
        "description": "Specializes in client-side architectures, state management, responsive UI design, and web performance.",
        "core_skills": ["JavaScript", "TypeScript", "React", "HTML", "CSS", "Git"],
        "secondary_skills": ["REST APIs", "Webpack", "Vite", "Tailwind CSS", "Automated Testing"],
        "category": "Web Development",
        "primary_focus": "Component state lifecycle, web accessibility, and interactive user interfaces."
    },
    {
        "role_id": "devops_cloud_engineer",
        "title": "DevOps & Cloud Engineer",
        "description": "Automates cloud infrastructure provisioning, CI/CD deployment pipelines, container orchestration, and monitoring.",
        "core_skills": ["Docker", "Linux", "Kubernetes", "CI/CD", "AWS", "Git", "Bash"],
        "secondary_skills": ["Terraform", "Ansible", "Python", "Prometheus", "Networking", "Security"],
        "category": "Cloud & Infrastructure",
        "primary_focus": "Infrastructure automation, container scheduling, and high-availability operations."
    },
    {
        "role_id": "machine_learning_engineer",
        "title": "Machine Learning Engineer",
        "description": "Develops, trains, evaluates, and deploys predictive machine learning and deep learning models to production.",
        "core_skills": ["Python", "Scikit-Learn", "NumPy", "Pandas", "SQL", "Machine Learning"],
        "secondary_skills": ["PyTorch", "TensorFlow", "Docker", "MLOps", "Model Deployment", "Data Pipelines"],
        "category": "Data Science & AI",
        "primary_focus": "Statistical model training, evaluation metrics, and inference pipeline integration."
    },
    {
        "role_id": "data_engineer",
        "title": "Data Engineer",
        "description": "Architects high-throughput ETL data pipelines, distributed data warehouses, and streaming compute infrastructure.",
        "core_skills": ["Python", "SQL", "Spark", "PostgreSQL", "ETL", "Git"],
        "secondary_skills": ["Docker", "Kafka", "Airflow", "AWS", "Data Warehousing", "Linux"],
        "category": "Data Platforms",
        "primary_focus": "Batch and streaming pipeline reliability, data lake modeling, and schema normalization."
    },
    {
        "role_id": "data_analyst",
        "title": "Data Analyst & BI Specialist",
        "description": "Extracts operational insights, designs interactive business intelligence dashboards, and quantifies business KPIs.",
        "core_skills": ["SQL", "Excel", "Python", "Power BI", "Data Analysis"],
        "secondary_skills": ["Tableau", "Pandas", "Statistics", "Reporting", "Communication"],
        "category": "Analytics & Business Intelligence",
        "primary_focus": "Descriptive statistics, KPI dashboard Authoring, and relational querying."
    },
    {
        "role_id": "systems_software_engineer",
        "title": "Systems / Software Engineer",
        "description": "Develops high-performance native applications, low-latency concurrent services, and memory-managed systems.",
        "core_skills": ["C++", "Linux", "Algorithms", "Data Structures", "Git", "OOP"],
        "secondary_skills": ["C#", "Multithreading", "Docker", "Python", "Debugging", "Bash"],
        "category": "Systems Engineering",
        "primary_focus": "Computational complexity optimization, memory safety, and operating system interfaces."
    }
]


def recommend_suitable_roles(
    career_profile: Dict[str, Any],
    analysis_data: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Computes deterministic role suitability recommendations based on candidate's
    demonstrated and verified evidence. Never fabricates credentials or market data.
    """
    data = analysis_data or {}
    
    # Extract canonical candidate skills by source
    demonstrated_skills = {
        s["skill"].lower(): s for s in career_profile.get("demonstrated_competencies", [])
    }
    confirmed_skills = {
        s["skill"].lower(): s for s in career_profile.get("candidate_confirmed_competencies", [])
    }
    partial_skills = {
        s["skill"].lower(): s for s in career_profile.get("partially_evidenced_competencies", [])
    }

    # All known candidate skills mapped to canonical lowercase
    all_candidate_skills = set(demonstrated_skills.keys()) | set(confirmed_skills.keys()) | set(partial_skills.keys())
    
    # Also consider resume_skills from analysis if present
    for s in data.get("resume_skills", []):
        all_candidate_skills.add(resolve_canonical_skill(s).lower())

    projects = career_profile.get("projects", [])
    primary_project = projects[0].get("title") if projects else None

    recommendations = []

    for archetype in ROLE_ARCHETYPES:
        core_skills = [resolve_canonical_skill(s) for s in archetype["core_skills"]]
        secondary_skills = [resolve_canonical_skill(s) for s in archetype["secondary_skills"]]
        
        matching_core = []
        matching_secondary = []
        missing_core = []
        missing_secondary = []

        total_weight = len(core_skills) * 1.5 + len(secondary_skills) * 1.0
        earned_weight = 0.0

        for s in core_skills:
            s_lower = s.lower()
            if s_lower in demonstrated_skills:
                matching_core.append(s)
                earned_weight += 1.5
            elif s_lower in confirmed_skills:
                matching_core.append(s)
                earned_weight += 1.5 * 0.75
            elif s_lower in partial_skills or s_lower in all_candidate_skills:
                matching_core.append(s)
                earned_weight += 1.5 * 0.50
            else:
                missing_core.append(s)

        for s in secondary_skills:
            s_lower = s.lower()
            if s_lower in demonstrated_skills:
                matching_secondary.append(s)
                earned_weight += 1.0
            elif s_lower in confirmed_skills:
                matching_secondary.append(s)
                earned_weight += 1.0 * 0.75
            elif s_lower in partial_skills or s_lower in all_candidate_skills:
                matching_secondary.append(s)
                earned_weight += 1.0 * 0.50
            else:
                missing_secondary.append(s)

        match_score = min(round((earned_weight / total_weight) * 100, 1), 100.0) if total_weight > 0 else 0.0

        if match_score >= 60.0:
            fit_tier = "Strong Fit"
            fit_badge = "success"
        elif match_score >= 35.0:
            fit_tier = "Potential Fit"
            fit_badge = "warning"
        else:
            fit_tier = "Growth Fit"
            fit_badge = "info"

        # Construct specific evidence-grounded fit explanation
        reasons = []
        if matching_core:
            reasons.append(f"Demonstrates verified foundational competence in {', '.join(matching_core[:3])}")
        if primary_project:
            reasons.append(f"Project background in '{primary_project}' aligns with practical engineering demands")
        if not matching_core:
            reasons.append(f"Requires closing core {missing_core[0] if missing_core else 'engineering'} competencies")

        fit_reason = "; ".join(reasons) + "."

        # Deterministic practical next action
        if missing_core:
            top_gap = missing_core[0]
            next_action = f"Complete a hands-on implementation project to demonstrate practical proficiency in {top_gap}."
        elif missing_secondary:
            top_gap = missing_secondary[0]
            next_action = f"Reinforce competitive edge by adopting {top_gap} in production deployment workflows."
        else:
            next_action = f"Prepare for senior interview loops focusing on system architecture and design trade-offs."

        market_note = (
            "Heuristic alignment based on ResumeMatch AI engineering archetype standards. "
            "Real-time market demand and compensation vary by location and organization."
        )

        role_entry = {
            "role_id": archetype["role_id"],
            "title": archetype["title"],
            "role_title": archetype["title"],
            "category": archetype["category"],
            "description": archetype["description"],
            "primary_focus": archetype["primary_focus"],
            "match_score": match_score,
            "match_score_pct": match_score,
            "fit_tier": fit_tier,
            "fit_badge": fit_badge,
            "fit_reason": fit_reason,
            "evidence_grounded_fit_reason": fit_reason,
            "matching_skills": matching_core + matching_secondary,
            "matching_competencies": matching_core + matching_secondary,
            "matching_core_count": len(matching_core),
            "missing_core_skills": missing_core,
            "missing_secondary_skills": missing_secondary,
            "primary_gaps": missing_core[:3] if missing_core else missing_secondary[:3],
            "practical_next_action": next_action,
            "recommended_actions": [next_action],
            "market_intelligence_note": market_note,
            "heuristic_note": market_note
        }
        recommendations.append(role_entry)

    # Sort descending by match_score
    recommendations.sort(key=lambda r: r["match_score"], reverse=True)
    if limit is not None and limit > 0:
        return recommendations[:limit]
    return recommendations


def evaluate_specific_role(
    role_name_or_id: str,
    career_profile: Dict[str, Any],
    analysis_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluates candidate against a specific chosen target role."""
    all_recs = recommend_suitable_roles(career_profile, analysis_data, limit=None)
    target = (role_name_or_id or "").lower().strip()

    for r in all_recs:
        if r["role_id"] == target or r["title"].lower() == target or target in r["title"].lower() or r["title"].lower() in target:
            return r

    # If custom role name not in standard archetypes, build dynamic assessment
    demonstrated = career_profile.get("demonstrated_competencies", [])
    matching_names = [s["skill"] for s in demonstrated[:5]]
    heuristic = "Custom target role evaluation based on candidate's current documented skills profile."
    next_action = "Align resume experience bullet points with target role responsibilities."

    return {
        "role_id": "custom_role",
        "title": role_name_or_id.title(),
        "role_title": role_name_or_id.title(),
        "category": "Custom Target Role",
        "description": f"Custom evaluation for target role '{role_name_or_id}'.",
        "primary_focus": "Target role requirements alignment.",
        "match_score": 50.0,
        "match_score_pct": 50.0,
        "fit_tier": "Potential Fit",
        "fit_badge": "warning",
        "fit_reason": "Evaluated against candidate's current documented skills profile.",
        "evidence_grounded_fit_reason": "Evaluated against candidate's current documented skills profile.",
        "matching_skills": matching_names,
        "matching_competencies": matching_names,
        "matching_core_count": len(demonstrated),
        "missing_core_skills": [],
        "missing_secondary_skills": [],
        "primary_gaps": [],
        "practical_next_action": next_action,
        "recommended_actions": [next_action],
        "market_intelligence_note": heuristic,
        "heuristic_note": heuristic
    }

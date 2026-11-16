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
    
    # Extract canonical candidate skills by source evidence tier
    traceable_demonstrated = {}
    registry_derived_skills = {}
    for s in career_profile.get("demonstrated_competencies", []):
        name = s["skill"].lower()
        if s.get("evidence_source") == "registry_derived" or s.get("excerpt_status") == "unavailable" or not s.get("excerpt"):
            registry_derived_skills[name] = s
        else:
            traceable_demonstrated[name] = s

    confirmed_skills = {
        s["skill"].lower(): s for s in career_profile.get("candidate_confirmed_competencies", [])
    }
    partial_skills = {
        s["skill"].lower(): s for s in career_profile.get("partially_evidenced_competencies", [])
    }

    # All known candidate skills mapped to canonical lowercase
    all_candidate_skills = (
        set(traceable_demonstrated.keys()) |
        set(registry_derived_skills.keys()) |
        set(confirmed_skills.keys()) |
        set(partial_skills.keys())
    )
    
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
            if s_lower in traceable_demonstrated:
                matching_core.append(s)
                earned_weight += 1.5 * 1.0  # Full demonstrated weight (1.0 factor)
            elif s_lower in confirmed_skills:
                matching_core.append(s)
                earned_weight += 1.5 * 0.75  # Candidate-confirmed self-attestation weight (0.75 factor)
            elif s_lower in registry_derived_skills:
                matching_core.append(s)
                earned_weight += 1.5 * 0.60  # Registry-derived without excerpt weight (0.60 factor)
            elif s_lower in partial_skills or s_lower in all_candidate_skills:
                matching_core.append(s)
                earned_weight += 1.5 * 0.50  # Partial evidence weight (0.50 factor)
            else:
                missing_core.append(s)

        for s in secondary_skills:
            s_lower = s.lower()
            if s_lower in traceable_demonstrated:
                matching_secondary.append(s)
                earned_weight += 1.0 * 1.0
            elif s_lower in confirmed_skills:
                matching_secondary.append(s)
                earned_weight += 1.0 * 0.75
            elif s_lower in registry_derived_skills:
                matching_secondary.append(s)
                earned_weight += 1.0 * 0.60
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
    analysis_data: Optional[Dict[str, Any]] = None,
    custom_role_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate against a specific chosen target role.
    For standard archetypes, returns deterministic match metrics.
    For unlisted custom roles without structured requirements, returns an 'unevaluated'
    status without inventing scores or fit tiers.
    """
    if not isinstance(role_name_or_id, str) or not role_name_or_id.strip():
        raise ValueError("Invalid role name: must be a non-empty string.")
    
    clean_role = role_name_or_id.strip()
    if len(clean_role) > 100:
        raise ValueError("Role name exceeds maximum allowable length of 100 characters.")

    all_recs = recommend_suitable_roles(career_profile, analysis_data, limit=None)
    target = clean_role.lower()

    for r in all_recs:
        if r["role_id"] == target or r["title"].lower() == target or target in r["title"].lower() or r["title"].lower() in target:
            return r

    # Check if structured requirements were provided for this custom role
    reqs = custom_role_requirements or {}
    if not reqs and analysis_data:
        # Check if analysis_data contains specific custom role requirements
        if analysis_data.get("job_title", "").strip().lower() == target and analysis_data.get("required_skills"):
            reqs = {
                "core_skills": analysis_data.get("required_skills", []),
                "secondary_skills": analysis_data.get("preferred_skills", [])
            }

    core_reqs = reqs.get("core_skills") or reqs.get("required_skills") or []
    if core_reqs:
        # Evaluate dynamically against the provided structured requirements using explicit evidence tiers
        traceable_demonstrated = {
            s["skill"].lower(): s for s in career_profile.get("demonstrated_competencies", [])
            if s.get("evidence_source") != "registry_derived" and s.get("excerpt_status") != "unavailable" and s.get("excerpt")
        }
        registry_derived = {
            s["skill"].lower(): s for s in career_profile.get("demonstrated_competencies", [])
            if s.get("evidence_source") == "registry_derived" or s.get("excerpt_status") == "unavailable" or not s.get("excerpt")
        }
        candidate_confirmed = {s["skill"].lower(): s for s in career_profile.get("candidate_confirmed_competencies", [])}
        partial_skills = {s["skill"].lower(): s for s in career_profile.get("partially_evidenced_competencies", [])}

        matched_core = []
        missing_core = []
        total_weight = len(core_reqs) * 1.5
        earned_weight = 0.0

        for s in core_reqs:
            s_l = s.lower()
            if s_l in traceable_demonstrated:
                matched_core.append(s)
                earned_weight += 1.5 * 1.0  # Full demonstrated credit
            elif s_l in candidate_confirmed:
                matched_core.append(s)
                earned_weight += 1.5 * 0.75  # Candidate-confirmed credit
            elif s_l in registry_derived:
                matched_core.append(s)
                earned_weight += 1.5 * 0.60  # Registry-derived credit
            elif s_l in partial_skills:
                matched_core.append(s)
                earned_weight += 1.5 * 0.50  # Partial evidence credit
            else:
                missing_core.append(s)

        score = round((earned_weight / total_weight) * 100, 1) if total_weight > 0 else 0.0

        tier = "Strong Fit" if score >= 60.0 else ("Potential Fit" if score >= 35.0 else "Growth Fit")
        badge = "emerald" if score >= 60.0 else ("amber" if score >= 35.0 else "blue")
        reason = f"Evaluated against {len(core_reqs)} custom role requirements: matched {len(matched_core)} verified skills."
        next_act = f"Address primary gap in {missing_core[0]}." if missing_core else "Prepare for domain-specific interview loops."

        return {
            "role_id": "custom_role",
            "title": clean_role.title(),
            "role_title": clean_role.title(),
            "category": "Custom Target Role",
            "description": f"Custom evaluation for target role '{clean_role}' based on provided requirements.",
            "primary_focus": "Custom role requirements alignment.",
            "evaluation_status": "evaluated",
            "match_score": score,
            "match_score_pct": score,
            "fit_tier": tier,
            "fit_badge": badge,
            "fit_reason": reason,
            "evidence_grounded_fit_reason": reason,
            "matching_skills": matched_core,
            "matching_competencies": matched_core,
            "matching_core_count": len(matched_core),
            "missing_core_skills": missing_core,
            "missing_secondary_skills": [],
            "primary_gaps": missing_core[:3],
            "practical_next_action": next_act,
            "recommended_actions": [next_act],
            "market_intelligence_note": "Evaluated against user-provided custom role requirements.",
            "heuristic_note": "Evaluated against user-provided custom role requirements."
        }

    # If no structured role requirements are available, return 'unevaluated' without fabricating scores
    un_eval_msg = (
        f"Role '{clean_role}' is not one of the 8 standard engineering archetypes, "
        "and no structured requirement criteria (core skills/tools) were provided for evaluation. "
        "A reliable competency assessment requires role-specific skills and requirements."
    )
    un_eval_action = "Provide structured job requirements or select a standard engineering archetype to generate an evidence-grounded fit score."
    market_note = "Evaluation requires structured role requirements to compute evidence-grounded alignment without hallucination."

    return {
        "role_id": "custom_role",
        "title": clean_role.title(),
        "role_title": clean_role.title(),
        "category": "Custom / Unlisted Role",
        "description": f"Target role evaluation for '{clean_role}'.",
        "primary_focus": "Requires structured target role requirement specification.",
        "evaluation_status": "unevaluated",
        "match_score": None,
        "match_score_pct": None,
        "fit_tier": "Unevaluated",
        "fit_badge": "slate",
        "fit_reason": un_eval_msg,
        "evidence_grounded_fit_reason": un_eval_msg,
        "matching_skills": [],
        "matching_competencies": [],
        "matching_core_count": 0,
        "missing_core_skills": [],
        "missing_secondary_skills": [],
        "primary_gaps": [],
        "practical_next_action": un_eval_action,
        "recommended_actions": [un_eval_action],
        "market_intelligence_note": market_note,
        "heuristic_note": market_note
    }

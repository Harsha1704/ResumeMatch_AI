"""
Resume Advisor Module.
Inspects candidate resume evidence, project descriptions, and structural features
to generate deterministic, actionable resume enhancement recommendations.
Provides concrete before/after examples and rationale for every suggestion.
"""

from typing import Dict, List, Any, Optional
import re


def generate_resume_improvement_suggestions(
    career_profile: Dict[str, Any],
    analysis_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generates deterministic resume improvement recommendations based on
    analyzed candidate resume text, project descriptions, and evidence gaps.
    """
    data = analysis_data or {}
    raw_text = data.get("raw_text") or data.get("cleaned_resume_text") or ""
    projects = career_profile.get("projects", [])
    identity = career_profile.get("identity", {})
    suggestions = []

    # 1. Quantifiable Metric Verification
    # Check if project or experience descriptions contain metric numbers, percentages, or scale indicators
    has_metrics = False
    metric_pattern = re.compile(r"\b(?:\d+[%]|latency|throughput|reduced|improved by|\d+x|\d{2,}\+?\s*(?:users|requests|records|ms|sec))\b", re.I)
    
    combined_experience_text = ""
    for p in projects:
        combined_experience_text += " " + (p.get("description") or "")
    for exp in career_profile.get("internships", []):
        combined_experience_text += " " + " ".join(exp.get("responsibilities", []))
    
    if metric_pattern.search(combined_experience_text) or metric_pattern.search(raw_text):
        has_metrics = True

    # Identify any specific projects or internships lacking metrics
    unquantified_bullets = []
    for p in projects:
        desc = p.get("description", "")
        if desc and not metric_pattern.search(desc):
            unquantified_bullets.append((p.get("title") or "Project", desc))
    for exp in career_profile.get("internships", []):
        for resp in exp.get("responsibilities", []):
            if resp and not metric_pattern.search(resp):
                unquantified_bullets.append((exp.get("organization") or "Experience", resp))

    if not has_metrics or unquantified_bullets or len(projects) == 0:
        sample_before = unquantified_bullets[0][1] if unquantified_bullets else "Built a backend service using Python and Flask to process customer telemetry data."
        sample_title = unquantified_bullets[0][0] if unquantified_bullets else "Engineering Project"
        sample_after = f"Engineered {sample_title} service, improving request throughput by [measured throughput, e.g. +X%] and reducing response latency to [verified latency, e.g. <Y ms] (Insert only measured, verifiable values from your testing or production logs)."

        before_after_list = [
            {
                "original": sample_before,
                "suggested": sample_after,
                "rationale": "Demonstrates how to frame technical scope with measured scale and latency benchmarks using verifiable placeholders."
            },
            {
                "original": "Worked on REST APIs and database queries.",
                "suggested": "Architected [count] REST API endpoints handling [volume] requests with [measured uptime/availability] SLA (Insert only measured, verifiable values).",
                "rationale": "Illustrates how to add quantifiable scope and reliability metrics using your actual verified measurements without inventing unmeasured claims."
            }
        ]

        suggestions.append({
            "suggestion_id": "quantifiable_metrics",
            "category": "Quantifiable Business Impact",
            "priority": "High",
            "reason": "Engineering hiring managers look for measurable scale and business impact rather than passive task descriptions.",
            "evidence_context": f"Bullet points in '{sample_title}' describe technical activities without explicit percentage, latency, or throughput figures." if unquantified_bullets else "Current project bullet points describe technical activities without explicit percentage, latency, or throughput figures.",
            "instruction": "Insert only measured, verifiable values from your actual project benchmarks, telemetry, or production metrics. Never fabricate performance or scale statistics.",
            "actionable_example": {
                "before": sample_before,
                "after": sample_after
            },
            "before_after_examples": before_after_list,
            "practical_next_action": "Audit your project bullets and replace template placeholders with concrete, measured metrics (e.g., query latency reduction, test coverage %, or data volume processed)."
        })

    # 2. Public Repository Traceability
    if not identity.get("has_github") and not identity.get("has_portfolio"):
        suggestions.append({
            "suggestion_id": "repository_traceability",
            "category": "Portfolio & Code Verification",
            "priority": "High",
            "reason": "Technical recruiters prioritize candidates with publicly verifiable GitHub repositories containing clear documentation and runnable code.",
            "evidence_context": "No public GitHub or personal portfolio URL was detected in candidate contact information.",
            "actionable_example": {
                "before": "Header lists: email and phone number only.",
                "after": "Header lists: email | phone | github.com/username | linkedin.com/in/username"
            },
            "before_after_examples": [
                {
                    "original": "Header: email@example.com | +1 555-0100",
                    "suggested": "Header: email@example.com | +1 555-0100 | github.com/username | linkedin.com/in/username",
                    "rationale": "Provides immediate code verifiability for technical recruiters."
                }
            ],
            "practical_next_action": "Add a clickable GitHub profile link in your resume header, featuring well-documented repositories with architecture diagrams and unit tests."
        })

    # 3. Grounding Static Skill Inventory in Implementation Context
    partially_evidenced = career_profile.get("partially_evidenced_competencies", [])
    if len(partially_evidenced) >= 2:
        sample_skills = [s["skill"] for s in partially_evidenced[:3]]
        suggestions.append({
            "suggestion_id": "skill_grounding",
            "category": "Skill Evidence Grounding",
            "priority": "High",
            "reason": "Skills listed only in a static skills section without contextual project bullet points appear unverified to technical interviewers.",
            "evidence_context": f"Competencies like {', '.join(sample_skills)} are listed in your profile but lack supporting project or employment bullet points.",
            "actionable_example": {
                "before": f"Technical Skills: {', '.join(sample_skills)} (never mentioned in project descriptions).",
                "after": f"Project bullet: Applied {sample_skills[0]} to implement scalable caching and asynchronous task queuing."
            },
            "before_after_examples": [
                {
                    "original": f"Technical Skills: {', '.join(sample_skills)}",
                    "suggested": f"Project bullet: Implemented core {sample_skills[0]} module to optimize request handling.",
                    "rationale": "Transforms abstract skill claims into verifiable project evidence."
                }
            ],
            "practical_next_action": "Incorporate your listed technical skills directly into project or work experience bullet points showing how each tool solved a concrete problem."
        })

    # 4. Active Engineering Verbs
    passive_verbs = re.findall(r"\b(?:worked on|helped with|responsible for|assisted in|participated in|maintained|handled)\b", raw_text.lower())
    if passive_verbs:
        found_verb = passive_verbs[0].capitalize()
        suggestions.append({
            "suggestion_id": "active_action_verbs",
            "category": "Action Verb Strength",
            "priority": "Medium",
            "reason": "Passive introductory phrases weaken candidate ownership. Technical resumes should start every bullet with strong engineering verbs.",
            "evidence_context": f"Found {len(passive_verbs)} instances of passive wording like '{passive_verbs[0]}'.",
            "actionable_example": {
                "before": f"{found_verb} building database queries and frontend views.",
                "after": "Architected normalized PostgreSQL schema and optimized analytical queries using composite B-Tree indexes."
            },
            "before_after_examples": [
                {
                    "original": f"{found_verb} application code and database schema.",
                    "suggested": "Architected and deployed production application services with automated unit test coverage.",
                    "rationale": "Emphasizes technical leadership, ownership, and engineering rigor."
                }
            ],
            "practical_next_action": "Replace passive verbs ('responsible for', 'worked on') with authoritative verbs such as 'Architected', 'Engineered', 'Optimized', and 'Automated'."
        })

    # 5. Missing Certifications / Continuing Education
    if not career_profile.get("certifications"):
        suggestions.append({
            "suggestion_id": "credential_reinforcement",
            "category": "Credential Differentiation",
            "priority": "Low",
            "reason": "Industry-recognized vendor certifications (e.g. AWS, Linux Foundation, Google Cloud) validate standardized competencies.",
            "evidence_context": "No formal industry certifications currently documented in resume.",
            "instruction": "Only list certifications and credentials that you have officially completed and can verify via certificate ID or digital badge.",
            "actionable_example": {
                "before": "Certifications section omitted.",
                "after": "Certifications: [Earned Certification Name, e.g. AWS Certified Developer] ([Year]) (Include only credentials officially earned)."
            },
            "practical_next_action": "If applicable to your target role, prepare for an industry certification aligned with your desired career roadmap."
        })

    return suggestions

"""
Career Roadmap Synthesis Module.
Constructs structured short-term (1-3 Months) and medium-term (3-6 Months) career milestones.
Every recommendation is grounded in candidate's verified evidence or explicit evidence gaps.
"""

from typing import Dict, List, Any, Optional


def generate_structured_career_roadmap(
    career_profile: Dict[str, Any],
    skill_gaps: Optional[Dict[str, Any]] = None,
    target_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesizes short-term and medium-term career milestones grounded in candidate
    evidence, prioritized skill gaps, and target role requirements.
    """
    gaps_data = skill_gaps or {}
    role_title = target_role or gaps_data.get("job_title") or "Target Engineering Role"

    # Handle skill_gaps passed as dossier gaps or as full analysis data
    if "prioritized_gaps" in gaps_data:
        prioritized_gaps = gaps_data.get("prioritized_gaps", [])
    elif "gaps" in gaps_data and isinstance(gaps_data["gaps"], dict):
        prioritized_gaps = gaps_data["gaps"].get("prioritized_gaps", [])
    else:
        # Fallback extraction from analysis data missing skills
        missing_req = gaps_data.get("missing_required_skills", [])
        missing_pref = gaps_data.get("missing_preferred_skills", [])
        prioritized_gaps = [
            {"skill_name": s, "priority": "Mandatory", "practical_deliverable": f"Hands-on {s} service module."}
            for s in missing_req
        ] + [
            {"skill_name": s, "priority": "Preferred", "practical_deliverable": f"Applied {s} integration pipeline."}
            for s in missing_pref
        ]

    top_gaps = [g["skill_name"] for g in prioritized_gaps[:3]]
    gap_deliverables = [g.get("practical_deliverable") for g in prioritized_gaps[:2] if g.get("practical_deliverable")]
    
    demonstrated_skills = [s["skill"] for s in career_profile.get("demonstrated_competencies", [])]
    projects = career_profile.get("projects", [])
    primary_proj_title = projects[0].get("title") if projects else "Primary Engineering Project"

    short_term_milestones = []
    medium_term_milestones = []

    # -------------------------------------------------------------------------
    # Short-Term Milestones (1–3 Months / 14–30 Days)
    # -------------------------------------------------------------------------
    if top_gaps:
        primary_gap = top_gaps[0]
        deliv1 = gap_deliverables[0] if gap_deliverables else f"Standalone, tested {primary_gap} portfolio module with automated test coverage."
        short_term_milestones.append({
            "milestone_id": "st_close_primary_gap",
            "phase": "Short-Term (1-3 Months)",
            "timeframe": "Weeks 1–3",
            "estimated_timeline": "Weeks 1–3",
            "title": f"Master Core Prerequisite: {primary_gap}",
            "goal": f"Close the highest-priority competency gap ({primary_gap}) required by target employers.",
            "reason": f"Employer requirement for {role_title} prioritizes {primary_gap}, which currently lacks verifiable implementation evidence in your resume.",
            "supporting_evidence_or_gap": f"Missing evidence for mandatory skill '{primary_gap}'.",
            "priority": "Critical",
            "deliverable": deliv1,
            "deliverables": [deliv1],
            "verification_criteria": f"Code compiles and passes unit test suite; GitHub repository contains clear architectural README."
        })

    if len(top_gaps) > 1:
        secondary_gap = top_gaps[1]
        deliv2 = gap_deliverables[1] if len(gap_deliverables) > 1 else f"Working integration demonstrating {secondary_gap} connected to backend services."
        short_term_milestones.append({
            "milestone_id": "st_close_secondary_gap",
            "phase": "Short-Term (1-3 Months)",
            "timeframe": "Weeks 4–6",
            "estimated_timeline": "Weeks 4–6",
            "title": f"Reinforce Applied Tooling: {secondary_gap}",
            "goal": f"Develop working proficiency in {secondary_gap} and integrate with existing engineering foundations.",
            "reason": f"{secondary_gap} differentiates strong candidates for {role_title} and builds upon your existing verified skills.",
            "supporting_evidence_or_gap": f"Partial or missing evidence for '{secondary_gap}'.",
            "priority": "High",
            "deliverable": deliv2,
            "deliverables": [deliv2],
            "verification_criteria": f"Working end-to-end integration verified locally without runtime errors."
        })

    deliv_resume = "Updated 1-page PDF resume with metric bullets and clickable GitHub repository links."
    short_term_milestones.append({
        "milestone_id": "st_resume_and_github_polish",
        "phase": "Short-Term (1-3 Months)",
        "timeframe": "Weeks 7–8",
        "estimated_timeline": "Weeks 7–8",
        "title": "Evidence-Grounded Resume & Portfolio Publishing",
        "goal": "Update resume bullets with newly created deliverables, quantifiable metrics, and public repository links.",
        "reason": "Recruiters evaluate substantiated outcomes. Documenting your newly verified deliverables with metrics increases interview callback rates.",
        "supporting_evidence_or_gap": "Resume bullets currently lack quantifiable scale metrics and public GitHub links.",
        "priority": "High",
        "deliverable": deliv_resume,
        "deliverables": [deliv_resume],
        "verification_criteria": "Resume parsed through ResumeMatch AI achieves 100% demonstrated evidence for completed project competencies."
    })

    # -------------------------------------------------------------------------
    # Medium-Term Milestones (3–6 Months)
    # -------------------------------------------------------------------------
    deliv_cloud = "Publicly hosted service running on cloud infrastructure (AWS/GCP/Render) with automated test pipeline."
    medium_term_milestones.append({
        "milestone_id": "mt_cloud_and_cicd_deployment",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 3–4",
        "estimated_timeline": "Months 3–4",
        "title": "Production Deployment & Automated CI/CD Pipeline",
        "goal": "Deploy your primary project to a cloud runtime environment using containerization and automated GitHub Actions CI/CD.",
        "reason": "Transitioning from local code execution to automated cloud deployment demonstrates production-readiness to senior hiring committees.",
        "supporting_evidence_or_gap": f"Builds upon verified project '{primary_proj_title}' to demonstrate modern DevOps workflows.",
        "priority": "High",
        "deliverable": deliv_cloud,
        "deliverables": [deliv_cloud],
        "verification_criteria": "Pull request triggers automated build, test matrix passes, and container deploys to production staging."
    })

    deliv_design = "Completed 10 mock technical interview question sessions in ResumeMatch AI Interview Studio."
    medium_term_milestones.append({
        "milestone_id": "mt_interview_system_design",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 4–5",
        "estimated_timeline": "Months 4–5",
        "title": "Technical Interview Loops & System Design Preparation",
        "goal": "Master technical interview questions, architecture trade-offs, and behavioral STAR stories for target role.",
        "reason": "Senior engineering loops evaluate system design scalability, data modeling choices, and clear communication under pressure.",
        "supporting_evidence_or_gap": f"Leverages verified competencies in {', '.join(demonstrated_skills[:3]) if demonstrated_skills else 'software engineering'}.",
        "priority": "High",
        "deliverable": deliv_design,
        "deliverables": [deliv_design],
        "verification_criteria": "Interview studio scoring confirms verified answers without ungrounded factual claims."
    })

    deliv_cert = "Earned certification badge published on LinkedIn and added to resume header."
    medium_term_milestones.append({
        "milestone_id": "mt_industry_certification",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 5–6",
        "estimated_timeline": "Months 5–6",
        "title": "Formal Industry Certification & Domain Authority",
        "goal": "Attain a recognized industry credential (e.g., AWS Certified Developer, CKA, or Azure Developer Associate).",
        "reason": "Provides independent third-party verification of your technical capabilities, distinguishing your profile in recruiter searches.",
        "supporting_evidence_or_gap": "No formal industry certifications currently documented in resume.",
        "priority": "Medium",
        "deliverable": deliv_cert,
        "deliverables": [deliv_cert],
        "verification_criteria": "Official verification URL from certifying vendor (Amazon, Linux Foundation, Google)."
    })

    all_milestones = short_term_milestones + medium_term_milestones

    return {
        "target_role": role_title,
        "short_term": short_term_milestones,
        "medium_term": medium_term_milestones,
        "milestones": all_milestones,
        "short_term_focus": "Closing highest-priority technical requirements and publishing verified project deliverables.",
        "medium_term_focus": "Cloud automation, CI/CD pipelines, technical interview mastery, and industry certifications.",
        "total_milestones_count": len(all_milestones),
        "guidance_philosophy": (
            "Every career milestone is grounded directly in your resume evidence gaps. "
            "Complete short-term portfolio deliverables before attempting medium-term cloud certification exams."
        )
    }

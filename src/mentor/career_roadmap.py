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

    identity = career_profile.get("identity", {})
    has_github = identity.get("has_github", False) or identity.get("has_portfolio", False)
    certs = career_profile.get("certifications", [])
    has_explicit_role = bool(target_role and target_role not in ("Target Engineering Role", "Target Technical Role"))

    short_term_milestones = []
    medium_term_milestones = []

    # -------------------------------------------------------------------------
    # Short-Term Milestones (1–3 Months / 14–30 Days)
    # -------------------------------------------------------------------------
    if top_gaps:
        primary_gap = top_gaps[0]
        deliv1 = gap_deliverables[0] if gap_deliverables else f"Standalone, tested {primary_gap} portfolio module with automated test coverage."
        reason_text = (
            f"Employer requirement for {role_title} prioritizes {primary_gap}, which currently lacks verifiable implementation evidence in your resume."
            if has_explicit_role else
            f"Closing competency gap in {primary_gap} expands verifiable project qualifications."
        )
        short_term_milestones.append({
            "milestone_id": "st_close_primary_gap",
            "phase": "Short-Term (1-3 Months)",
            "timeframe": "Weeks 1–3",
            "estimated_timeline": "Weeks 1–3",
            "title": f"Master Core Prerequisite: {primary_gap}",
            "goal": f"Close the prioritized competency gap ({primary_gap}) through hands-on implementation.",
            "reason": reason_text,
            "supporting_evidence_or_gap": f"Missing evidence for requirement '{primary_gap}'.",
            "guidance_type": "candidate_specific",
            "priority": "Critical",
            "deliverable": deliv1,
            "deliverables": [deliv1],
            "verification_criteria": f"Code compiles and passes unit test suite; repository contains clear architectural documentation."
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
            "reason": f"Reinforces competency profile for {role_title} by connecting {secondary_gap} to existing verified skills.",
            "supporting_evidence_or_gap": f"Partial or missing evidence for '{secondary_gap}'.",
            "guidance_type": "candidate_specific",
            "priority": "High",
            "deliverable": deliv2,
            "deliverables": [deliv2],
            "verification_criteria": f"Working end-to-end integration verified locally without runtime errors."
        })

    # Portfolio & Resume Grounding Milestone
    if has_github:
        resume_gap_note = "Candidate profile has verifiable repository links; keep documentation aligned with newly built deliverables."
        resume_deliv = "Updated technical resume documenting recent project outcomes with verifiable repository links."
        resume_goal = "Update resume experience bullet points with measured deliverables and updated repository documentation."
    else:
        resume_gap_note = "Profile currently lacks public repository links for direct source code inspection."
        resume_deliv = "Updated 1-page PDF resume with measured project bullets and clickable public repository links."
        resume_goal = "Publish a public GitHub repository and update resume bullets with verifiable implementation links."

    short_term_milestones.append({
        "milestone_id": "st_resume_and_github_polish",
        "phase": "Short-Term (1-3 Months)",
        "timeframe": "Weeks 7–8",
        "estimated_timeline": "Weeks 7–8",
        "title": "Evidence-Grounded Resume & Portfolio Publishing",
        "goal": resume_goal,
        "reason": "Clear technical documentation and verifiable code links allow engineering evaluators to directly review implementation scope and code quality.",
        "supporting_evidence_or_gap": resume_gap_note,
        "guidance_type": "candidate_specific" if not has_github else "general_career_development",
        "priority": "High",
        "deliverable": resume_deliv,
        "deliverables": [resume_deliv],
        "verification_criteria": "Resume parsed through ResumeMatch AI achieves verified demonstrated evidence for completed project competencies."
    })

    # -------------------------------------------------------------------------
    # Medium-Term Milestones (3–6 Months)
    # -------------------------------------------------------------------------
    # Cloud Deployment Milestone
    has_cloud_skill = any(s.lower() in ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd"] for s in demonstrated_skills)
    deliv_cloud = "Publicly hosted service running on cloud infrastructure (AWS/GCP/Render) with automated test pipeline."
    cloud_gap_note = (
        f"Builds upon verified project '{primary_proj_title}' to demonstrate modern automated deployment and containerization practices."
        if has_cloud_skill else
        f"Optional development: deploy '{primary_proj_title}' using containerization if targeting cloud or backend deployment roles."
    )

    medium_term_milestones.append({
        "milestone_id": "mt_cloud_and_cicd_deployment",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 3–4",
        "estimated_timeline": "Months 3–4",
        "title": "Production Deployment & Automated CI/CD Pipeline",
        "goal": "Deploy your primary project to a cloud runtime environment using containerization and automated CI/CD workflows.",
        "reason": "Transitioning from local code execution to automated cloud deployment demonstrates production readiness for engineering roles.",
        "supporting_evidence_or_gap": cloud_gap_note,
        "guidance_type": "candidate_specific" if any("ci/cd" in g.lower() or "docker" in g.lower() or "cloud" in g.lower() for g in top_gaps) else "general_career_development",
        "priority": "High",
        "deliverable": deliv_cloud,
        "deliverables": [deliv_cloud],
        "verification_criteria": "Automated build and test suite executes successfully upon pull request; service responds to health-check endpoints."
    })

    deliv_design = "Completed 10 mock technical interview question sessions in ResumeMatch AI Interview Studio."
    medium_term_milestones.append({
        "milestone_id": "mt_interview_system_design",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 4–5",
        "estimated_timeline": "Months 4–5",
        "title": "Technical Interview Loops & System Design Preparation",
        "goal": "Prepare for technical interview questions, architecture trade-offs, and behavioral STAR stories for target role.",
        "reason": "Engineering interview loops assess structured problem-solving, architectural trade-offs, and clear communication.",
        "supporting_evidence_or_gap": f"Leverages verified competencies in {', '.join(demonstrated_skills[:3]) if demonstrated_skills else 'software engineering'}.",
        "guidance_type": "general_career_development",
        "priority": "High",
        "deliverable": deliv_design,
        "deliverables": [deliv_design],
        "verification_criteria": "Interview studio scoring confirms verified answers without ungrounded factual claims."
    })

    # Certification Milestone (Grounded in Actual Credentials)
    if certs:
        existing_cert_title = certs[0].get("title", "Technical Certification")
        cert_gap_note = f"Candidate holds verified credential '{existing_cert_title}'; optional advanced specialization can deepen domain expertise if desired."
        cert_goal = f"Optionally pursue advanced specialization building upon {existing_cert_title} if aligned with target career path."
        cert_deliv = "Advanced credential badge or specialized portfolio domain module."
    else:
        cert_gap_note = "No formal industry certifications currently documented in profile; vendor certification is optional unless explicitly required by employers."
        cert_goal = "Optionally attain a recognized industry certification if seeking third-party validation for target cloud or systems roles."
        cert_deliv = "Optional earned certification badge published on professional profile."

    medium_term_milestones.append({
        "milestone_id": "mt_industry_certification",
        "phase": "Medium-Term (3-6 Months)",
        "timeframe": "Months 5–6",
        "estimated_timeline": "Months 5–6",
        "title": "Formal Industry Certification (Optional Domain Validation)",
        "goal": cert_goal,
        "reason": "Where explicitly required by employers, third-party vendor credentials validate standardized competencies in cloud and infrastructure domains.",
        "supporting_evidence_or_gap": cert_gap_note,
        "guidance_type": "general_career_development",
        "priority": "Medium",
        "deliverable": cert_deliv,
        "deliverables": [cert_deliv],
        "verification_criteria": "Official verification URL or digital badge from certifying vendor."
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

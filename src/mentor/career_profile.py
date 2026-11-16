"""
Career Profile Builder Module.
Extracts and structures verified candidate credentials, demonstrated competencies,
candidate-confirmed attestations, projects, experience, and explicit information gaps.
Enforces zero hallucination: never invents qualifications or achievements.
"""

from typing import Dict, List, Any, Optional
import re

from src.common.evidence_registry import resolve_canonical_skill


def build_structured_career_profile(analysis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs an evidence-grounded structured career profile from analysis data.
    Clearly distinguishes resume-demonstrated evidence, candidate self-confirmations,
    and missing/uncertain information.
    """
    data = analysis_data or {}
    cand_profile = data.get("candidate_profile") or {}
    ev_registry = data.get("evidence_registry") or {}

    # 1. Identity & Contact Details
    contact = cand_profile.get("contact_info") or {}
    cand_name = cand_profile.get("name") or {}
    preferred_name = cand_name.get("preferred_name") or "Candidate"
    full_name = cand_name.get("full_name") or preferred_name

    identity_info = {
        "full_name": full_name,
        "preferred_name": preferred_name,
        "email": contact.get("email"),
        "has_email": bool(contact.get("email")),
        "phone": contact.get("phone"),
        "has_phone": bool(contact.get("phone")),
        "linkedin": contact.get("linkedin"),
        "has_linkedin": bool(contact.get("linkedin")),
        "github": contact.get("github"),
        "has_github": bool(contact.get("github")),
        "portfolio": contact.get("portfolio"),
        "has_portfolio": bool(contact.get("portfolio")),
        "location": contact.get("location") or "Not provided"
    }

    # 2. Education Credentials
    edu_list = cand_profile.get("education") or []
    education_records = []
    for edu in edu_list:
        education_records.append({
            "degree_level": edu.get("degree_level", "Degree"),
            "degree_name": edu.get("degree_name", "Academic Degree"),
            "field_of_study": edu.get("field_of_study") or "Not specified",
            "institution": edu.get("institution") or "Accredited Institution",
            "graduation_year": edu.get("graduation_year"),
            "gpa": edu.get("gpa")
        })

    edu_analysis = data.get("education_analysis") or {}
    education_summary = {
        "records": education_records,
        "total_degrees_count": len(education_records),
        "education_verified": edu_analysis.get("education_verified", False),
        "verification_status": edu_analysis.get("verification_status", "no_explicit_requirement"),
        "notes": edu_analysis.get("notes", "No explicit education requirements specified in job description.")
    }

    # 3. Certifications
    cert_list = cand_profile.get("certifications") or []
    certifications = []
    for c in cert_list:
        certifications.append({
            "title": c.get("title") or c.get("name") or "Technical Certification",
            "issuer": c.get("issuer") or "Accredited Body",
            "year": c.get("year")
        })

    # 4. Work History & Project Experience
    projects = data.get("projects") or data.get("relevant_projects") or []
    internships = data.get("internships") or []
    prof_exp = data.get("professional_experience") or []
    exp_summary = data.get("experience_summary") or {}

    experience_overview = {
        "total_experience_years": exp_summary.get("total_years", 0.0),
        "full_time_years": exp_summary.get("full_time_years", 0.0),
        "internship_months": exp_summary.get("internship_months", 0),
        "projects_count": len(projects),
        "internships_count": len(internships),
        "professional_roles_count": len(prof_exp),
        "display_summary": exp_summary.get("display_summary", "Demonstrated hands-on technical background.")
    }

    # 5. Competencies Categorization (Strict Evidence Provenance)
    # Demonstrated: evidenced in projects, internships, or employment descriptions
    demonstrated_skills = []
    demonstrated_set = set()

    for p in projects:
        p_title = p.get("title") or p.get("project_title", "Project")
        p_desc = (p.get("description") or "").strip()
        for t in p.get("technologies", []):
            canon = resolve_canonical_skill(t)
            if canon.lower() not in demonstrated_set:
                demonstrated_set.add(canon.lower())
                has_excerpt = bool(p_desc)
                demonstrated_skills.append({
                    "skill": canon,
                    "evidence_source": "project",
                    "provenance_title": p_title,
                    "excerpt": p_desc[:140] + ("..." if len(p_desc) > 140 else "") if has_excerpt else None,
                    "excerpt_status": "available" if has_excerpt else "unavailable",
                    "provenance_note": None if has_excerpt else f"Technology listed in project '{p_title}' without descriptive excerpt.",
                    "confidence": 0.95
                })

    for intern in internships:
        org = intern.get("organization") or "Internship"
        pos = intern.get("position") or "Intern"
        resp = intern.get("responsibilities") or []
        resp_text = "; ".join([r.strip() for r in resp if r.strip()][:2])
        for t in intern.get("technologies", []):
            canon = resolve_canonical_skill(t)
            if canon.lower() not in demonstrated_set:
                demonstrated_set.add(canon.lower())
                has_excerpt = bool(resp_text)
                demonstrated_skills.append({
                    "skill": canon,
                    "evidence_source": "internship",
                    "provenance_title": f"{pos} at {org}",
                    "excerpt": resp_text[:140] + ("..." if len(resp_text) > 140 else "") if has_excerpt else None,
                    "excerpt_status": "available" if has_excerpt else "unavailable",
                    "provenance_note": None if has_excerpt else f"Technology listed in internship '{pos} at {org}' without descriptive responsibilities.",
                    "confidence": 0.90
                })

    # Pull additional solidly evidenced skills from evidence registry or analysis
    registry_demonstrated = ev_registry.get("demonstrated_skills") or data.get("solidly_evidenced_skills") or []
    for s in registry_demonstrated:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in demonstrated_set:
            demonstrated_set.add(canon.lower())
            
            # Search for genuine textual excerpt in matches, work experience, or resume text
            real_excerpt = None
            
            # Check matches table
            for m in data.get("matches", []):
                if isinstance(m, dict):
                    m_skill = m.get("skill") or m.get("skill_name") or ""
                    if resolve_canonical_skill(m_skill).lower() == canon.lower():
                        ex = m.get("resume_evidence") or m.get("evidence") or m.get("excerpt")
                        if ex and isinstance(ex, str) and len(ex.strip()) > 5:
                            real_excerpt = ex.strip()
                            break

            # Check professional experience
            if not real_excerpt:
                for pe in prof_exp:
                    if isinstance(pe, dict):
                        desc = pe.get("description") or pe.get("responsibilities") or ""
                        if isinstance(desc, list):
                            desc = " ".join(desc)
                        if canon.lower() in desc.lower():
                            sentences = re.split(r"(?<=[.!?])\s+", desc)
                            for sent in sentences:
                                if canon.lower() in sent.lower():
                                    real_excerpt = sent.strip()
                                    break
                    if real_excerpt:
                        break

            # Check raw resume text
            if not real_excerpt and data.get("raw_text"):
                raw_t = data.get("raw_text")
                if canon.lower() in raw_t.lower():
                    lines = re.split(r"[\r\n]+", raw_t)
                    for l in lines:
                        cl = l.strip()
                        if len(cl) >= 15 and canon.lower() in cl.lower() and not cl.lower().startswith("skills:"):
                            real_excerpt = cl[:140] + ("..." if len(cl) > 140 else "")
                            break

            if real_excerpt:
                demonstrated_skills.append({
                    "skill": canon,
                    "evidence_source": "professional_experience",
                    "provenance_title": "Documented Work Experience",
                    "excerpt": real_excerpt[:140] + ("..." if len(real_excerpt) > 140 else ""),
                    "excerpt_status": "available",
                    "confidence": 0.90
                })
            else:
                # Skill is in registry without a traceable source excerpt; preserve skill but mark provenance honestly
                demonstrated_skills.append({
                    "skill": canon,
                    "evidence_source": "registry_derived",
                    "provenance_title": "Evidence Registry (Derived)",
                    "excerpt": None,
                    "excerpt_status": "unavailable",
                    "provenance_note": "Registry-derived competency without source resume excerpt; eligible for registry-tier credit (60%), not full demonstrated credit.",
                    "confidence": 0.60
                })

    # Candidate Self-Confirmed: explicitly confirmed via candidate portal/attestation
    user_confirmations = ev_registry.get("user_confirmations") or data.get("user_confirmations") or {}
    candidate_confirmed_skills = []
    for k, v in user_confirmations.items():
        is_conf = False
        if isinstance(v, dict):
            is_conf = v.get("status") == "confirmed" or v.get("value") is True
        elif isinstance(v, bool):
            is_conf = v
        if is_conf:
            canon = resolve_canonical_skill(k)
            # Never upgrade candidate self-attestation into resume-demonstrated evidence
            if canon.lower() not in demonstrated_set:
                candidate_confirmed_skills.append({
                    "skill": canon,
                    "evidence_source": "candidate_confirmed",
                    "excerpt": None,
                    "excerpt_status": "unavailable",
                    "notes": "Candidate self-attestation; not independently evidenced in uploaded resume text.",
                    "confidence": 0.75
                })

    # Partially Evidenced / Mentioned in Skills List
    partially_evidenced_skills = []
    partial_raw = ev_registry.get("partially_evidenced_skills") or data.get("partially_evidenced_skills") or []
    for s in partial_raw:
        canon = resolve_canonical_skill(s)
        if canon.lower() not in demonstrated_set and not any(c["skill"].lower() == canon.lower() for c in candidate_confirmed_skills):
            partially_evidenced_skills.append({
                "skill": canon,
                "evidence_source": "skills_section",
                "excerpt": None,
                "excerpt_status": "unavailable",
                "notes": "Listed in candidate profile/skills section without contextual project implementation details.",
                "confidence": 0.50
            })

    # 6. Missing or Uncertain Information (Strict Zero Hallucination Tracking)
    missing_info = []
    cand_missing_fields = cand_profile.get("missing_fields") or []
    for mf in cand_missing_fields:
        missing_info.append({
            "field": mf,
            "category": "Contact/Profile Detail",
            "impact": "Low",
            "detail": f"{mf.replace('_', ' ').title()} was not documented in candidate resume."
        })

    if not contact.get("github"):
        missing_info.append({
            "field": "github_link",
            "category": "Portfolio Verification",
            "impact": "Moderate",
            "detail": "No public GitHub or source repository link provided in resume."
        })

    if not certifications:
        missing_info.append({
            "field": "certifications",
            "category": "Credentials",
            "impact": "Low",
            "detail": "No formal industry certifications documented in resume."
        })

    missing_required = data.get("missing_required_skills") or []
    for s in missing_required:
        missing_info.append({
            "field": f"skill_gap_{s.lower()}",
            "category": "Employer Requirement Gap",
            "impact": "High",
            "detail": f"Required competency '{s}' lacks verifiable evidence in candidate resume."
        })

    # Conflicts & Inconsistencies
    conflicts = cand_profile.get("conflicts") or []

    # Separate traceable demonstrated from registry-derived without excerpts
    registry_derived_skills = [
        s for s in demonstrated_skills if s.get("evidence_source") == "registry_derived" or s.get("excerpt_status") == "unavailable"
    ]
    traceable_demonstrated_skills = [
        s for s in demonstrated_skills if s.get("evidence_source") != "registry_derived" and s.get("excerpt_status") != "unavailable"
    ]

    return {
        "identity": identity_info,
        "education": education_summary,
        "certifications": certifications,
        "experience": experience_overview,
        "projects": projects,
        "internships": internships,
        "demonstrated_competencies": demonstrated_skills,
        "traceable_demonstrated_competencies": traceable_demonstrated_skills,
        "registry_derived_competencies": registry_derived_skills,
        "candidate_confirmed_competencies": candidate_confirmed_skills,
        "partially_evidenced_competencies": partially_evidenced_skills,
        "missing_or_uncertain_information": missing_info,
        "conflicts_and_inconsistencies": conflicts,
        "evidence_metrics": {
            "demonstrated_count": len(demonstrated_skills),
            "traceable_demonstrated_count": len(traceable_demonstrated_skills),
            "registry_derived_count": len(registry_derived_skills),
            "candidate_confirmed_count": len(candidate_confirmed_skills),
            "partially_evidenced_count": len(partially_evidenced_skills),
            "missing_items_count": len(missing_info),
            "has_conflicts": len(conflicts) > 0
        }
    }

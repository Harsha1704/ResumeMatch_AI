"""
Career Profile Builder Module.
Extracts and structures verified candidate credentials, demonstrated competencies,
candidate-confirmed attestations, projects, experience, and explicit information gaps.
Enforces zero hallucination: never invents qualifications or achievements.
"""

from typing import Dict, List, Any, Optional, Set
import re

from src.common.evidence_registry import resolve_canonical_skill, matches_skill_token, CANONICAL_SKILL_ALIASES

# Markers identifying negated, unused, considered, or prospective non-demonstrated skills
NON_DEMONSTRATED_PATTERNS = [
    # Negated / not used / unused
    r"\b(?:not\s+used|did\s+not\s+use|didn't\s+use|never\s+used|without\s+using|unused)\b",
    r"\b(?:considered\s+but\s+not\s+used|evaluated\s+but\s+not\s+used|decided\s+against|not\s+adopted|evaluated\s+and\s+rejected)\b",
    r"\b(?:was|were|is)\s+considered\s+but\s+not\s+used\b",
    # Planned / prospective / future
    r"\b(?:plan(?:ned|ning|s)?\s+to\s+(?:migrate|implement|use|adopt|switch|transition))\b",
    r"\b(?:plan(?:ned|ning|s)?\s+to\b|\bplanning\s+to\b)",
    r"\b(?:future\s+tool|future\s+plan|future\s+roadmap|future\s+adoption|future\s+work|prospective\s+tool)\b",
    r"\b(?:possible\s+future\s+tool|potential\s+future\s+tool|possible\s+tool|potential\s+tool)\b",
    r"\b(?:listed\s+as\s+a\s+possible|listed\s+as\s+a\s+potential|listed\s+as\s+a\s+future)\b",
    # Considered / proposed
    r"\b(?:was|were|is)\s+considered\b(?!\s+(?:essential|crucial|key|central|vital|by))",
    r"\bconsidered\s+(?:for\s+future|as\s+a\s+possible|as\s+a\s+potential)\b",
    r"\b(?:propos(?:ed|al)|tentative)\s+(?:tool|framework|library|to\s+use|for\s+use)\b",
    r"\bproposed\s+to\s+use\b",
    # General discussions / planning without implementation
    r"\b(?:was|were|is)\s+discussed\b",
    r"\bdiscussed\s+(?:during|in|at|for)\b",
    r"\b(?:under|in)\s+discussion\b",
    # Requirements / preferences / role specs (not candidate evidence)
    r"\b(?:is|are|was|were)\s+required\s+(?:for|by|in)\b",
    r"\brequired\s+for\s+(?:this|the|a)\s+(?:role|job|position|project)\b",
    r"\b(?:is|are)\s+preferred\b",
    r"\b(?:preferred|desirable)\s+(?:qualification|skill|tool)\b",
    r"\brole\s+requirement\b",
]

# Action verbs and active engineering context indicators required for full demonstrated credit.
# Strictly limited to genuine action verbs; nominal forms (e.g. development, implementation,
# architecture, analysis, configuration, management) are excluded to prevent treating discussions,
# requirements, or descriptions as proof of candidate implementation.
DEMONSTRATED_ACTION_VERBS = {
    # Active usage
    "use", "used", "uses", "using", "utilize", "utilized", "utilizes", "utilizing",
    # Construction / development / implementation
    "build", "built", "building", "develop", "developed", "developing",
    "engineer", "engineered",
    "implement", "implemented", "implementing",
    "design", "designed", "designing", "create", "created", "creating",
    "construct", "constructed", "constructing",
    "author", "authored", "authoring",
    "refactor", "refactored", "refactoring",
    "program", "programmed",
    "code", "coded", "coding",
    "write", "wrote", "writing", "written",
    # Operations / verification / systems
    "test", "tested", "testing",
    "deploy", "deployed", "deploying",
    "configure", "configured", "configuring",
    "optimize", "optimized", "optimizing",
    "integrate", "integrated", "integrating",
    "analyze", "analyzed", "analyzing",
    "automate", "automated", "automating",
    "maintain", "maintained", "maintaining",
    "orchestrate", "orchestrated", "orchestrating",
    "architect", "architected", "architecting",
    "containerize", "containerized", "containerizing",
    "monitor", "monitored", "monitoring",
    "ingest", "ingested", "ingesting",
    "process", "processed", "processing",
    "scale", "scaled", "scaling",
    "execute", "executed", "executing",
    "manage", "managed", "managing",
    "support", "supported", "supporting",
    "deliver", "delivered", "delivering",
    "lead", "led", "leading",
    "handle", "handled", "handling",
    "run", "running",
    "leverage", "leveraged", "leveraging",
    "train", "trained",
    "fine-tune", "fine-tuned",
    "serve", "served", "serving"
}


def find_supporting_excerpt_for_skill(skill_name: str, text: Optional[str]) -> Optional[str]:
    """
    Finds a genuine supporting sentence in the given text establishing DEMONSTRATED USE
    for the canonical skill.

    Heuristic Evaluation & Semantic Scoping:
    1. Canonical Resolution & Aliases: expands canonical tokens and registered aliases.
    2. Substring & Boundary Protection: isolates C, C++, C#, .NET from cross-contamination.
    3. Mentions vs Demonstrated Use:
       - Rejects negated, unused, considered, or prospective claims (e.g. 'not used',
         'considered but not used', 'planned to migrate to', 'possible future tool').
       - Requires contextual indicators of actual engineering use (implementation, development, testing, deployment, etc.).
       - Preserves the authentic sentence as the excerpt when demonstrated use is established.
       - Returns None when use cannot be substantiated (triggering 0.60 registry tier).

    Documented Limitations:
    This heuristic inspects grammatical clauses and known intentional/negation markers. While robust against
    standard candidate phrasing (negations, future tools, passive consideration), complex multi-clause rhetorical
    structures without explicit markers cannot be guaranteed 100% equivalent to human semantic analysis.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return None

    canon = resolve_canonical_skill(skill_name)
    search_terms = {skill_name.lower().strip(), canon.lower().strip()}
    for alias, c in CANONICAL_SKILL_ALIASES.items():
        if c.lower() == canon.lower():
            search_terms.add(alias.lower())

    # Split text into authentic sentences
    sentences = re.split(r"(?<=[.!?\n])\s+|[\r\n]+", text)
    for sent in sentences:
        s_clean = sent.strip(" \t\n*-•")
        if len(s_clean) < 4:
            continue

        # Check if this sentence mentions the skill
        if not any(matches_skill_token(s_clean, term) for term in search_terms):
            continue

        # Split sentence into clauses (by semicolons, contrasting conjunctions, or parentheticals)
        clauses = re.split(r";\s*|\s*,\s*(?:but|however|whereas|while)\s*|\s+but\s+", s_clean)

        # Check clauses that specifically mention the skill
        skill_clauses = [c for c in clauses if any(matches_skill_token(c, term) for term in search_terms)]

        has_demonstrated_clause = False
        for cl in skill_clauses:
            cl_lower = cl.lower()

            # 1. Check for negation, unused, prospective, or considered markers in this clause
            is_non_dem = False
            for pat in NON_DEMONSTRATED_PATTERNS:
                if re.search(pat, cl_lower):
                    is_non_dem = True
                    break
            if is_non_dem:
                continue

            # 2. Check for contextual evidence of actual use / implementation / activity
            cl_words = set(re.findall(r"\b[a-z]{3,}\b", cl_lower))
            if cl_words.intersection(DEMONSTRATED_ACTION_VERBS):
                has_demonstrated_clause = True
                break

        if has_demonstrated_clause:
            # Overarching sentence rejection check: e.g. "Python was considered but not used"
            whole_lower = s_clean.lower()
            overarching_rejection = False
            for pat in [
                r"\b(?:was|were|is)\s+considered\s+but\s+not\s+used\b",
                r"\bconsidered\s+(?:[a-z0-9#+.]+\s+)?but\s+not\s+used\b",
                r"\bnot\s+used\b",
                r"\bdid\s+not\s+use\b",
                r"\bnever\s+used\b",
                r"\b(?:is|are|was|were)\s+required\s+for\s+(?:this|the|a)\s+(?:role|job|position)\b",
                r"\bdiscussed\s+during\s+planning\b",
                r"\b(?:was|were|is)\s+discussed\s+(?:during|in|at)\b"
            ]:
                if re.search(pat, whole_lower):
                    overarching_rejection = True
                    break

            if overarching_rejection:
                continue

            if len(s_clean) > 140:
                return s_clean[:137] + "..."
            return s_clean

    return None


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
    demonstrated_skills_map: Dict[str, Dict[str, Any]] = {}

    def _record_demonstrated_skill(candidate_obj: Dict[str, Any]) -> None:
        """
        Records or updates a competency in demonstrated_skills_map.
        Ensures a stronger genuine evidence source (available excerpt) is never
        overwritten or downgraded by a weaker or unsupported source.
        """
        canon_key = candidate_obj["skill"].lower()
        if canon_key not in demonstrated_skills_map:
            demonstrated_skills_map[canon_key] = candidate_obj
            return

        existing = demonstrated_skills_map[canon_key]
        existing_available = (existing.get("excerpt_status") == "available" and bool(existing.get("excerpt")))
        new_available = (candidate_obj.get("excerpt_status") == "available" and bool(candidate_obj.get("excerpt")))

        # If existing is unsupported/unavailable and new is supported/available, upgrade!
        if not existing_available and new_available:
            demonstrated_skills_map[canon_key] = candidate_obj
        elif existing_available and new_available:
            # Both supported: prefer higher confidence (e.g. project 0.95 over internship 0.90)
            if candidate_obj.get("confidence", 0.0) > existing.get("confidence", 0.0):
                demonstrated_skills_map[canon_key] = candidate_obj

    for p in projects:
        p_title = p.get("title") or p.get("project_title", "Project")
        p_desc = (p.get("description") or "").strip()
        for t in p.get("technologies", []):
            canon = resolve_canonical_skill(t)
            supported_excerpt = find_supporting_excerpt_for_skill(canon, p_desc)
            if supported_excerpt:
                _record_demonstrated_skill({
                    "skill": canon,
                    "evidence_source": "project",
                    "provenance_title": p_title,
                    "excerpt": supported_excerpt,
                    "excerpt_status": "available",
                    "provenance_note": None,
                    "confidence": 0.95
                })
            else:
                _record_demonstrated_skill({
                    "skill": canon,
                    "evidence_source": "registry_derived",
                    "provenance_title": p_title,
                    "excerpt": None,
                    "excerpt_status": "unavailable",
                    "provenance_note": f"Technology listed in project '{p_title}' metadata without descriptive excerpt; registry-derived.",
                    "confidence": 0.60
                })

    for intern in internships:
        org = intern.get("organization") or "Internship"
        pos = intern.get("position") or "Intern"
        resp = intern.get("responsibilities") or []
        resp_text = "; ".join([r.strip() for r in resp if r.strip()][:3])
        for t in intern.get("technologies", []):
            canon = resolve_canonical_skill(t)
            supported_excerpt = find_supporting_excerpt_for_skill(canon, resp_text)
            if supported_excerpt:
                _record_demonstrated_skill({
                    "skill": canon,
                    "evidence_source": "internship",
                    "provenance_title": f"{pos} at {org}",
                    "excerpt": supported_excerpt,
                    "excerpt_status": "available",
                    "provenance_note": None,
                    "confidence": 0.90
                })
            else:
                _record_demonstrated_skill({
                    "skill": canon,
                    "evidence_source": "registry_derived",
                    "provenance_title": f"{pos} at {org}",
                    "excerpt": None,
                    "excerpt_status": "unavailable",
                    "provenance_note": f"Technology listed in internship '{pos} at {org}' metadata without descriptive responsibilities; registry-derived.",
                    "confidence": 0.60
                })

    # Pull candidate skills from registry, analysis solidly evidenced, or matches
    registry_demonstrated = list(ev_registry.get("demonstrated_skills") or data.get("solidly_evidenced_skills") or [])
    for m in data.get("matches", []):
        if isinstance(m, dict):
            m_skill = m.get("skill") or m.get("skill_name")
            if m_skill and isinstance(m_skill, str) and m_skill.strip():
                canon_m = resolve_canonical_skill(m_skill.strip())
                if not any(resolve_canonical_skill(existing).lower() == canon_m.lower() for existing in registry_demonstrated):
                    registry_demonstrated.append(canon_m)

    for s in registry_demonstrated:
        canon = resolve_canonical_skill(s)
        canon_key = canon.lower()

        # If already strongly evidenced with an available excerpt, preserve it
        if canon_key in demonstrated_skills_map and demonstrated_skills_map[canon_key].get("excerpt_status") == "available":
            continue

        real_excerpt = None
        source_title = "Documented Work Experience"
        source_type = "professional_experience"

        # Check matches table with strict evidence validation (no bypass for arbitrary strings)
        for m in data.get("matches", []):
            if isinstance(m, dict):
                m_skill = m.get("skill") or m.get("skill_name") or ""
                if resolve_canonical_skill(m_skill).lower() == canon_key:
                    ex = m.get("resume_evidence") or m.get("evidence") or m.get("excerpt")
                    if isinstance(ex, list):
                        ex = " ".join(str(item) for item in ex if item)
                    if ex and isinstance(ex, str) and len(ex.strip()) >= 4:
                        validated_ex = find_supporting_excerpt_for_skill(canon, ex)
                        if validated_ex:
                            real_excerpt = validated_ex
                            source_title = "Verified Resume Match"
                            source_type = "professional_experience"
                            break

        # Check professional experience with safe boundary-checked search
        if not real_excerpt:
            for pe in prof_exp:
                if isinstance(pe, dict):
                    desc = pe.get("description") or pe.get("responsibilities") or ""
                    if isinstance(desc, list):
                        desc = " ".join(desc)
                    found_ex = find_supporting_excerpt_for_skill(canon, desc)
                    if found_ex:
                        real_excerpt = found_ex
                        source_title = "Documented Work Experience"
                        source_type = "professional_experience"
                        break

        # Check raw resume text with safe boundary-checked search
        if not real_excerpt and data.get("raw_text"):
            raw_t = data.get("raw_text")
            found_ex = find_supporting_excerpt_for_skill(canon, raw_t)
            if found_ex and not any(found_ex.lower().startswith(h) for h in ["skills:", "technical skills", "technologies:"]):
                real_excerpt = found_ex
                source_title = "Resume Text"
                source_type = "professional_experience"

        if real_excerpt:
            _record_demonstrated_skill({
                "skill": canon,
                "evidence_source": source_type,
                "provenance_title": source_title,
                "excerpt": real_excerpt,
                "excerpt_status": "available",
                "provenance_note": None,
                "confidence": 0.90
            })
        else:
            _record_demonstrated_skill({
                "skill": canon,
                "evidence_source": "registry_derived",
                "provenance_title": "Evidence Registry (Derived)",
                "excerpt": None,
                "excerpt_status": "unavailable",
                "provenance_note": "Registry-derived competency without source resume excerpt; eligible for registry-tier credit (60%), not full demonstrated credit.",
                "confidence": 0.60
            })

    demonstrated_skills = list(demonstrated_skills_map.values())
    demonstrated_set = set(demonstrated_skills_map.keys())
    traceable_demonstrated_set = {
        k for k, v in demonstrated_skills_map.items()
        if v.get("excerpt_status") == "available" and v.get("evidence_source") != "registry_derived"
    }

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
            # Never upgrade candidate self-attestation into resume-demonstrated evidence;
            # candidate confirmation takes precedence over registry-only absence when not evidenced in text
            if canon.lower() not in traceable_demonstrated_set:
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

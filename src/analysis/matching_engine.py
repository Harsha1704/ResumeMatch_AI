"""
Master Resume Matching & Skill Gap Analysis Engine.
Integrates:
- Document Parsing (PDF, DOCX, TXT)
- Job Description Analysis (REQUIRED, PREFERRED, UNSPECIFIED tiers)
- Supervised ML Compatibility Prediction (Logistic Regression)
- Skill Gap & Partial Evidence Categorization with Strict Mathematical Accounting
- Experience & Structured Project Alignment
- Resume Improvement Recommendations & Verified Learning Resources
Zero LLM reliance. Fully deterministic.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging
import uuid
import re

logger = logging.getLogger(__name__)

from src.analysis.resume_parser import parse_resume
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.skill_gap import SkillGapAnalyzer
from src.analysis.experience_analyzer import ExperienceAnalyzer
from src.analysis.recommendation_engine import RecommendationEngine
from src.models.inference import get_inference_engine, CLASSES
from src.services.challenger_service import get_challenger_service
from src.common.evidence_registry import build_unified_evidence_registry


ALLOWED_MATCH_CLASSIFICATIONS = {
    "fully_supported",
    "partially_supported",
    "explicitly_mentioned",
    "missing_evidence",
    "conflicting_evidence",
    "candidate_confirmed"
}

ALLOWED_EVIDENCE_SOURCES = {
    "project",
    "internship",
    "professional_experience",
    "skills_section",
    "candidate_confirmed",
    "contradictory_claim",
    "none"
}

DEGREE_LEVEL_HIERARCHY = {
    "Doctorate": 4,
    "Master's": 3,
    "Bachelor's": 2,
    "Associate": 1,
    "Not specified": 0
}

STEM_AND_TECH_FIELDS = {
    "computer science", "software engineering", "information technology",
    "electrical engineering", "electronics", "data science", "artificial intelligence",
    "machine learning", "cybersecurity", "engineering", "mathematics",
    "statistics", "physics", "stem"
}


def verify_structured_education(
    candidate_education: List[Dict[str, Any]],
    job_education_requirements: List[str]
) -> Dict[str, Any]:
    """
    Verifies candidate education credentials against actual job education requirements:
    - Distinguishes a mere degree keyword mention from a verified matching qualification.
    - Compares degree level and field of study specialization.
    - Handles positive, negative, unrelated-degree, missing-education, and inconclusive cases.
    """
    candidate_degrees = [e.get("degree_name") for e in candidate_education if e.get("degree_name")]

    # 1. Check if job has explicit education requirements
    has_explicit_job_req = bool(
        job_education_requirements and
        not any("no explicit education" in r.lower() for r in job_education_requirements)
    )

    if not has_explicit_job_req:
        if candidate_education:
            return {
                "education_verified": False,
                "verification_status": "no_explicit_requirement",
                "candidate_degrees": candidate_degrees,
                "detected_job_requirements": job_education_requirements,
                "notes": "No explicit education requirements specified in job description; candidate credentials recorded."
            }
        else:
            return {
                "education_verified": False,
                "verification_status": "no_explicit_requirement",
                "candidate_degrees": [],
                "detected_job_requirements": job_education_requirements,
                "notes": "Education details not confidently identified"
            }

    # 2. Job has explicit requirements: check if candidate has any documented education
    if not candidate_education:
        return {
            "education_verified": False,
            "verification_status": "missing_education",
            "candidate_degrees": [],
            "detected_job_requirements": job_education_requirements,
            "notes": "Missing education: Job requires formal degree qualifications, but no education credentials were documented in candidate resume."
        }

    # Parse required degree level and required fields from job requirements
    combined_job_req_text = " ".join(job_education_requirements).lower()

    required_level = "Bachelor's"
    if any(k in combined_job_req_text for k in ["ph.d", "phd", "doctorate", "doctoral"]):
        required_level = "Doctorate"
    elif any(k in combined_job_req_text for k in ["master", "m.tech", "m.s", "m.e", "msc", "mba", "postgraduate"]):
        required_level = "Master's"
    elif any(k in combined_job_req_text for k in ["bachelor", "b.tech", "b.s", "b.e", "bsc", "undergraduate"]):
        required_level = "Bachelor's"
    elif any(k in combined_job_req_text for k in ["associate", "diploma"]):
        required_level = "Associate"

    required_rank = DEGREE_LEVEL_HIERARCHY.get(required_level, 2)
    job_specifies_stem = any(f in combined_job_req_text for f in [
        "computer science", "engineering", "technical", "information technology",
        "stem", "software", "data science", "quantitative", "math"
    ])

    best_match = None
    unrelated_match = None

    for edu in candidate_education:
        cand_level = edu.get("degree_level", "Not specified")
        cand_rank = DEGREE_LEVEL_HIERARCHY.get(cand_level, 0)
        cand_field = (edu.get("field_of_study") or "").lower()
        cand_deg_name = (edu.get("degree_name") or "").lower()
        cand_full = f"{cand_deg_name} {cand_field}"

        level_ok = cand_rank >= required_rank

        field_ok = False
        is_explicitly_unrelated = False

        if not job_specifies_stem:
            field_ok = True
        else:
            if any(f in cand_full for f in STEM_AND_TECH_FIELDS):
                field_ok = True
            elif any(u in cand_full for u in ["arts", "literature", "history", "philosophy", "fine arts", "music", "theology", "english"]):
                is_explicitly_unrelated = True

        if level_ok and field_ok:
            best_match = edu
            break
        elif level_ok and is_explicitly_unrelated:
            unrelated_match = edu

    if best_match:
        deg_str = best_match.get("degree_name") or best_match.get("degree_level")
        inst_str = best_match.get("institution") or "accredited institution"
        return {
            "education_verified": True,
            "verification_status": "verified",
            "candidate_degrees": candidate_degrees,
            "detected_job_requirements": job_education_requirements,
            "notes": f"Verified: Candidate holds {deg_str} from {inst_str}, satisfying required degree qualification."
        }

    if unrelated_match:
        deg_str = unrelated_match.get("degree_name") or unrelated_match.get("degree_level")
        return {
            "education_verified": False,
            "verification_status": "unrelated_degree",
            "candidate_degrees": candidate_degrees,
            "detected_job_requirements": job_education_requirements,
            "notes": f"Unrelated qualification: Candidate degree ({deg_str}) does not align with the required technical specialization."
        }

    return {
        "education_verified": False,
        "verification_status": "inconclusive",
        "candidate_degrees": candidate_degrees,
        "detected_job_requirements": job_education_requirements,
        "notes": "Verification inconclusive: Extracted education credentials could not be definitively matched against job degree requirements."
    }


def check_skill_contradiction(skill: str, resume_raw_text: str, conflicts: List[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """
    Checks if there is contradictory or disclaimed evidence regarding a skill:
    - Explicit denial or disclaimer in resume text (e.g. 'no experience with Docker', 'did not work with Kubernetes', 'never used AWS')
    - Directly contradictory chronology affecting the skill's tenure
    Returns (conflicting_excerpt, explanation) if contradiction exists, otherwise None.
    """
    skill_lower = skill.lower()

    # 1. Check for explicit negative disclaimer or denial in resume text
    denial_patterns = [
        rf"\b(?:no|little|without|never\s+used|not\s+used|did\s+not\s+(?:use|work\s+with)|lacks?|have\s+not\s+worked\s+with|haven't\s+worked\s+with)\b[^.!?\n]{{0,40}}\b{re.escape(skill_lower)}\b",
        rf"\b{re.escape(skill_lower)}\b[^.!?\n]{{0,40}}\b(?:was\s+not\s+used|not\s+applicable|is\s+unfamiliar|not\s+practiced|not\s+experienced)\b"
    ]
    for pat in denial_patterns:
        m = re.search(pat, resume_raw_text, re.I)
        if m:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", resume_raw_text) if s.strip()]
            for s in sentences:
                if m.group(0).lower() in s.lower() or (re.search(rf"\b{re.escape(skill_lower)}\b", s, re.I) and any(w in s.lower() for w in ["no experience", "did not", "never used", "not worked", "without", "lacks"])):
                    return s, f"Contradictory evidence: Resume text explicitly disclaims or negates experience with {skill}."

    # 2. Check if a candidate profile conflict directly relates to this skill
    for c in conflicts:
        desc = c.get("description", "")
        if re.search(rf"\b{re.escape(skill_lower)}\b", desc, re.I):
            return desc, f"Contradictory evidence: {desc}"

    return None


class ResumeMatchingEngine:
    """
    Unified end-to-end matching and skill gap engine.
    Supports both stable Production Baseline and experimental Challenger Model 5.
    """

    def __init__(self):
        self.job_analyzer = JobDescriptionAnalyzer()
        self.gap_analyzer = SkillGapAnalyzer()
        self.exp_analyzer = ExperienceAnalyzer()
        self.rec_engine = RecommendationEngine()
        self._inference_engine = None
        self._challenger_service = None

    @property
    def inference_engine(self):
        if self._inference_engine is None:
            self._inference_engine = get_inference_engine()
        return self._inference_engine

    @property
    def challenger_service(self):
        if self._challenger_service is None:
            self._challenger_service = get_challenger_service()
        return self._challenger_service

    def analyze(
        self,
        resume_input: Union[str, bytes],
        job_description_input: str,
        resume_filename: Optional[str] = None,
        model_backend: Optional[str] = None,
        target_role_input: Optional[str] = None,
        user_confirmations: Optional[Union[List[str], Dict[str, Any]]] = None
    ) -> Dict:
        """
        Runs the full analysis pipeline on a resume and job description.
        Returns a complete, structured, JSON-serializable dictionary.
        """
        analysis_id = str(uuid.uuid4())
        warnings: List[str] = []

        # 1. Parse Resume
        if isinstance(resume_input, bytes):
            parsed_resume = parse_resume(resume_input, filename=resume_filename)
        else:
            parsed_resume = parse_resume(resume_input.encode("utf-8"), filename=resume_filename or "resume.txt")

        if parsed_resume["status"] != "success":
            return {
                "analysis_id": analysis_id,
                "status": parsed_resume["status"],
                "error_message": parsed_resume["error_message"],
                "warnings": parsed_resume.get("warnings", []),
                "predicted_class": "No Fit",
                "class_probabilities": {c: 0.0 for c in CLASSES},
                "model_confidence": 0.0,
                "compatibility_score": 0.0,
                "skill_coverage": 0.0,
                "skill_coverage_pct": 0.0,
                "full_coverage_pct": 0.0,
                "any_coverage_pct": 0.0,
                "full_coverage_display": "Not Available",
                "any_coverage_display": "Not Available",
                "skill_coverage_display": "Not Available",
                "fully_matched_coverage_pct": 0.0,
                "skill_evidence_coverage_pct": 0.0,
                "skill_gap_summary": {
                    "total_required_count": 0,
                    "fully_matched_required_count": 0,
                    "partially_evidenced_required_count": 0,
                    "matched_required_count": 0,
                    "missing_required_count": 0,
                    "total_preferred_count": 0,
                    "matched_preferred_count": 0,
                    "missing_preferred_count": 0,
                    "full_coverage_pct": 0.0,
                    "any_coverage_pct": 0.0,
                    "full_coverage_display": "Not Available",
                    "any_coverage_display": "Not Available",
                    "skill_coverage_pct": None,
                    "skill_coverage_display": "Not Available"
                },
                "matched_skills": [],
                "missing_skills": [],
                "partially_evidenced_skills": [],
                "required_skills": [],
                "preferred_skills": [],
                "resume_skills": [],
                "projects": [],
                "relevant_projects": [],
                "internships": [],
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
                "experience_analysis": {},
                "education_analysis": {},
                "recommendations": [],
                "learning_resources": [],
                "candidate_profile": parsed_resume.get("candidate_profile", {}),
                "evidence_grounded_matches": [],
                "scorecard": {},
                "responsibilities": [],
                "qualifications": [],
                "tools_and_technologies": [],
                "experience_requirements": {}
            }

        warnings.extend(parsed_resume.get("warnings", []))
        resume_raw_text = parsed_resume["raw_text"]

        # 2. Analyze Job Description
        job_res = self.job_analyzer.analyze(job_description_input)
        if job_res["status"] != "success":
            return {
                "analysis_id": analysis_id,
                "status": "error",
                "error_message": "Job description input was empty or invalid.",
                "warnings": warnings,
                "predicted_class": "No Fit",
                "candidate_profile": parsed_resume.get("candidate_profile", {}),
                "evidence_grounded_matches": [],
                "scorecard": {},
                "responsibilities": [],
                "qualifications": [],
                "tools_and_technologies": [],
                "experience_requirements": {}
            }

        detected_job_title = job_res["job_title"]
        target_role = ""
        if isinstance(target_role_input, str):
            target_role = re.sub(r"\s+", " ", target_role_input).strip()
            target_role = re.sub(r"[\x00-\x1f\x7f]", "", target_role)[:120].strip()
        job_title = target_role or detected_job_title
        job_required_skills = job_res["required_skills"]
        job_preferred_skills = job_res["preferred_skills"]
        job_unspecified_skills = job_res.get("unspecified_skills", [])
        job_exp_years = job_res["required_years_exp"]

        # 3. Supervised Machine Learning Compatibility Prediction
        is_challenger = False
        inference_latency_ms = 0.0
        cache_status = None
        model_requested = model_backend or "production"
        fallback_triggered = False
        fallback_reason = None
        pending_jobs = None

        if model_backend == "challenger_m5":
            try:
                c_pred = self.challenger_service.predict_match(resume_raw_text, job_description_input)
                if c_pred.get("status") == "cache_miss_pending":
                    # Non-blocking miss: background worker queued
                    fallback_triggered = True
                    fallback_reason = c_pred.get("fallback_reason", "cache_miss_pending_worker_generation")
                    pending_jobs = c_pred.get("job_ids")
                    logger.info("Challenger cache miss. Jobs queued: %s. Serving Production Baseline fallback.", pending_jobs)
                    warnings.append("Neural embeddings are queued for background generation. Temporary analysis computed via Production Baseline.")
                    ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                    predicted_class = ml_prediction["predicted_class"]
                    class_probabilities = ml_prediction["probabilities"]
                    model_confidence = ml_prediction["confidence"]
                    compatibility_score = ml_prediction["compatibility_score"]
                    model_used = "Production Baseline (Fallback: Embeddings Queued for Background Worker)"
                    model_backend_applied = "production_fallback"
                    inference_latency_ms = c_pred.get("latency_ms", 0.0)
                    cache_status = c_pred.get("cache_status", {})
                    is_challenger = False
                    calibration_note = "Production Baseline: Calibrated probabilities while neural embeddings generate in background."
                elif c_pred.get("status") == "error":
                    fallback_triggered = True
                    fallback_reason = c_pred.get("fallback_reason", "challenger_error")
                    logger.error("Challenger error: %s. Falling back to Production Baseline.", fallback_reason)
                    warnings.append(f"Challenger Model 5 encountered an issue ({fallback_reason}); safely reverted to Production Baseline.")
                    ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                    predicted_class = ml_prediction["predicted_class"]
                    class_probabilities = ml_prediction["probabilities"]
                    model_confidence = ml_prediction["confidence"]
                    compatibility_score = ml_prediction["compatibility_score"]
                    model_used = "Production Baseline (Fallback from Challenger Error)"
                    model_backend_applied = "production_fallback"
                    is_challenger = False
                    calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."
                else:
                    predicted_class = c_pred["predicted_class"]
                    class_probabilities = c_pred["probabilities"]
                    model_confidence = c_pred["confidence"]
                    compatibility_score = c_pred["compatibility_score"]
                    model_used = "Challenger Model 5 (Semantic & Skill Fusion - Experimental)"
                    model_backend_applied = "challenger_m5"
                    inference_latency_ms = c_pred.get("latency_ms", 0.0)
                    cache_status = c_pred.get("cache_status", {})
                    is_challenger = True
                    calibration_note = "Experimental Model Notice: Probabilities reflect softmax cross-entropy output from the multi-modal fusion challenger. Calibration refinement is active."
            except Exception as e:
                fallback_triggered = True
                fallback_reason = f"challenger_exception: {type(e).__name__} - {str(e)[:80]}"
                logger.error("Challenger Model 5 unexpected exception, falling back to Production Baseline: %s", e)
                warnings.append(f"Challenger Model 5 encountered an exception ({str(e)[:60]}); safely reverted to Production Baseline.")
                ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
                predicted_class = ml_prediction["predicted_class"]
                class_probabilities = ml_prediction["probabilities"]
                model_confidence = ml_prediction["confidence"]
                compatibility_score = ml_prediction["compatibility_score"]
                model_used = "Production Baseline (Fallback from Challenger Error)"
                model_backend_applied = "production_fallback"
                is_challenger = False
                calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."
        else:
            ml_prediction = self.inference_engine.predict_match(resume_raw_text, job_description_input)
            predicted_class = ml_prediction["predicted_class"]
            class_probabilities = ml_prediction["probabilities"]
            model_confidence = ml_prediction["confidence"]
            compatibility_score = ml_prediction["compatibility_score"]
            model_used = "Production Baseline (TF-IDF + Logistic Regression)"
            model_backend_applied = "production"
            calibration_note = "Production Model: Calibrated probabilities based on TF-IDF baseline."

        # 4. Comparative Skill Gap Analysis
        gap_res = self.gap_analyzer.analyze_gap(
            resume_raw_text,
            job_res,
            job_raw_text=job_description_input
        )

        # Clean and sanitize skill lists (filter out any empty, whitespace-only, or None values)
        def _clean_skills(skill_list: List[str], tier_name: str) -> List[str]:
            cleaned = []
            for s in skill_list:
                if s and isinstance(s, str) and s.strip():
                    cleaned.append(s.strip())
                else:
                    logger.warning("Omitted empty %s skill badge: %r", tier_name, s)
            return cleaned

        matched_skills = _clean_skills(gap_res["matched_skills"], "matched")
        matched_required = _clean_skills(gap_res["matched_required_skills"], "matched_required")
        fully_matched_required = _clean_skills(gap_res["fully_matched_required_skills"], "fully_matched_required")
        partially_evidenced_required = _clean_skills(gap_res["partially_evidenced_required_skills"], "partially_evidenced_required")
        missing_required = _clean_skills(gap_res["missing_required_skills"], "missing_required")
        matched_preferred = _clean_skills(gap_res["matched_preferred_skills"], "matched_preferred")
        missing_preferred = _clean_skills(gap_res["missing_preferred_skills"], "missing_preferred")
        missing_all = missing_required + [s for s in missing_preferred if s not in missing_required]

        # 5. Experience Alignment & Project Evidence
        exp_res = self.exp_analyzer.analyze_experience(resume_raw_text, job_required_years=job_exp_years)
        relevant_projects = exp_res["detected_projects"]

        # 6. Improvement Recommendations & Verified Learning Resources
        recommendations = self.rec_engine.generate_recommendations(
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            partially_evidenced=partially_evidenced_required,
            experience_analysis=exp_res,
            job_title=job_title
        )
        learning_resources = self.rec_engine.get_learning_resources(missing_all)

        # 7. Unified Skill Gap Accounting Summary (Two clearly separated coverage calculations)
        full_cov_pct = gap_res.get("full_coverage_pct", 0.0)
        any_cov_pct = gap_res.get("any_coverage_pct", 0.0)
        full_cov_disp = gap_res.get("full_coverage_display", f"{full_cov_pct}%")
        any_cov_disp = gap_res.get("any_coverage_display", f"{any_cov_pct}%")

        skill_gap_summary = {
            "total_required_count": gap_res["total_required_count"],
            "fully_matched_required_count": gap_res["fully_matched_required_count"],
            "partially_evidenced_required_count": gap_res["partially_evidenced_required_count"],
            "matched_required_count": gap_res["matched_required_count"],
            "missing_required_count": gap_res["missing_required_count"],
            "total_preferred_count": gap_res["total_preferred_count"],
            "matched_preferred_count": gap_res["matched_preferred_count"],
            "missing_preferred_count": gap_res["missing_preferred_count"],
            "total_resume_skills_count": gap_res.get("total_resume_skills_count", 0),
            "full_coverage_pct": full_cov_pct,
            "any_coverage_pct": any_cov_pct,
            "full_coverage_display": full_cov_disp,
            "any_coverage_display": any_cov_disp,
            "skill_coverage_pct": any_cov_pct,
            "fully_matched_coverage_pct": full_cov_pct,
            "skill_evidence_coverage_pct": any_cov_pct,
            "skill_coverage_display": full_cov_disp
        }

        # Structured Education verification
        candidate_edu_list = parsed_resume.get("candidate_profile", {}).get("education", [])
        edu_verif = verify_structured_education(
            candidate_edu_list,
            job_res.get("education_requirements", [])
        )

        from src.common.evidence_registry import build_unified_evidence_registry

        # 8. Assemble Complete Result
        result_payload = {
            "analysis_id": analysis_id,
            "status": "success",
            "filename": parsed_resume["filename"],
            "raw_text": resume_raw_text,
            "resume_raw_text": resume_raw_text,
            "cleaned_resume_text": parsed_resume.get("cleaned_text", ""),
            "job_title": job_title,
            "target_role": job_title,
            "detected_job_title": detected_job_title,
            "target_role_source": "user_override" if target_role else "job_description",
            "job_description_text": str(job_description_input),
            "raw_jd": str(job_description_input),
            "predicted_class": predicted_class,
            "class_probabilities": class_probabilities,
            "model_confidence": model_confidence,
            "compatibility_score": compatibility_score,
            "skill_coverage": any_cov_pct,
            "skill_coverage_pct": any_cov_pct,
            "full_coverage_pct": full_cov_pct,
            "any_coverage_pct": any_cov_pct,
            "skill_coverage_display": full_cov_disp,
            "full_coverage_display": full_cov_disp,
            "any_coverage_display": any_cov_disp,
            "fully_matched_coverage_pct": full_cov_pct,
            "skill_evidence_coverage_pct": any_cov_pct,
            "skill_gap_summary": skill_gap_summary,
            "matched_skills": matched_skills,
            "matched_required_skills": matched_required,
            "fully_matched_required_skills": fully_matched_required,
            "partially_evidenced_required_skills": partially_evidenced_required,
            "missing_skills": missing_all,
            "missing_required_skills": missing_required,
            "matched_preferred_skills": matched_preferred,
            "missing_preferred_skills": missing_preferred,
            "satisfied_alternatives": gap_res.get("satisfied_alternatives", []),
            "alternative_groups": job_res.get("alternative_groups", []),
            "partially_evidenced_skills": gap_res["partially_evidenced_skills"],
            "solidly_evidenced_skills": gap_res["solidly_evidenced_skills"],
            "required_skills": gap_res.get("effective_required_skills", job_required_skills),
            "preferred_skills": gap_res.get("effective_preferred_skills", job_preferred_skills),
            "unspecified_skills": job_unspecified_skills,
            "requirement_intelligence": job_res.get("requirement_intelligence", []),
            "resume_skills": gap_res["resume_skills"],
            "projects": relevant_projects,
            "relevant_projects": relevant_projects,
            "internships": exp_res.get("internships", []),
            "professional_experience": exp_res.get("professional_experience", []),
            "experience_summary": exp_res.get("experience_summary", {}),
            "experience_analysis": exp_res,
            "education_analysis": {
                "detected_job_requirements": job_res["education_requirements"],
                "candidate_degrees": edu_verif["candidate_degrees"],
                "education_verified": edu_verif["education_verified"],
                "verification_status": edu_verif["verification_status"],
                "notes": edu_verif["notes"]
            },
            "prioritized_gaps": gap_res["prioritized_gaps"],
            "recommendations": recommendations,
            "learning_resources": learning_resources,
            "has_missing_skills": bool(missing_all),
            "structural_metadata": parsed_resume["structural_features"],
            "model_requested": model_requested,
            "model_used": model_used,
            "model_backend": model_backend_applied,
            "fallback_triggered": fallback_triggered,
            "fallback_reason": fallback_reason,
            "pending_jobs": pending_jobs,
            "is_challenger": is_challenger,
            "inference_latency_ms": inference_latency_ms,
            "cache_status": cache_status,
            "calibration_note": calibration_note,
            "warnings": warnings
        }

        # Build unified evidence registry
        evidence_reg = build_unified_evidence_registry(result_payload)
        if user_confirmations:
            if isinstance(user_confirmations, (list, set)):
                for skill_conf in user_confirmations:
                    evidence_reg.add_user_confirmation(skill_conf, True)
            elif isinstance(user_confirmations, dict):
                for skill_conf, is_conf in user_confirmations.items():
                    if is_conf:
                        evidence_reg.add_user_confirmation(skill_conf, is_conf)

        result_payload["evidence_registry"] = evidence_reg.build_summary_dossier()

        # Build unified evidence-grounded matches table
        evidence_grounded_matches = []
        conflicts = parsed_resume.get("candidate_profile", {}).get("conflicts", [])

        for canon_lower, req in evidence_reg.job_requirements.items():
            canon_skill = req.name
            tier = req.tier
            job_sentence = req.supporting_sentence

            # 1. First check if contradictory evidence exists for this skill
            contradiction = check_skill_contradiction(canon_skill, resume_raw_text, conflicts)
            if contradiction:
                contra_excerpt, contra_explanation = contradiction
                evidence_grounded_matches.append({
                    "skill": canon_skill,
                    "tier": tier,
                    "job_requirement_sentence": job_sentence,
                    "candidate_evidence": contra_excerpt,
                    "evidence_source": "contradictory_claim",
                    "match_classification": "conflicting_evidence",
                    "confidence": 0.0,
                    "explanation": contra_explanation
                })
                continue

            # 2. Check candidate evidence in evidence registry
            rec = evidence_reg.evidence_records.get(canon_lower)
            is_resume_demonstrated = rec and rec.evidence_type in (
                "demonstrated", "demonstrated_project", "demonstrated_internship",
                "demonstrated_experience"
            )
            is_candidate_confirmed = rec and (
                rec.evidence_type == "user_confirmed" or
                getattr(rec, "candidate_confirmation", None) == "confirmed"
            )

            if is_resume_demonstrated:
                source = (
                    "project" if "project" in rec.evidence_type
                    else ("internship" if "internship" in rec.evidence_type
                          else "professional_experience")
                )
                classification = "fully_supported"
                confidence = float(rec.confidence) if rec.confidence else 0.95
                excerpt = rec.supporting_text
                explanation = f"Candidate demonstrates verifiable application of {canon_skill} with contextual project or experience details."
            elif is_candidate_confirmed:
                # Candidate confirmation is strictly separate from independently verified resume evidence
                source = "candidate_confirmed"
                classification = "candidate_confirmed"
                confidence = 0.75
                excerpt = rec.supporting_text
                explanation = f"Candidate confirmed proficiency with {canon_skill} via self-attestation; not independently evidenced in resume document."
            elif rec and rec.evidence_type == "partially_evidenced":
                source = "skills_section" if "skills" in rec.supporting_text.lower() else "project"
                classification = "partially_supported"
                confidence = 0.65
                excerpt = rec.supporting_text
                explanation = f"Candidate mentions {canon_skill} in profile or technical stack without comprehensive implementation context."
            elif rec and rec.evidence_type in ("explicit_mention", "explicitly_mentioned"):
                source = "skills_section"
                classification = "explicitly_mentioned"
                confidence = 0.50
                excerpt = rec.supporting_text
                explanation = f"Candidate explicitly lists {canon_skill} in resume skills inventory."
            else:
                source = "none"
                classification = "missing_evidence"
                confidence = 0.0
                excerpt = "No direct evidence documented in candidate resume"
                explanation = f"No verifiable usage or explicit mention of {canon_skill} documented in candidate resume."

            evidence_grounded_matches.append({
                "skill": canon_skill,
                "tier": tier,
                "job_requirement_sentence": job_sentence,
                "candidate_evidence": excerpt,
                "evidence_source": source,
                "match_classification": classification,
                "confidence": round(confidence, 2),
                "explanation": explanation
            })

        # Scorecard cleanly separating dimensions without double-counting
        scorecard = {
            "ml_compatibility": {
                "predicted_class": predicted_class,
                "compatibility_score": compatibility_score,
                "model_confidence": model_confidence,
                "probabilities": class_probabilities,
                "model_used": model_used
            },
            "skill_coverage": {
                "full_coverage_pct": full_cov_pct,
                "any_coverage_pct": any_cov_pct,
                "matched_required_count": gap_res["matched_required_count"],
                "total_required_count": gap_res["total_required_count"],
                "matched_preferred_count": gap_res["matched_preferred_count"],
                "total_preferred_count": gap_res["total_preferred_count"],
                "fully_matched_required_count": gap_res["fully_matched_required_count"],
                "partially_evidenced_required_count": gap_res["partially_evidenced_required_count"]
            },
            "experience_coverage": {
                "job_required_years": job_exp_years,
                "candidate_experience_years": exp_res.get("resume_years_exp", exp_res.get("experience_summary", {}).get("full_time_years", 0.0)),
                "meets_experience_requirement": exp_res.get("meets_experience_requirement", False),
                "has_full_time": exp_res.get("experience_summary", {}).get("has_full_time", False),
                "has_internships": exp_res.get("experience_summary", {}).get("has_internships", False),
                "internships_count": exp_res.get("experience_summary", {}).get("internships_count", 0),
                "has_projects": exp_res.get("experience_summary", {}).get("has_projects", False),
                "projects_count": exp_res.get("experience_summary", {}).get("projects_count", 0),
                "primary_classification": exp_res.get("experience_summary", {}).get("primary_classification", "Experience not established"),
                "display_summary": exp_res.get("experience_summary", {}).get("display_summary", "")
            },
            "qualification_coverage": {
                "detected_job_requirements": job_res.get("education_requirements", []),
                "candidate_degrees": edu_verif["candidate_degrees"],
                "education_verified": edu_verif["education_verified"],
                "verification_status": edu_verif["verification_status"],
                "notes": edu_verif["notes"]
            }
        }

        result_payload["evidence_grounded_matches"] = evidence_grounded_matches
        result_payload["scorecard"] = scorecard
        result_payload["candidate_profile"] = parsed_resume.get("candidate_profile", {})
        result_payload["responsibilities"] = job_res.get("responsibilities", [])
        result_payload["qualifications"] = job_res.get("qualifications", [])
        result_payload["tools_and_technologies"] = job_res.get("tools_and_technologies", [])
        result_payload["experience_requirements"] = job_res.get("experience_requirements", {})

        return result_payload


# Global singleton instance
_default_matching_engine: Optional[ResumeMatchingEngine] = None


def get_matching_engine() -> ResumeMatchingEngine:
    global _default_matching_engine
    if _default_matching_engine is None:
        _default_matching_engine = ResumeMatchingEngine()
    return _default_matching_engine


def analyze_resume_and_job(
    resume_input: Union[str, bytes],
    job_description_input: str,
    resume_filename: Optional[str] = None,
    model_backend: Optional[str] = None,
    target_role_input: Optional[str] = None,
    user_confirmations: Optional[Union[List[str], Dict[str, Any]]] = None
) -> Dict:
    return get_matching_engine().analyze(
        resume_input,
        job_description_input,
        resume_filename=resume_filename,
        model_backend=model_backend,
        target_role_input=target_role_input,
        user_confirmations=user_confirmations
    )

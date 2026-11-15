"""
src/phase12f/long_document_handler.py
Requirement-Gated Extraction (RGE) and Long-Document Processing.
Prevents the 98.3% sequence truncation failure identified in Phase 12E-3
by intelligently condensing paired documents into a high-density <=256 token budget.
"""

import re
from typing import Dict, List, Optional, Tuple
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features


class RequirementGatedExtractor:
    """
    Intelligently compresses resume and job description pairs into a high-signal,
    structured format fitting within a 256-token budget without losing critical qualifications.
    """

    def __init__(self, max_total_tokens: int = 256):
        self.max_total_tokens = max_total_tokens
        self.skill_engine = SkillEngine()

    def extract_job_core_requirements(self, jd_text: str, max_words: int = 110) -> Dict:
        """
        Extracts high-signal requirement clauses from JD:
        - Position title
        - Required experience years
        - Mandatory skills / technology stack
        - Core requirement bullet points
        """
        clean_jd = clean_text(jd_text)
        skills = self.skill_engine.extract_skills(clean_jd)
        struct = parse_structural_features(clean_jd)

        # Regex for requirement sections (Requirements, Qualifications, Must have, What we look for)
        req_pattern = re.compile(
            r"(?:requirements?|qualifications?|must have|what we look for|what you(?:'ll)? need|skills?|responsibilities?)[\s:]+(.*?)(?=(?:benefits|perks|we offer|about us|company|salary|\Z))",
            re.IGNORECASE | re.DOTALL
        )
        match = req_pattern.search(clean_jd)
        req_text = match.group(1).strip() if match else clean_jd[:500]

        # Extract sentences/bullets containing skills
        sentences = re.split(r"[\n•\-\*]+|\.\s+", req_text)
        high_signal_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 10:
                continue
            # If sentence mentions skills or experience, prioritize it
            if any(skill.lower() in s_clean.lower() for skill in skills) or re.search(r"\d+\+?\s*(?:years?|yrs)", s_clean, re.I):
                high_signal_sentences.append(s_clean)
            if len(" ".join(high_signal_sentences).split()) >= max_words:
                break

        if not high_signal_sentences:
            core_text = " ".join(clean_jd.split()[:max_words])
        else:
            core_text = " ".join(high_signal_sentences)
            core_text = " ".join(core_text.split()[:max_words])

        return {
            "core_text": core_text,
            "skills": skills,
            "exp_years_req": struct.get("years_experience", 0.0)
        }

    def extract_resume_candidate_evidence(self, resume_text: str, jd_skills: List[str], max_words: int = 110) -> Dict:
        """
        Extracts high-signal candidate qualifications:
        - Matched skills
        - Explicit years of experience
        - High-density sentences from work experience / summary
        """
        clean_res = clean_text(resume_text)
        res_skills = self.skill_engine.extract_skills(clean_res)
        struct = parse_structural_features(clean_res)

        # Overlap with JD skills
        matched_skills = [s for s in res_skills if s in jd_skills]

        # Break resume into sections/sentences
        sentences = re.split(r"[\n•\-\*]+|\.\s+", clean_res)
        priority_sentences = []

        # 1. First priority: sentences containing matched skills or experience duration
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            has_matched_skill = any(ms.lower() in s_clean.lower() for ms in matched_skills)
            has_exp_mention = bool(re.search(r"\d+\+?\s*(?:years?|yrs|months?)", s_clean, re.I))
            if has_matched_skill or has_exp_mention:
                priority_sentences.append(s_clean)
            if len(" ".join(priority_sentences).split()) >= max_words:
                break

        if not priority_sentences:
            evidence_text = " ".join(clean_res.split()[:max_words])
        else:
            evidence_text = " ".join(priority_sentences)
            evidence_text = " ".join(evidence_text.split()[:max_words])

        return {
            "evidence_text": evidence_text,
            "skills": res_skills,
            "matched_skills": matched_skills,
            "candidate_exp_years": struct.get("years_experience", 0.0)
        }

    def transform_pair(self, resume_text: str, jd_text: str) -> Dict:
        """
        Combines resume and job into a structured, requirement-gated sequence.
        Format:
        JD Requirements: [Core JD Requirements] | Required Skills: [S1, S2] | Exp Req: [N yrs]
        Candidate Evidence: [Evidence text] | Matched Skills: [S1] | Total Exp: [M yrs]
        """
        jd_core = self.extract_job_core_requirements(jd_text, max_words=100)
        res_evidence = self.extract_resume_candidate_evidence(resume_text, jd_core["skills"], max_words=100)

        jd_skills_list = list(jd_core["skills"]) if isinstance(jd_core["skills"], (set, list)) else []
        matched_skills_list = list(res_evidence["matched_skills"]) if isinstance(res_evidence["matched_skills"], (set, list)) else []

        jd_skills_str = ", ".join(jd_skills_list[:10]) if jd_skills_list else "None specified"
        matched_skills_str = ", ".join(matched_skills_list[:10]) if matched_skills_list else "None matched"

        structured_text = (
            f"JOB REQUIREMENTS: {jd_core['core_text']} | "
            f"REQ SKILLS: {jd_skills_str} | "
            f"REQ EXP: {jd_core['exp_years_req']:.1f}y || "
            f"CANDIDATE QUALIFICATIONS: {res_evidence['evidence_text']} | "
            f"MATCHED SKILLS: {matched_skills_str} | "
            f"CANDIDATE EXP: {res_evidence['candidate_exp_years']:.1f}y"
        )

        # Word count ~ 220 words => ~250 tokens
        words = structured_text.split()
        if len(words) > 230:
            structured_text = " ".join(words[:230])

        # Retention metrics
        all_jd_skills = set(jd_core["skills"])
        all_res_skills = set(res_evidence["skills"])
        skill_retention = len(res_evidence["matched_skills"]) / max(len(all_jd_skills.intersection(all_res_skills)), 1)

        return {
            "structured_text": structured_text,
            "raw_word_count": len(resume_text.split()) + len(jd_text.split()),
            "rge_word_count": len(structured_text.split()),
            "estimated_tokens": int(len(structured_text.split()) * 1.2),
            "skill_retention": round(skill_retention, 3),
            "exp_gap": round(res_evidence["candidate_exp_years"] - jd_core["exp_years_req"], 1)
        }

    def batch_transform(self, resumes: List[str], jobs: List[str]) -> List[str]:
        """Transforms a batch of resume and job description pairs."""
        return [self.transform_pair(r, j)["structured_text"] for r, j in zip(resumes, jobs)]

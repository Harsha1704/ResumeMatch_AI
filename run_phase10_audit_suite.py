"""
Phase 10 Quality Audit Runner Script.
Runs all 30 scenarios through the ResumeMatch AI pipeline:
- Matching Engine
- Requirement Intelligence & Alternative Skill Analysis
- Candidate Evidence Registry
- Career Mentor Counseling & Roadmap Generation
- Interview Intelligence Studio & Answer Quality Validation
Saves audit outputs to results/phase10_audit_outputs/
Computes repetition and quality metrics.
"""

import os
import json
import re
from typing import Dict, Any, List
from collections import Counter

from tests.fixtures.thirty_audit_scenarios import THIRTY_AUDIT_SCENARIOS
from src.analysis.matching_engine import ResumeMatchingEngine
from src.mentor.mentor_engine import CareerMentorEngine
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_validator import AnswerQualityValidator
from src.common.evidence_registry import build_unified_evidence_registry

OUTPUT_DIR = "results/phase10_audit_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def compute_jaccard_similarity(s1: str, s2: str) -> float:
    w1 = set(re.findall(r"\w+", s1.lower()))
    w2 = set(re.findall(r"\w+", s2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)

def run_audit():
    print(f"Starting Phase 10 Real-World Quality Audit on {len(THIRTY_AUDIT_SCENARIOS)} scenarios...")
    engine = ResumeMatchingEngine()
    
    audit_summary = []
    all_recommendation_sentences = []
    all_interview_answers = []
    all_inquiry_prompts = []
    
    total_questions_validated = 0
    passed_validation_questions = 0
    validation_issues = []
    invariant_failures = []
    alt_failures = []

    for idx, (s_key, scenario) in enumerate(THIRTY_AUDIT_SCENARIOS.items(), 1):
        cand_id = scenario["candidate_id"]
        print(f"[{idx:02d}/30] Auditing {cand_id}...")
        
        raw_text = scenario["raw_text"]
        jd_text = scenario["job_description"]
        
        # 1. Matching Engine
        analysis = engine.analyze(
            resume_input=raw_text,
            job_description_input=jd_text,
            resume_filename=f"{cand_id}.pdf"
        )
        
        # 2. Evidence Registry
        registry = analysis.get("evidence_registry", {})
        
        # 3. Requirement & Gap Invariants
        gap_data = analysis.get("skill_gap_analysis", {})
        breakdown = gap_data.get("requirement_breakdown", {})
        solid_req = len(breakdown.get("solid_matched_required", []))
        part_req = len(breakdown.get("partial_matched_required", []))
        miss_req = len(breakdown.get("missing_required", []))
        total_req = solid_req + part_req + miss_req
        total_extracted_req = len(gap_data.get("required_skills", []))
        
        if total_req != total_extracted_req:
            invariant_failures.append({
                "scenario": s_key,
                "solid": solid_req,
                "partial": part_req,
                "missing": miss_req,
                "sum": total_req,
                "extracted": total_extracted_req
            })
            
        # Check alternative skill handling
        sat_alts = gap_data.get("satisfied_alternatives", {})
        if s_key == "scenario_26_alt_powerbi_tableau":
            # Power BI matched -> Tableau should NOT be in missing_required
            missing_names = [m["name"] if isinstance(m, dict) else m for m in breakdown.get("missing_required", [])]
            if "Tableau" in missing_names:
                alt_failures.append("Tableau flagged as missing when Power BI matched in Scenario 26")
        elif s_key == "scenario_27_alt_postgres_mysql":
            # MySQL matched -> PostgreSQL should NOT be in missing_required
            missing_names = [m["name"] if isinstance(m, dict) else m for m in breakdown.get("missing_required", [])]
            if "PostgreSQL" in missing_names:
                alt_failures.append("PostgreSQL flagged as missing when MySQL matched in Scenario 27")
        elif s_key == "scenario_28_alt_pytorch_tensorflow":
            # PyTorch matched -> TensorFlow should NOT be in missing_required
            missing_names = [m["name"] if isinstance(m, dict) else m for m in breakdown.get("missing_required", [])]
            if "TensorFlow" in missing_names:
                alt_failures.append("TensorFlow flagged as missing when PyTorch matched in Scenario 28")

        # 4. Career Mentor
        mentor_engine = CareerMentorEngine(analysis)
        mentor_guidance = mentor_engine.build_mentor_dossier(timeline_days=14, daily_hours=2.0)
        
        # Collect mentor recommendation sentences
        counseling_profile = mentor_guidance.get("counseling_profile", {})
        for q_key, q_ans in counseling_profile.items():
            if isinstance(q_ans, dict):
                for sub_k, sub_v in q_ans.items():
                    if isinstance(sub_v, str):
                        sents = [s.strip() for s in sub_v.split(". ") if len(s.strip()) > 15]
                        all_recommendation_sentences.extend(sents)
            elif isinstance(q_ans, str):
                sents = [s.strip() for s in q_ans.split(". ") if len(s.strip()) > 15]
                all_recommendation_sentences.extend(sents)

        # 5. Interview Intelligence Studio
        interview_gen = InterviewQuestionGenerator(analysis)
        questions = interview_gen.generate_questions(category="ALL", max_questions=15)
        
        scenario_validated_qs = []
        for q in questions:
            total_questions_validated += 1
            val_result = AnswerQualityValidator.validate_answer(q)
            if val_result["is_valid"]:
                passed_validation_questions += 1
            else:
                validation_issues.append({
                    "scenario": s_key,
                    "question_id": q.get("question_id"),
                    "issues": val_result["issues"]
                })
            
            detailed_ans = q.get("detailed_answer", "")
            if detailed_ans:
                all_interview_answers.append(detailed_ans)
                
            inquiries = q.get("missing_information_prompts") or q.get("candidate_inquiry_prompts") or []
            if inquiries:
                all_inquiry_prompts.extend(inquiries)
                
            scenario_validated_qs.append({
                "question_id": q.get("question_id"),
                "category": q.get("category"),
                "question_text": q.get("question_text"),
                "framework": q.get("recommended_framework") or q.get("recommended_answer_framework"),
                "validation_score": val_result["quality_score"],
                "validation_issues": val_result["issues"],
                "detailed_answer_preview": detailed_ans[:200]
            })

        # Save Scenario JSON Output
        scenario_record = {
            "scenario_key": s_key,
            "candidate_id": cand_id,
            "description": scenario["description"],
            "matching_analysis": {
                "match_score": analysis.get("match_score"),
                "category": analysis.get("category"),
                "matched_skills": analysis.get("matched_skills"),
                "missing_skills": analysis.get("missing_skills"),
                "satisfied_alternatives": sat_alts,
                "requirement_breakdown": breakdown
            },
            "evidence_registry": {
                "total_evidence_units": registry.get("total_evidence_units"),
                "evidence_coverage_ratio": registry.get("evidence_coverage_ratio")
            },
            "career_mentor": {
                "candidate_name": mentor_guidance.get("candidate_name"),
                "counseling_profile_keys": list(counseling_profile.keys()),
                "roadmap_skills_count": len(mentor_guidance.get("skill_roadmaps", [])),
                "scheduled_tasks_count": mentor_guidance.get("study_plan", {}).get("scheduled_tasks_count")
            },
            "interview_studio": {
                "total_questions_generated": len(questions),
                "questions": scenario_validated_qs
            }
        }
        
        out_path = os.path.join(OUTPUT_DIR, f"{s_key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scenario_record, f, indent=2)
            
        audit_summary.append({
            "scenario_key": s_key,
            "candidate_id": cand_id,
            "match_score": analysis.get("match_score"),
            "category": analysis.get("category"),
            "questions_count": len(questions),
            "satisfied_alternatives": sat_alts
        })

    # Repetition Metrics
    rec_counts = Counter(all_recommendation_sentences)
    exact_duplicate_recs = [s for s, count in rec_counts.items() if count > 1]
    rec_repetition_rate = len(exact_duplicate_recs) / max(1, len(rec_counts)) * 100.0

    ans_pairs = []
    # Sample up to 100 random answer pairs for cross-scenario similarity
    for i in range(min(50, len(all_interview_answers))):
        for j in range(i + 1, min(50, len(all_interview_answers))):
            sim = compute_jaccard_similarity(all_interview_answers[i], all_interview_answers[j])
            ans_pairs.append(sim)
            
    avg_jaccard = sum(ans_pairs) / max(1, len(ans_pairs))

    results = {
        "total_scenarios_audited": len(THIRTY_AUDIT_SCENARIOS),
        "total_questions_audited": total_questions_validated,
        "passed_validation_questions": passed_validation_questions,
        "validation_pass_rate": round(passed_validation_questions / max(1, total_questions_validated) * 100.0, 2),
        "invariant_failures_count": len(invariant_failures),
        "alternative_failures_count": len(alt_failures),
        "recommendation_sentence_repetition_rate": round(rec_repetition_rate, 2),
        "average_interview_answer_jaccard_similarity": round(avg_jaccard, 4),
        "invariant_failures": invariant_failures,
        "alternative_failures": alt_failures,
        "sample_validation_issues": validation_issues[:10]
    }
    
    with open("results/phase10_audit_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("\n=== PHASE 10 AUDIT RESULTS SUMMARY ===")
    print(f"Scenarios Audited: {results['total_scenarios_audited']}/30")
    print(f"Questions Audited: {results['total_questions_audited']}")
    print(f"Validation Pass Rate: {results['validation_pass_rate']}%")
    print(f"Invariant Failures: {results['invariant_failures_count']}")
    print(f"Alternative Skill Failures: {results['alternative_failures_count']}")
    print(f"Recommendation Repetition Rate: {results['recommendation_sentence_repetition_rate']}%")
    print(f"Avg Interview Answer Jaccard Sim: {results['average_interview_answer_jaccard_similarity']}")
    print("======================================\n")
    return results

if __name__ == "__main__":
    run_audit()

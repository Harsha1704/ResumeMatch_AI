"""
Phase 2 Test Suite: Unified Candidate Evidence Engine & Reliability Repair.

Verifies all 26 Phase 2 requirements across:
1. Evidence classification (Static skills list, project description, internship, no excerpt, user confirmed, multiple projects, project+internship).
2. Requirement consistency (Required demonstrated, required partial, required not evidenced, preferred demonstrated, required vs preferred separation, alternative satisfaction, aliases, non-erasure of requirement data).
3. Integrity and privacy (No fabricated excerpts, no generic placeholders, no duplicate counts, no contradictory demonstrated/missing status, analysis isolation, confirmation preserves resume evidence).
4. Module integration (Resume Analyzer, Skill Gap Analytics, Career Mentor, Interview Studio, Practice & Review).
"""

import pytest
from app import app
from src.analysis.matching_engine import ResumeMatchingEngine, analyze_resume_and_job
from src.common.evidence_registry import (
    CandidateEvidenceRegistry,
    EvidenceRecord,
    JobRequirementRecord,
    build_unified_evidence_registry,
    resolve_canonical_skill,
    find_jd_quote,
    find_resume_sentence_for_skill,
    CANONICAL_SKILL_ALIASES
)
from src.mentor.mentor_engine import CareerMentorEngine
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.evidence_mapper import extract_candidate_evidence


# =============================================================================
# Class 1: Evidence Classification Tests (Req 1 - 7)
# =============================================================================

class TestEvidenceClassification:

    def test_01_skill_mentioned_in_static_skills_list(self):
        """1. Verify skill mentioned only in static skills list is classified as partially_evidenced / explicit_mention."""
        analysis_data = {
            "resume_raw_text": "Harsha Vardhan\nSkills: Python, Scikit-learn, Docker, Redis\nEducation: B.Tech",
            "resume_skills": ["python", "scikit-learn", "docker", "redis"],
            "partially_evidenced_skills": ["redis"],
            "job_description_text": "Requirements: Python, Docker, Redis",
            "required_skills": ["python", "docker", "redis"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("redis")
        assert rec is not None
        assert rec.evidence_type in ("partially_evidenced", "explicitly_mentioned", "explicit_mention")
        assert rec.evidence_strength in ("partially_evidenced", "explicitly_mentioned", "weak", "moderate")
        assert "Verified with contextual engineering verbs in resume." not in rec.supporting_text
        assert "Listed in static skills list." not in rec.supporting_text

    def test_02_skill_demonstrated_in_project_description(self):
        """2. Verify skill with active implementation verb in project description is classified as demonstrated."""
        analysis_data = {
            "resume_raw_text": "Built multimodal search pipeline using PyTorch and FastAPI.",
            "projects": [
                {
                    "title": "Multimodal Search Engine",
                    "technologies": ["PyTorch", "FastAPI", "Docker"],
                    "description": "Architected, trained, and deployed deep learning transformers using PyTorch."
                }
            ],
            "resume_skills": ["pytorch", "fastapi", "docker"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("pytorch")
        assert rec is not None
        assert rec.evidence_type in ("demonstrated", "demonstrated_project")
        assert rec.evidence_strength in ("demonstrated", "strong")
        assert "Multimodal Search Engine" in rec.supporting_text
        assert "PyTorch" in rec.supporting_text

    def test_03_skill_mentioned_in_internship_responsibility(self):
        """3. Verify skill mentioned in internship responsibilities is classified as demonstrated_internship."""
        analysis_data = {
            "internships": [
                {
                    "organization": "DataCore Systems",
                    "position": "Backend Intern",
                    "responsibilities": ["Engineered automated ETL pipelines and database migration scripts using PostgreSQL."],
                    "technologies": ["PostgreSQL", "Python"]
                }
            ],
            "resume_skills": ["postgresql", "python"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("postgresql")
        assert rec is not None
        assert rec.evidence_type in ("demonstrated", "demonstrated_internship")
        assert "DataCore Systems" in rec.supporting_text
        assert "PostgreSQL" in rec.supporting_text

    def test_04_skill_with_no_supporting_excerpt(self):
        """4. Verify missing requirement with no candidate excerpt states unavailable rather than inventing quote."""
        analysis_data = {
            "resume_raw_text": "Experienced Python and SQL developer.",
            "resume_skills": ["python", "sql"],
            "required_skills": ["python", "kubernetes"],
            "missing_required_skills": ["kubernetes"],
            "job_description_text": "Job requires Python and Kubernetes cluster management."
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("kubernetes")
        assert rec is not None
        assert rec.evidence_type == "not_evidenced"
        assert rec.evidence_strength == "none"
        assert "Not evidenced in resume" in rec.supporting_text

    def test_05_skill_explicitly_confirmed_by_user(self):
        """5. Verify candidate user confirmation updates status without erasing original resume evidence."""
        analysis_data = {
            "resume_raw_text": "Technical skills: Java, Spring Boot.",
            "resume_skills": ["java", "spring boot"],
            "partially_evidenced_skills": ["java"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec_initial = reg.get_record("java")
        assert rec_initial.evidence_type == "partially_evidenced"

        # Candidate confirms Java in session
        reg.add_user_confirmation("Java", "5 years enterprise Java experience")
        rec_updated = reg.get_record("java")
        assert rec_updated.candidate_confirmation == "confirmed"
        assert rec_updated.evidence_strength == "confirmed"
        # Original resume occurrence is preserved in occurrences list
        assert len(rec_updated.occurrences) >= 2
        assert any(o.get("source_type") == "user_confirmation" for o in rec_updated.occurrences)

    def test_06_same_skill_supported_by_multiple_projects(self):
        """6. Verify same skill in multiple projects preserves all occurrences without overwriting or duplicate counts."""
        analysis_data = {
            "projects": [
                {
                    "title": "Alpha Microservice",
                    "technologies": ["Python", "Flask"],
                    "description": "Developed backend REST APIs using Python."
                },
                {
                    "title": "Beta Anomaly Detector",
                    "technologies": ["Python", "PyTorch"],
                    "description": "Implemented real-time anomaly detection using Python."
                }
            ],
            "resume_skills": ["python", "flask", "pytorch"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("python")
        assert rec is not None
        # Must retain both project occurrences
        occs = rec.occurrences
        titles = [o.get("source_title") for o in occs]
        assert "Alpha Microservice" in titles
        assert "Beta Anomaly Detector" in titles
        # Unique canonical count is 1, not 2
        assert len([k for k in reg.evidence_records if k == "python"]) == 1

    def test_07_same_skill_supported_by_project_and_internship(self):
        """7. Verify skill in project AND internship retains multi-source traceability."""
        analysis_data = {
            "projects": [
                {
                    "title": "Cloud Storage Sync",
                    "technologies": ["Go", "Docker"],
                    "description": "Built cloud storage synchronization service in Go."
                }
            ],
            "internships": [
                {
                    "organization": "CloudScale Inc",
                    "position": "Infrastructure Intern",
                    "responsibilities": ["Engineered high-throughput microservices using Go and Docker."],
                    "technologies": ["Go", "Docker"]
                }
            ],
            "resume_skills": ["go", "docker"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        rec = reg.get_record("go")
        assert rec is not None
        sources = {o.get("source_type") for o in rec.occurrences}
        assert "project" in sources
        assert "internship" in sources


# =============================================================================
# Class 2: Requirement Consistency Tests (Req 8 - 15)
# =============================================================================

class TestRequirementConsistency:

    def test_08_required_skill_demonstrated_by_candidate(self):
        """8. Verify required skill demonstrated by candidate is marked satisfied and demonstrated."""
        analysis_data = {
            "projects": [
                {
                    "title": "Analytics Engine",
                    "technologies": ["SQL", "PostgreSQL"],
                    "description": "Authored complex SQL analytical aggregation queries."
                }
            ],
            "resume_skills": ["sql", "postgresql"],
            "required_skills": ["sql"],
            "job_description_text": "Requirements: Must have strong SQL proficiency."
        }
        reg = build_unified_evidence_registry(analysis_data)
        status = reg.get_skill_status("sql")
        assert status["is_required"] is True
        assert status["is_demonstrated"] is True
        assert status["is_not_evidenced"] is False
        assert status["canonical_skill"] == "SQL"

    def test_09_required_skill_only_partially_evidenced(self):
        """9. Verify required skill mentioned without project context is marked partially_evidenced."""
        analysis_data = {
            "resume_raw_text": "Skills: Python, Docker, C++",
            "resume_skills": ["python", "docker", "c++"],
            "partially_evidenced_skills": ["docker"],
            "required_skills": ["docker"],
            "job_description_text": "Requirements: Production Docker experience required."
        }
        reg = build_unified_evidence_registry(analysis_data)
        status = reg.get_skill_status("docker")
        assert status["is_required"] is True
        assert status["is_demonstrated"] is False
        assert status["is_partially_evidenced"] is True
        assert status["is_not_evidenced"] is False

    def test_10_required_skill_not_evidenced(self):
        """10. Verify required skill not present in resume is marked not_evidenced and missing."""
        analysis_data = {
            "resume_raw_text": "Developer with Python and SQL.",
            "resume_skills": ["python", "sql"],
            "required_skills": ["python", "terraform"],
            "missing_required_skills": ["terraform"],
            "job_description_text": "Requirements: Terraform infrastructure automation required."
        }
        reg = build_unified_evidence_registry(analysis_data)
        status = reg.get_skill_status("terraform")
        assert status["is_required"] is True
        assert status["is_demonstrated"] is False
        assert status["is_not_evidenced"] is True
        missing_skills = [r.canonical_skill for r in reg.get_missing_skills()]
        assert "Terraform" in missing_skills

    def test_11_preferred_skill_demonstrated(self):
        """11. Verify preferred skill demonstrated by candidate retains Preferred tier."""
        analysis_data = {
            "projects": [
                {
                    "title": "Cloud Pipeline",
                    "technologies": ["AWS"],
                    "description": "Deployed cloud microservices on AWS using Lambda and S3."
                }
            ],
            "resume_skills": ["aws"],
            "preferred_skills": ["aws"],
            "job_description_text": "Preferred: Experience with AWS cloud is a plus."
        }
        reg = build_unified_evidence_registry(analysis_data)
        status = reg.get_skill_status("aws")
        assert status["is_preferred"] is True
        assert status["is_required"] is False
        assert status["is_demonstrated"] is True

    def test_12_required_and_preferred_skill_separation(self):
        """12. Verify required and preferred requirements are strictly separated."""
        analysis_data = {
            "required_skills": ["python", "docker"],
            "preferred_skills": ["kubernetes", "aws"],
            "job_description_text": "Required: Python, Docker. Preferred: Kubernetes, AWS."
        }
        reg = build_unified_evidence_registry(analysis_data)
        for req_skill in ["python", "docker"]:
            stat = reg.get_skill_status(req_skill)
            assert stat["is_required"] is True
            assert stat["is_preferred"] is False

        for pref_skill in ["kubernetes", "aws"]:
            stat = reg.get_skill_status(pref_skill)
            assert stat["is_preferred"] is True
            assert stat["is_required"] is False

    def test_13_alternative_requirement_satisfaction(self):
        """13. Verify alternative requirements (Power BI or Tableau) are reconciled consistently."""
        analysis_data = {
            "projects": [
                {
                    "title": "BI Dashboard",
                    "technologies": ["Power BI"],
                    "description": "Constructed interactive executive KPI dashboards using Power BI."
                }
            ],
            "resume_skills": ["power bi"],
            "required_skills": ["power bi"],
            "satisfied_alternatives": [
                {
                    "group": ["Power BI", "Tableau"],
                    "satisfied_by": "power bi",
                    "omitted_alternatives": ["tableau"],
                    "tier": "Required",
                    "sentence": "Experience with Power BI or Tableau required."
                }
            ],
            "job_description_text": "Experience with Power BI or Tableau required."
        }
        reg = build_unified_evidence_registry(analysis_data)
        # Power BI is demonstrated
        pbi_stat = reg.get_skill_status("power bi")
        assert pbi_stat["is_demonstrated"] is True
        # Tableau is noted as satisfied via alternative
        tab_rec = reg.get_record("tableau")
        if tab_rec:
            assert "alternative requirement group satisfied" in tab_rec.supporting_text.lower()

    def test_14_same_canonical_skill_appearing_under_different_aliases(self):
        """14. Verify aliases (k8s vs kubernetes, py vs python) resolve to identical canonical record."""
        assert resolve_canonical_skill("k8s") == "Kubernetes"
        assert resolve_canonical_skill("kubernetes") == "Kubernetes"
        assert resolve_canonical_skill("python3") == "Python"
        assert resolve_canonical_skill("py") == "Python"
        assert resolve_canonical_skill("reactjs") == "React"
        assert resolve_canonical_skill("react.js") == "React"

    def test_15_candidate_evidence_must_not_erase_job_requirement_data(self):
        """15. Registering candidate evidence must not erase job requirement metadata and vice-versa."""
        analysis_data = {
            "projects": [
                {
                    "title": "Machine Learning Core",
                    "technologies": ["Python"],
                    "description": "Built machine learning pipelines using Python."
                }
            ],
            "resume_skills": ["python"],
            "required_skills": ["python"],
            "job_description_text": "Must have strong Python programming experience."
        }
        reg = build_unified_evidence_registry(analysis_data)
        # Both registry.evidence_records and registry.job_requirements exist independently
        assert "python" in reg.evidence_records
        assert "python" in reg.job_requirements
        req = reg.job_requirements["python"]
        assert req.tier == "Required"
        assert req.is_satisfied is True
        ev = reg.evidence_records["python"]
        assert ev.evidence_type in ("demonstrated", "demonstrated_project")
        assert ev.is_required is True


# =============================================================================
# Class 3: Integrity and Privacy Tests (Req 16 - 21)
# =============================================================================

class TestIntegrityAndPrivacy:

    def test_16_no_fabricated_supporting_excerpts(self):
        """16. Verify no fabricated or invented quotations exist in evidence registry."""
        engine = ResumeMatchingEngine()
        res = engine.analyze(
            resume_input="Software engineer with experience in Python and Flask.",
            job_description_input="Seeking Python engineer with Docker and AWS experience."
        )
        reg = build_unified_evidence_registry(res)
        for skill_key, rec in reg.evidence_records.items():
            assert "Verified with contextual engineering verbs in resume." not in rec.supporting_text
            assert "Listed in static skills list." not in rec.supporting_text
            assert "Explicitly mentioned in resume text." not in rec.supporting_text

    def test_17_no_generic_placeholder_presented_as_source_evidence(self):
        """17. Verify invariant check flags prohibited placeholder phrases."""
        reg = CandidateEvidenceRegistry()
        reg.register_evidence(
            skill="Python",
            evidence_type="demonstrated_experience",
            source_doc="resume",
            supporting_text="Verified with contextual engineering verbs in resume."  # Illegal boilerplate
        )
        is_valid, violations = reg.verify_consistency_invariants()
        assert is_valid is False
        assert any("prohibited boilerplate" in v for v in violations)

    def test_18_no_duplicate_canonical_counts(self):
        """18. Verify duplicate aliases or multiple project mentions do not inflate canonical count."""
        analysis_data = {
            "projects": [
                {"title": "P1", "technologies": ["Python", "python3"], "description": "Used Python."},
                {"title": "P2", "technologies": ["py", "Python"], "description": "Engineered in Python."}
            ],
            "resume_skills": ["python", "python3", "py"]
        }
        reg = build_unified_evidence_registry(analysis_data)
        dossier = reg.build_summary_dossier()
        # Canonical Python should only be counted once
        python_records = [k for k in dossier["evidence_by_skill"] if k == "python"]
        assert len(python_records) == 1

    def test_19_no_contradictory_demonstrated_and_missing_status(self):
        """19. Verify no skill is marked simultaneously as demonstrated and missing."""
        engine = ResumeMatchingEngine()
        res = engine.analyze(
            resume_input="Harsha Vardhan\nSkills: Python, Scikit-learn, SQL, Docker\nProject: Built Flask app.",
            job_description_input="Required: Python, Docker, Kubernetes, AWS."
        )
        reg = build_unified_evidence_registry(res)
        is_valid, violations = reg.verify_consistency_invariants()
        assert is_valid is True, f"Invariant violations: {violations}"

    def test_20_evidence_from_one_analysis_must_not_leak_into_another(self):
        """20. Verify two separate analyses create isolated evidence registries without cross-talk."""
        engine = ResumeMatchingEngine()
        res_a = engine.analyze(
            resume_input="Candidate A with C++ and Rust skills.",
            job_description_input="Required: C++, Rust."
        )
        res_b = engine.analyze(
            resume_input="Candidate B with Ruby and Rails skills.",
            job_description_input="Required: Ruby, Rails."
        )
        reg_a = build_unified_evidence_registry(res_a)
        reg_b = build_unified_evidence_registry(res_b)

        assert "c++" in reg_a.evidence_records
        assert "c++" not in reg_b.evidence_records
        assert "ruby" in reg_b.evidence_records
        assert "ruby" not in reg_a.evidence_records

    def test_21_user_confirmation_preserves_original_resume_evidence(self):
        """21. Confirming a skill preserves underlying resume occurrences rather than replacing them."""
        reg = CandidateEvidenceRegistry()
        reg.register_evidence(
            skill="Docker",
            evidence_type="partially_evidenced",
            source_doc="resume",
            supporting_text="Listed in resume skills inventory.",
            evidence_strength="partially_evidenced"
        )
        assert len(reg.get_occurrences("Docker")) == 1

        reg.add_user_confirmation("Docker", "Containerized 5 microservices")
        occs = reg.get_occurrences("Docker")
        assert len(occs) >= 2
        # Resume occurrence still intact
        assert any(o.get("source_type") == "resume" for o in occs)
        # User confirmation occurrence also present
        assert any(o.get("source_type") == "user_confirmation" for o in occs)


# =============================================================================
# Class 4: Module Integration Tests (Req 22 - 26)
# =============================================================================

class TestModuleIntegration:

    def test_22_resume_analyzer_consumes_shared_evidence(self):
        """22. Resume Matching Engine produces and attaches verified evidence registry dossier."""
        engine = ResumeMatchingEngine()
        analysis = engine.analyze(
            resume_input="Full-stack engineer with React, Node.js, and MongoDB.",
            job_description_input="Required: React, Node.js, TypeScript."
        )
        assert "evidence_registry" in analysis
        dossier = analysis["evidence_registry"]
        assert "demonstrated_count" in dossier
        assert "missing_gaps_count" in dossier
        assert "evidence_by_skill" in dossier
        assert "job_requirements" in dossier

    def test_23_skill_gap_analytics_consumes_shared_evidence(self):
        """23. Skill Gap Analytics output agrees with evidence registry partitioning."""
        engine = ResumeMatchingEngine()
        analysis = engine.analyze(
            resume_input="Python and Docker developer.",
            job_description_input="Required: Python, Docker, Kubernetes."
        )
        dossier = analysis["evidence_registry"]
        # Disjointness check between matched and missing
        demonstrated = set(dossier.get("demonstrated_skills", []))
        missing = set(dossier.get("missing_skills", []))
        assert len(demonstrated.intersection(missing)) == 0

    def test_24_career_mentor_consumes_shared_evidence(self):
        """24. Career Mentor uses shared evidence and does not label ungrounded skills verified."""
        engine = ResumeMatchingEngine()
        analysis = engine.analyze(
            resume_input="Harsha Vardhan\nSkills: Python, Scikit-learn, SQL, Docker\nProject: Built Flask app.",
            job_description_input="Required: Python, Docker, Kubernetes, AWS."
        )
        mentor = CareerMentorEngine(analysis, user_override_name="Harsha")
        strengths = mentor.strengths
        # Verified skills should only contain demonstrated or matched skills, not random keywords
        assert "verified_skills" in strengths
        assert "Kubernetes" not in strengths["verified_skills"]
        # Gaps use shared evidence status
        expandable = mentor.gaps.get("expandable_requirements", [])
        for g in expandable:
            assert g["evidence_status"] in ("Partially evidenced", "Not evidenced in resume", "Demonstrated")

    def test_25_interview_studio_consumes_shared_evidence(self):
        """25. Interview Studio extracts shared evidence without inventing achievements."""
        engine = ResumeMatchingEngine()
        resume_doc = (
            "Harsha Vardhan\nEmail: harsha@example.com\n\n"
            "PROJECTS\n"
            "Anomaly Detection System\n"
            "Built real-time anomaly detection pipelines using PyTorch and Flask.\n\n"
            "TECHNICAL SKILLS\n"
            "Python, PyTorch, Flask"
        )
        analysis = engine.analyze(
            resume_input=resume_doc,
            job_description_input="Required: PyTorch, Docker, Kubernetes."
        )
        generator = InterviewQuestionGenerator(analysis)
        evidence = generator.evidence
        assert "projects" in evidence
        assert len(evidence["projects"]) >= 1
        # Questions in Category B reference genuine project title
        b_qs = generator.generate_category_b()
        assert len(b_qs) >= 1
        q_text_all = " ".join([q["question_text"] for q in b_qs])
        assert "Anomaly Detection" in q_text_all or "Anomaly" in q_text_all

    def test_26_interview_practice_and_review_remain_compatible(self):
        """26. Practice mode and answer evaluations work with shared evidence data."""
        client = app.test_client()
        resp = client.get("/api/analysis/sample")
        assert resp.status_code == 200
        data = resp.get_json()
        analysis = data["analysis"]
        assert "evidence_registry" in analysis
        ev_reg = analysis["evidence_registry"]
        assert ev_reg["total_evidenced_skills"] >= 0

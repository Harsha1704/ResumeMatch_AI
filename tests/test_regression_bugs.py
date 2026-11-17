"""
Comprehensive Regression Test Suite for ResumeMatch AI Defect Corrections (Bug 1 through Bug 12).
Verifies:
1. Matched count never exceeds required count.
2. Skill coverage stays within 0–100%.
3. Required skill partition accounting: fully_matched + partial + missing == total_required.
4. Partially evidenced skills are never double-counted as missing or fully matched.
5. R language boundary matching (rejects research, reporting, requirements).
6. C language boundary matching (rejects letter c in copyright, section c).
7. Go language boundary matching (rejects verb 'go').
8. C++ and C# token preservation.
9. Generic words (applications, commitment, enthusiasm, ownership) do not become mandatory technical skills.
10. Required/preferred/unspecified classification into 3 mutually exclusive tiers.
11. Project dates attach to project titles.
12. CERTIFICATES and section headers are excluded from project extraction.
13. Missing experience duration is reported as unestablished, not fabricated as zero / satisfied.
14. Recommendations match competency domains (technical project vs professional workflow vs behavioral).
15. Learning resource summary agrees with actual gaps (no contradiction).
16. Dataset class percentage annotations use correct split denominators.
17. Result page and skill gap page display consistent counts.
18. Printed report structure renders individual badges and consistent values.
"""

import pytest
import re
import pandas as pd
from src.analysis.matching_engine import analyze_resume_and_job
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.skill_gap import SkillGapAnalyzer
from src.analysis.experience_analyzer import ExperienceAnalyzer
from src.analysis.recommendation_engine import RecommendationEngine
from src.preprocessing.skill_extractor import SkillEngine, categorize_competency, TAXONOMY_GENERIC
from src.utils.data_loader import load_primary_dataset
from src.utils.visualizer import plot_class_distribution
from app import app


# -------------------------------------------------------------------------
# Test 1: Matched Count Never Exceeds Required Count
# -------------------------------------------------------------------------
def test_matched_count_never_exceeds_required():
    resume = "Candidate skilled in Python, Docker, SQL, Kubernetes, AWS, React, C++, Redis, Linux, Git, Java, TypeScript."
    job = """
    Target Position: Python Specialist
    Mandatory Requirements:
    - Python
    - Docker
    """
    result = analyze_resume_and_job(resume, job)
    assert result["status"] == "success"
    summary = result["skill_gap_summary"]

    assert summary["matched_required_count"] <= summary["total_required_count"]
    assert summary["total_required_count"] == 2
    assert summary["matched_required_count"] == 2


# -------------------------------------------------------------------------
# Test 2: Skill Coverage Stays Within 0–100%
# -------------------------------------------------------------------------
def test_skill_coverage_bounds():
    # Case A: High skill overlap
    res_high = analyze_resume_and_job(
        "Senior Python Engineer with Docker, SQL, Kubernetes.",
        "Mandatory: Python, Docker, SQL."
    )
    assert 0.0 <= res_high["skill_coverage"] <= 100.0
    assert 0.0 <= res_high["skill_gap_summary"]["skill_coverage_pct"] <= 100.0

    # Case B: Zero overlap
    res_zero = analyze_resume_and_job(
        "Chef with pastry baking and culinary experience.",
        "Mandatory: C++, Rust, Embedded Firmware."
    )
    assert res_zero["skill_coverage"] == 0.0

    # Case C: Zero mandatory requirements
    res_none = analyze_resume_and_job(
        "Software Engineer with Python.",
        "General company job overview with no explicit mandatory skills."
    )
    assert 0.0 <= res_none["skill_coverage"] <= 100.0


# -------------------------------------------------------------------------
# Test 3: Required Skill Partition Accounting Identity
# -------------------------------------------------------------------------
def test_required_skill_partition_identity():
    resume = (
        "SKILLS: Python, Docker, Kubernetes, AWS\n"
        "EXPERIENCE:\n"
        "Engineered scalable microservices using Python and Docker.\n"
    )
    job = """
    Required Qualifications:
    - Python
    - Docker
    - Kubernetes
    - PostgreSQL
    - Terraform
    """
    result = analyze_resume_and_job(resume, job)
    summary = result["skill_gap_summary"]

    fully_matched = summary["fully_matched_required_count"]
    partially_evidenced = summary["partially_evidenced_required_count"]
    missing = summary["missing_required_count"]
    total = summary["total_required_count"]

    assert fully_matched + partially_evidenced + missing == total
    assert summary["matched_required_count"] == fully_matched + partially_evidenced


# -------------------------------------------------------------------------
# Test 4: Partially Evidenced Skills Never Double-Counted
# -------------------------------------------------------------------------
def test_partially_evidenced_skills_not_double_counted():
    gap_analyzer = SkillGapAnalyzer()
    job_analyzer = JobDescriptionAnalyzer()

    resume = "SKILLS: Kubernetes, Docker, Python\nEXPERIENCE:\nDeveloped backend in Python."
    job = "Required:\n- Python\n- Kubernetes\n- Terraform"

    job_res = job_analyzer.analyze(job)
    gap = gap_analyzer.analyze_gap(resume, job_res, job_raw_text=job)

    # Kubernetes is partially evidenced (no verb)
    assert "kubernetes" in gap["partially_evidenced_required_skills"]
    assert "kubernetes" not in gap["missing_required_skills"]
    assert "kubernetes" not in gap["fully_matched_required_skills"]
    assert "kubernetes" in gap["matched_required_skills"]


# -------------------------------------------------------------------------
# Test 5: R Language Boundary Matching
# -------------------------------------------------------------------------
def test_r_language_boundary_matching():
    engine = SkillEngine()

    # R inside non-technical words must NOT match R
    text_with_words = "Research and reporting requirements across our corporate resources."
    skills = engine.extract_skills(text_with_words)
    assert "r" not in skills

    # Standalone letter in generic prose must NOT match R
    generic_text = "Please refer to section r of our terms. John R. Doe authored this doc."
    assert "r" not in engine.extract_skills(generic_text)

    # Legitimate R programming MUST match R
    r_prog = "Statistical data analysis using R programming and ggplot2."
    assert "r" in engine.extract_skills(r_prog)

    r_studio = "Developed predictive models in RStudio with tidyverse and Python."
    assert "r" in engine.extract_skills(r_studio)


# -------------------------------------------------------------------------
# Test 6: C Language Boundary Matching
# -------------------------------------------------------------------------
def test_c_language_boundary_matching():
    engine = SkillEngine()

    # Letter c in ordinary prose must NOT match C
    generic_text = "Copyright (c) 2026. Grade C certified facility in area c."
    assert "c" not in engine.extract_skills(generic_text)

    # Legitimate C programming MUST match C
    c_prog = "Low-level Linux kernel driver development in C programming and Assembly."
    assert "c" in engine.extract_skills(c_prog)

    c_slash = "Embedded firmware engineered using C/C++."
    assert "c" in engine.extract_skills(c_slash)


# -------------------------------------------------------------------------
# Test 7: Go Language Boundary Matching
# -------------------------------------------------------------------------
def test_go_language_boundary_matching():
    engine = SkillEngine()

    # English verb "go" must NOT match Go
    verb_text = "We go through great lengths to go above and beyond for our customers. Go to the office."
    assert "go" not in engine.extract_skills(verb_text)

    # Legitimate Golang MUST match Go
    golang_text = "Backend microservices built using Golang and Docker."
    assert "go" in engine.extract_skills(golang_text)

    go_lang_text = "Experienced with Go programming language and Kubernetes."
    assert "go" in engine.extract_skills(go_lang_text)


# -------------------------------------------------------------------------
# Test 8: C++ and C# Token Preservation
# -------------------------------------------------------------------------
def test_cpp_and_csharp_token_preservation():
    engine = SkillEngine()
    text = "Core expertise in C++, C#, .NET, Node.js, and PL/SQL with CI/CD pipelines."
    skills = engine.extract_skills(text)

    for token in ["c++", "c#", ".net", "node.js", "pl/sql", "ci/cd"]:
        assert token in skills, f"Failed to preserve token: {token}"


# -------------------------------------------------------------------------
# Test 9: Generic Words Do Not Become Mandatory Technical Skills
# -------------------------------------------------------------------------
def test_generic_words_not_technical_skills():
    engine = SkillEngine()
    text = "Demonstrates enthusiasm, commitment, and strong ownership of applications and solutions."
    skills = engine.extract_skills(text)

    for generic in ["applications", "commitment", "enthusiasm", "ownership"]:
        assert generic not in skills, f"Generic term '{generic}' erroneously extracted as skill"
        assert categorize_competency(generic) == TAXONOMY_GENERIC


# -------------------------------------------------------------------------
# Test 10: Required, Preferred, and Unspecified Classification
# -------------------------------------------------------------------------
def test_three_tier_requirement_classification():
    job_text = """
    Job Title: Senior Software Engineer
    About the Company:
    We build web applications using modern tools.
    
    Required Skills:
    - Python
    - Docker
    - SQL
    
    Preferred Qualifications:
    - Kubernetes
    - Redis
    
    Responsibilities:
    - Collaborate using Git and Jira
    """
    analyzer = JobDescriptionAnalyzer()
    res = analyzer.analyze(job_text)

    assert set(res["required_skills"]) == {"python", "docker", "sql"}
    assert set(res["preferred_skills"]) == {"kubernetes", "redis"}
    assert "git" in res["unspecified_skills"] or "jira" in res["unspecified_skills"]

    # Mutual exclusivity
    req_set = set(res["required_skills"])
    pref_set = set(res["preferred_skills"])
    unspec_set = set(res["unspecified_skills"])
    assert len(req_set.intersection(pref_set)) == 0
    assert len(req_set.intersection(unspec_set)) == 0
    assert len(pref_set.intersection(unspec_set)) == 0


# -------------------------------------------------------------------------
# Test 11: Project Dates Attach to Project Titles
# -------------------------------------------------------------------------
def test_project_dates_attach_to_titles():
    analyzer = ExperienceAnalyzer()
    resume = """
    PROJECTS
    Distributed Cloud Pipeline
    Jan 2024 - May 2024
    Built scalable ETL data pipelines using Python and Docker.
    
    Real-Time Analytics Dashboard
    Sep 2023 - Dec 2023
    https://github.com/example/analytics-dash
    Implemented Chart.js visualizations with FastAPI backend.
    """
    projects = analyzer.detect_projects(resume)
    assert len(projects) >= 2

    p1 = projects[0]
    assert "pipeline" in p1["title"].lower()
    assert p1["dates"] is not None
    assert "2024" in p1["dates"]

    p2 = projects[1]
    assert "dashboard" in p2["title"].lower()
    assert p2["dates"] is not None
    assert p2["github_url"] is not None


# -------------------------------------------------------------------------
# Test 12: CERTIFICATES is Not a Project
# -------------------------------------------------------------------------
def test_certificates_and_dates_not_projects():
    analyzer = ExperienceAnalyzer()
    resume = """
    PROJECTS
    E-Commerce API Service
    Jan 2024 - Apr 2024
    Developed microservices in Python.
    
    CERTIFICATES
    AWS Certified Cloud Practitioner
    Sep 2023
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Engineering
    """
    projects = analyzer.detect_projects(resume)
    titles = [p["title"].upper() for p in projects]

    assert "CERTIFICATES" not in titles
    assert "EDUCATION" not in titles
    assert not any("JAN 2024" in t for t in titles)
    assert len(projects) == 1
    assert "e-commerce" in projects[0]["title"].lower()


# -------------------------------------------------------------------------
# Test 13: Missing Experience Reported as Unestablished, Not Zero
# -------------------------------------------------------------------------
def test_missing_experience_reported_as_unestablished():
    analyzer = ExperienceAnalyzer()

    # Resume with coursework but no stated professional tenure
    resume = "CS Graduate skilled in Python, SQL, and Algorithms. Completed several capstone projects."
    res = analyzer.analyze_experience(resume, job_required_years=3.0)

    assert res["has_resume_exp"] is False
    assert res["resume_exp_display"] == "Professional experience not established"
    assert res["meets_experience_requirement"] is False
    assert "not verified" in res["alignment_status"].lower() or "not established" in res["alignment_status"].lower()


# -------------------------------------------------------------------------
# Test 14: Recommendations Match Competency Categories
# -------------------------------------------------------------------------
def test_recommendations_competency_categories():
    rec_engine = RecommendationEngine()
    exp_info = {
        "experience_gap_years": -2.0,
        "meets_experience_requirement": False,
        "has_job_exp": True,
        "job_required_years": 3.0,
        "resume_years_exp": 1.0,
        "projects_count": 1
    }

    recs = rec_engine.generate_recommendations(
        missing_required=["docker", "agile", "leadership"],
        missing_preferred=["redis"],
        partially_evidenced=["python"],
        experience_analysis=exp_info,
        job_title="Software Engineer"
    )

    categories = [r["category"] for r in recs]
    assert "Technical Skill Gap" in categories
    assert "Professional Methodology Gap" in categories
    assert "Behavioral Competency Evidence" in categories

    # Verify no software project recommendation for generic terms
    for r in recs:
        rec_text = r["recommendation"].lower() + " " + r["actionable_step"].lower()
        assert "build a project using commitment" not in rec_text
        assert "build a project using enthusiasm" not in rec_text


# -------------------------------------------------------------------------
# Test 15: Learning Resource Summary Agrees with Actual Gaps
# -------------------------------------------------------------------------
def test_learning_resources_gap_agreement():
    rec_engine = RecommendationEngine()

    # When gaps exist with curated resources
    resources = rec_engine.get_learning_resources(["docker", "kubernetes"])
    assert len(resources) >= 2
    skills_in_res = {r["skill"].lower() for r in resources}
    assert "docker" in skills_in_res
    assert "kubernetes" in skills_in_res

    # When missing skill has no curated resource, returns empty list without inventing fake URLs
    obscure_res = rec_engine.get_learning_resources(["obscure_custom_internal_framework"])
    assert len(obscure_res) == 0


# -------------------------------------------------------------------------
# Test 16: Dataset Percentage Annotations Use Correct Denominators
# -------------------------------------------------------------------------
def test_dataset_percentage_denominators():
    train_df, test_df = load_primary_dataset()
    total_train = len(train_df)  # 6240
    total_test = len(test_df)    # 1759

    assert total_train == 6240
    assert total_test == 1759

    # Train class counts
    tr_counts = train_df["label"].value_counts().to_dict()
    assert abs((tr_counts["No Fit"] / total_train) * 100 - 50.35) < 0.1
    assert abs((tr_counts["Potential Fit"] / total_train) * 100 - 24.94) < 0.1
    assert abs((tr_counts["Good Fit"] / total_train) * 100 - 24.71) < 0.1

    # Test class counts
    te_counts = test_df["label"].value_counts().to_dict()
    assert abs((te_counts["No Fit"] / total_test) * 100 - 48.72) < 0.1
    assert abs((te_counts["Potential Fit"] / total_test) * 100 - 25.24) < 0.1
    assert abs((te_counts["Good Fit"] / total_test) * 100 - 26.04) < 0.1


# -------------------------------------------------------------------------
# Test 17: Result Page and Skill Gap Page Use Consistent Counts
# -------------------------------------------------------------------------
def test_consistent_counts_across_views():
    app.config["TESTING"] = True
    with app.test_client() as client:
        tok = client.get("/api/csrf-token").get_json()["csrf_token"]
        form_data = {
            "resume_text": "Experienced Python and Docker developer with SQL skills.",
            "job_description": "Required: Python, Docker, Kubernetes, AWS. Preferred: Redis.",
            "csrf_token": tok
        }
        resp = client.post("/analyze", data=form_data, follow_redirects=False)
        assert resp.status_code == 302
        analysis_id = resp.headers["Location"].split("=")[-1]

        # Results page
        res_page = client.get(f"/results?id={analysis_id}")
        html_res = res_page.data.decode("utf-8")

        # Skill gap page
        gap_page = client.get(f"/skill-gap?id={analysis_id}")
        html_gap = gap_page.data.decode("utf-8")

        # Both pages must display 2 / 4 or 2 of 4 required skills evidenced
        assert "2 / 4" in html_res
        assert "2</strong> of <strong>4" in html_gap or "2 of 4" in html_gap


# -------------------------------------------------------------------------
# Test 18: Printed Report Stylesheet Excludes Navigation and Formats Badges
# -------------------------------------------------------------------------
def test_print_stylesheet_rules():
    with open("static/css/dashboard.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert "@media print" in css
    assert "A4 portrait" in css
    assert "#sidebar" in css
    assert "page-break-inside: avoid" in css
    assert "a[href]:after" in css  # Avoids exposing raw URLs in print

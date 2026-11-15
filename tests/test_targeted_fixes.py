"""
Regression and verification tests for targeted ResumeMatch AI fixes:
1. Skill Coverage Consistency (Full Coverage vs Any-Evidence Coverage)
2. Education Requirement Extraction (No MS Word/Excel false positives; authentic degrees; default fallback)
3. No Blank Preferred Skill Badges
4. Skill Taxonomy (8 categories, soft skills, productivity software, domain-appropriate recommendations)
"""

import pytest
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.skill_gap import SkillGapAnalyzer
from src.analysis.matching_engine import ResumeMatchingEngine, analyze_resume_and_job
from src.preprocessing.skill_extractor import (
    SkillEngine,
    categorize_competency,
    TAXONOMY_PROGRAMMING_LANGUAGES,
    TAXONOMY_FRAMEWORKS_LIBRARIES,
    TAXONOMY_DATABASES,
    TAXONOMY_DEVELOPER_TOOLS,
    TAXONOMY_CLOUD_INFRASTRUCTURE,
    TAXONOMY_PRODUCTIVITY,
    TAXONOMY_PROFESSIONAL,
    TAXONOMY_SOFT,
    TAXONOMY_GENERIC
)
from src.analysis.recommendation_engine import RecommendationEngine


# -------------------------------------------------------------------------
# 1. Skill Coverage Consistency Tests
# -------------------------------------------------------------------------
def test_skill_coverage_consistency():
    gap_analyzer = SkillGapAnalyzer()

    # Total 25 required skills
    req_skills = [
        "python", "docker", "sql", "git", "linux",
        "react", "amazon web services", "kubernetes", "java", "c++",
        "html", "css", "postgresql", "redis", "flask",
        "django", "mongodb", "fastapi", "terraform", "ansible",
        "jenkins", "ci/cd", "pandas", "numpy", "scikit-learn"
    ]
    job_analysis = {
        "required_skills": req_skills,
        "preferred_skills": ["graphql"],
        "unspecified_skills": [],
        "all_skills": req_skills + ["graphql"]
    }

    # Resume with:
    # 5 fully evidenced (active verbs + context)
    # 3 partially evidenced (keyword list only)
    # 17 unevidenced
    resume_text = """
    EXPERIENCE:
    - Designed and implemented scalable backend services using Python and Docker.
    - Optimized relational database queries and transactions in SQL.
    - Maintained version control workflows and release tags using Git.
    - Deployed and automated system provisioning on Linux servers.

    SKILLS:
    React, AWS, Kubernetes
    """

    res = gap_analyzer.analyze_gap(resume_text, job_analysis)

    total_req = res["total_required_count"]
    fully_req = res["fully_matched_required_count"]
    partial_req = res["partially_evidenced_required_count"]
    matched_req = res["matched_required_count"]

    assert total_req == 25
    assert fully_req == 5
    assert partial_req == 3
    assert matched_req == 8

    # Full Coverage = 5 / 25 = 20.0%
    # Any-Evidence Coverage = 8 / 25 = 32.0%
    assert res["full_coverage_pct"] == 20.0
    assert res["any_coverage_pct"] == 32.0
    assert res["full_coverage_display"] == "20.0%"
    assert res["any_coverage_display"] == "32.0%"


def test_matching_engine_skill_coverage_consistency():
    resume = """
    EXPERIENCE:
    - Architected microservices with Python and Docker.
    SKILLS:
    SQL
    """
    job = """
    Requirements:
    - Python
    - Docker
    - SQL
    - Kubernetes
    """
    result = analyze_resume_and_job(resume, job)

    assert result["status"] == "success"
    summary = result["skill_gap_summary"]

    assert summary["total_required_count"] == 4
    assert summary["fully_matched_required_count"] == 2
    assert summary["partially_evidenced_required_count"] == 1
    assert summary["matched_required_count"] == 3

    # Full Coverage: 2 / 4 = 50.0%
    # Any Coverage: 3 / 4 = 75.0%
    assert result["full_coverage_pct"] == 50.0
    assert result["any_coverage_pct"] == 75.0
    assert summary["full_coverage_pct"] == 50.0
    assert summary["any_coverage_pct"] == 75.0


# -------------------------------------------------------------------------
# 2. Education Requirement Extraction Tests
# -------------------------------------------------------------------------
def test_education_extraction_excludes_productivity_software():
    analyzer = JobDescriptionAnalyzer()

    # Job description mentioning MS Word and MS Excel but NO academic degrees
    job_text = """
    Job Title: Office Administrator
    Requirements:
    - 3+ years experience.
    - Expert knowledge of MS Word, MS Excel, and MS PowerPoint.
    - Strong communication skills.
    """
    edu = analyzer.extract_education_requirements(job_text)
    assert edu == ["No explicit education requirement identified."]


def test_education_extraction_authentic_degrees():
    analyzer = JobDescriptionAnalyzer()

    # Degree types: B.Tech, MCA, Master's, etc.
    job_btech = "Qualifications: B.Tech in Computer Science or related engineering degree. Must know MS Office."
    edu_btech = analyzer.extract_education_requirements(job_btech)
    assert any("b.tech" in e.lower() for e in edu_btech)
    assert not any("office" in e.lower() for e in edu_btech)

    job_mca = "Requires MCA or Bachelor's degree in Software Engineering. Experience with Excel is a plus."
    edu_mca = analyzer.extract_education_requirements(job_mca)
    assert any("mca" in e.lower() or "bachelor" in e.lower() for e in edu_mca)
    assert not any("excel" in e.lower() for e in edu_mca)

    job_ms = "Candidates must possess an M.S. degree in Data Science or Ph.D. in Computer Science."
    edu_ms = analyzer.extract_education_requirements(job_ms)
    assert any("m.s" in e.lower() or "ph.d" in e.lower() for e in edu_ms)


# -------------------------------------------------------------------------
# 3. No Blank Preferred Skill Badges Tests
# -------------------------------------------------------------------------
def test_no_blank_preferred_skill_badges():
    resume_text = "Experienced developer with Python and SQL."
    job_text = """
    Required:
    - Python
    Preferred:
    - Docker
    - Redis
    """
    res = analyze_resume_and_job(resume_text, job_text)

    # Check that no skill lists have empty strings or whitespace
    for sk_list in [
        res["matched_skills"],
        res["matched_required_skills"],
        res["matched_preferred_skills"],
        res["missing_required_skills"],
        res["missing_preferred_skills"]
    ]:
        for sk in sk_list:
            assert isinstance(sk, str)
            assert len(sk.strip()) > 0
            assert sk.strip() == sk


# -------------------------------------------------------------------------
# 4. Skill Taxonomy and Domain-Appropriate Recommendations Tests
# -------------------------------------------------------------------------
def test_skill_taxonomy_8_categories():
    # 1. Programming languages
    assert categorize_competency("Python") == TAXONOMY_PROGRAMMING_LANGUAGES
    assert categorize_competency("Java") == TAXONOMY_PROGRAMMING_LANGUAGES
    assert categorize_competency("C++") == TAXONOMY_PROGRAMMING_LANGUAGES

    # 2. Frameworks and libraries
    assert categorize_competency("React") == TAXONOMY_FRAMEWORKS_LIBRARIES
    assert categorize_competency("Django") == TAXONOMY_FRAMEWORKS_LIBRARIES
    assert categorize_competency("scikit-learn") == TAXONOMY_FRAMEWORKS_LIBRARIES

    # 3. Databases
    assert categorize_competency("PostgreSQL") == TAXONOMY_DATABASES
    assert categorize_competency("MongoDB") == TAXONOMY_DATABASES
    assert categorize_competency("SQL") == TAXONOMY_DATABASES

    # 4. Developer tools
    assert categorize_competency("Git") == TAXONOMY_DEVELOPER_TOOLS
    assert categorize_competency("Jira") == TAXONOMY_DEVELOPER_TOOLS

    # 5. Cloud and infrastructure
    assert categorize_competency("Docker") == TAXONOMY_CLOUD_INFRASTRUCTURE
    assert categorize_competency("Kubernetes") == TAXONOMY_CLOUD_INFRASTRUCTURE
    assert categorize_competency("Amazon Web Services") == TAXONOMY_CLOUD_INFRASTRUCTURE

    # 6. Productivity software
    assert categorize_competency("MS Word") == TAXONOMY_PRODUCTIVITY
    assert categorize_competency("Word") == TAXONOMY_PRODUCTIVITY
    assert categorize_competency("Microsoft Excel") == TAXONOMY_PRODUCTIVITY
    assert categorize_competency("PowerPoint") == TAXONOMY_PRODUCTIVITY

    # 7. Professional competencies
    assert categorize_competency("Agile") == TAXONOMY_PROFESSIONAL
    assert categorize_competency("System Architecture") == TAXONOMY_PROFESSIONAL

    # 8. Soft skills
    assert categorize_competency("Communication Skills") == TAXONOMY_SOFT
    assert categorize_competency("Communication") == TAXONOMY_SOFT
    assert categorize_competency("Teamwork") == TAXONOMY_SOFT
    assert categorize_competency("Leadership") == TAXONOMY_SOFT

    # Generic terms
    assert categorize_competency("Application Software") == TAXONOMY_GENERIC
    assert categorize_competency("Applications") == TAXONOMY_GENERIC


def test_recommendations_domain_appropriate():
    rec_engine = RecommendationEngine()

    # Test soft skill recommendation (e.g. communication)
    recs_soft = rec_engine.generate_recommendations(
        missing_required=["communication"],
        missing_preferred=[],
        partially_evidenced=[],
        experience_analysis={"detected_projects": [{"title": "P1"}]},
        job_title="Project Lead"
    )

    # Check that recommendation for communication does NOT suggest coding project or GitHub
    soft_rec = next((r for r in recs_soft if "communication" in r["recommendation"].lower() or "communication" in r["actionable_step"].lower()), None)
    assert soft_rec is not None
    assert "github" not in soft_rec["actionable_step"].lower()
    assert "pipeline" not in soft_rec["actionable_step"].lower()
    assert "prototype service" not in soft_rec["actionable_step"].lower()

    # Test productivity software recommendation (e.g. word)
    recs_prod = rec_engine.generate_recommendations(
        missing_required=["word"],
        missing_preferred=[],
        partially_evidenced=[],
        experience_analysis={"detected_projects": [{"title": "P1"}]},
        job_title="Business Analyst"
    )
    prod_rec = next((r for r in recs_prod if "word" in r["recommendation"].lower() or "word" in r["actionable_step"].lower()), None)
    assert prod_rec is not None
    assert "github" not in prod_rec["actionable_step"].lower()
    assert "prototype service" not in prod_rec["actionable_step"].lower()

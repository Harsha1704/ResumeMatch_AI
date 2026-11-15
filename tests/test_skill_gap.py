"""
Unit tests for Skill Gap Analyzer, partial evidence detection, and prioritized roadmap.
"""

import pytest
from src.analysis.skill_gap import SkillGapAnalyzer
from src.analysis.job_analyzer import JobDescriptionAnalyzer


@pytest.fixture
def analyzers():
    return SkillGapAnalyzer(), JobDescriptionAnalyzer()


def test_matched_and_missing_skills(analyzers):
    gap_analyzer, job_analyzer = analyzers

    resume = (
        "Software Engineer with 4 years experience.\n"
        "Proficient in Python, Docker, PostgreSQL, and Linux.\n"
        "Built and deployed scalable REST APIs."
    )
    job = (
        "Job Title: Senior Backend Engineer\n"
        "Required Skills:\n"
        "- Python\n"
        "- Docker\n"
        "- Kubernetes\n"
        "- AWS\n"
        "Preferred Qualifications:\n"
        "- Redis\n"
    )

    job_res = job_analyzer.analyze(job)
    gap = gap_analyzer.analyze_gap(resume, job_res, job_raw_text=job)

    assert gap["status"] == "success"
    # Python and Docker are in both
    assert "python" in gap["matched_skills"]
    assert "docker" in gap["matched_skills"]

    # Kubernetes and AWS are missing required skills
    assert "kubernetes" in gap["missing_required_skills"]
    assert "amazon web services" in gap["missing_preferred_skills"] or "amazon web services" in gap["missing_required_skills"]

    # Skill coverage
    assert 0.0 < gap["skill_coverage_pct"] < 100.0


def test_partially_evidenced_skills(analyzers):
    gap_analyzer, _ = analyzers

    # Resume has 'Kubernetes' only in a comma list, but 'Python' with implementation verbs
    resume = (
        "SKILLS: Python, Kubernetes, Redis, Docker\n"
        "EXPERIENCE:\n"
        "Developed and optimized distributed Python backend services using Docker.\n"
    )

    matched = ["python", "kubernetes", "docker"]
    solid, partial = gap_analyzer.detect_partially_evidenced_skills(resume, matched)

    assert "python" in solid or "docker" in solid
    assert "kubernetes" in partial


def test_prioritized_skill_gaps(analyzers):
    gap_analyzer, _ = analyzers

    missing_req = ["kubernetes", "terraform"]
    missing_pref = ["graphql"]
    job_text = "Must have Kubernetes experience. Kubernetes is central to our infrastructure. Terraform is required."

    prioritized = gap_analyzer.prioritize_skill_gaps(missing_req, missing_pref, job_text)
    assert len(prioritized) == 3
    # Top item should be required with highest frequency (Kubernetes mentioned 2x)
    assert prioritized[0]["skill"] == "kubernetes"
    assert prioritized[0]["type"] == "Required"
    assert prioritized[-1]["type"] == "Preferred"

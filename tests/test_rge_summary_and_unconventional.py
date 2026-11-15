"""
tests/test_rge_summary_and_unconventional.py
Regression tests for Requirement-Gated Extraction (RGE):
Ensures skills residing in resume summaries and unconventional sections are retained.
"""

import pytest
from src.phase12f.long_document_handler import RequirementGatedExtractor
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text

@pytest.fixture
def rge_extractor():
    return RequirementGatedExtractor(max_total_tokens=256)

@pytest.fixture
def skill_engine():
    return SkillEngine()

def test_rge_captures_skills_in_professional_summary(rge_extractor, skill_engine):
    """
    Regression Test: Candidate has skills (Python, SQL, AWS) exclusively in the Professional Summary.
    Ensures RGE extracts these skills and does not discard the summary.
    """
    resume_text = (
        "PROFESSIONAL SUMMARY\n"
        "Highly accomplished Data Engineer with 8 years of experience. Expert in Python, SQL, and AWS cloud infrastructure. "
        "Proven track record in optimizing ETL pipelines.\n\n"
        "WORK HISTORY\n"
        "Senior Engineer at Tech Corp (2018 - Present)\n"
        "Led a multidisciplinary engineering team across distributed systems."
    )
    jd_text = (
        "JOB SUMMARY\n"
        "We are looking for a Senior Data Engineer proficient in Python, SQL, and AWS.\n"
        "Requirements:\n"
        "- 5+ years of experience\n"
        "- Deep knowledge of Python and SQL\n"
        "- Experience deploying on AWS"
    )
    res = rge_extractor.transform_pair(resume_text, jd_text)
    structured_text = res["structured_text"]
    
    extracted_skills = set(skill_engine.extract_skills(clean_text(structured_text)))
    assert "python" in extracted_skills
    assert "sql" in extracted_skills
    assert ("aws" in extracted_skills or "aws cloud" in extracted_skills or "amazon web services" in extracted_skills)
    assert res["exp_gap"] >= 0.0

def test_rge_captures_unconventional_technical_profile(rge_extractor, skill_engine):
    """
    Regression Test: Resume uses unconventional heading 'CORE COMPETENCIES & TOOLKIT'
    instead of standard 'SKILLS' or 'WORK HISTORY'.
    """
    resume_text = (
        "CANDIDATE DOSSIER\n"
        "Jane Doe - Software Architect\n\n"
        "CORE COMPETENCIES & TOOLKIT\n"
        "* Kubernetes container orchestration and Docker virtualization\n"
        "* Distributed stream processing with Apache Kafka\n"
        "* Go programming and microservice design\n\n"
        "CAREER HIGHLIGHTS\n"
        "Architected enterprise real-time messaging gateway handling 100k msg/sec."
    )
    jd_text = (
        "REQUIREMENTS:\n"
        "- Mandatory hands-on experience with Kubernetes, Docker, and Kafka.\n"
        "- Solid programming skills in Go."
    )
    res = rge_extractor.transform_pair(resume_text, jd_text)
    structured_text = res["structured_text"]
    
    extracted_skills = set(skill_engine.extract_skills(clean_text(structured_text)))
    assert "kubernetes" in extracted_skills
    assert "docker" in extracted_skills
    assert "kafka" in extracted_skills
    assert "go" in extracted_skills

def test_rge_handles_empty_or_malformed_sections(rge_extractor):
    """
    Ensures RGE does not crash or fail when encountering sparse or non-standard formatting.
    """
    resume_text = "Experienced Developer. Contact: test@example.com."
    jd_text = "Junior Developer needed."
    res = rge_extractor.transform_pair(resume_text, jd_text)
    assert "JOB REQUIREMENTS" in res["structured_text"]
    assert "CANDIDATE QUALIFICATIONS" in res["structured_text"]

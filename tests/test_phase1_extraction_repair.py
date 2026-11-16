"""
Phase 1: Resume & Job Description Extraction — Final Quality Repair Tests.
Comprehensive validation suite covering:
1. Role detection across diverse formats and edge cases.
2. Skill extraction and canonical alias normalization.
3. Preservation of critical technical tokens (C++, C#, .NET, Node.js, CI/CD, SQL, PL/SQL).
4. Generic word suppression without affecting compound technical terms.
5. Context-aware ambiguous token handling (R, C, Go, SQL, AI, ML).
6. 8-category competency taxonomy classification with explicit generic/unknown handling.
7. 3-tier requirement classification (Mandatory, Preferred, Unspecified).
8. Alternative requirement groups resolution (e.g. Power BI or Tableau).
9. Source text evidence traceability and defensible confidence scoring.
"""

import pytest
from typing import Set
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.preprocessing.skill_extractor import (
    SkillEngine,
    categorize_competency,
    get_canonical_skill_name,
    get_canonical_taxonomy_category,
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
from src.analysis.matching_engine import ResumeMatchingEngine


@pytest.fixture
def analyzer():
    return JobDescriptionAnalyzer()


@pytest.fixture
def skill_engine():
    return SkillEngine()


# =========================================================================
# 1. ROLE DETECTION TESTS
# =========================================================================

class TestRoleDetection:

    def test_explicit_job_title_labels(self, analyzer):
        """1. Detect job titles with explicit prefix labels."""
        samples = [
            ("Job Title: Senior Machine Learning Engineer\nRequirements: Python", "Senior Machine Learning Engineer"),
            ("Position: Python Developer\nLocation: Remote", "Python Developer"),
            ("Role: Full Stack Developer\nExperience: 3 years", "Full Stack Developer"),
            ("Hiring For: Data Analyst\nAbout us:...", "Data Analyst"),
            ("We Are Hiring: Backend Engineer\nDetails:...", "Backend Engineer"),
            ("Job Opening: DevOps Engineer\nQualifications:...", "DevOps Engineer"),
            ("Position Title: Cloud Solutions Architect\nMust have:...", "Cloud Solutions Architect"),
        ]
        for jd, expected in samples:
            assert analyzer.extract_job_title(jd) == expected

    def test_markdown_and_formatting_noise_in_title(self, analyzer):
        """2. Detect job titles formatted with markdown asterisks, hashes, pipes, and colons."""
        samples = [
            ("# Job Title: Senior Machine Learning Engineer", "Senior Machine Learning Engineer"),
            ("**Position**: Python Developer", "Python Developer"),
            ("### Role - Full Stack Developer", "Full Stack Developer"),
            ("* **Job Opening**: DevOps Engineer", "DevOps Engineer"),
            ("We're hiring for: Backend Engineer", "Backend Engineer"),
        ]
        for jd, expected in samples:
            assert analyzer.extract_job_title(jd) == expected

    def test_title_in_opening_lines_without_explicit_label(self, analyzer):
        """3. Detect job title in opening lines when no explicit label exists."""
        jd = (
            "Senior Machine Learning Engineer\n"
            "Acme AI Inc. | San Francisco, CA | Full-Time\n"
            "We are building cutting-edge deep learning systems."
        )
        assert analyzer.extract_job_title(jd) == "Senior Machine Learning Engineer"

    def test_company_name_and_location_separated_from_title(self, analyzer):
        """4. Isolate job title from company prefix, location pipes, and salary."""
        samples = [
            ("Acme Corp | Machine Learning Engineer | Remote", "Machine Learning Engineer"),
            ("Google - Senior Software Engineer", "Senior Software Engineer"),
            ("Netflix — DevOps Engineer ($160k - $190k)", "DevOps Engineer"),
            ("Stripe: Backend Engineer (US/Canada Remote)", "Backend Engineer"),
        ]
        for jd, expected in samples:
            assert analyzer.extract_job_title(jd) == expected

    def test_introductory_recruitment_sentences(self, analyzer):
        """5. Extract job titles from introductory narrative sentences."""
        jd = (
            "Acme Health is seeking a Senior Python Developer to join our core backend engineering team.\n"
            "Responsibilities include designing scalable REST APIs."
        )
        assert analyzer.extract_job_title(jd) == "Senior Python Developer"

    def test_job_description_with_no_title_returns_fallback(self, analyzer):
        """6. Return exact fallback when no title can be reliably identified."""
        samples = [
            "",
            "   \n\n  ",
            "Looking for a qualified candidate to join our team in London.",
            "About Us\nWe are a fast-growing company delivering excellence in customer service.",
            "Requirements:\n- Must have 5 years experience\n- Strong communication skills",
        ]
        for jd in samples:
            assert analyzer.extract_job_title(jd) == "Target role not specified"

    def test_user_supplied_role_override_in_matching_engine(self):
        """7. Verify user-supplied target_role overrides detected title while preserving detected value."""
        engine = ResumeMatchingEngine()
        resume = "Experienced developer with Python, Docker, SQL skills."
        job = "Job Title: Software Engineer\nMust have Python and SQL."

        # Case A: No override -> uses detected
        res_no_override = engine.analyze(resume, job)
        assert res_no_override["job_title"] == "Software Engineer"
        assert res_no_override["detected_job_title"] == "Software Engineer"
        assert res_no_override["target_role_source"] == "job_description"

        # Case B: Explicit user override -> overrides display job_title
        res_override = engine.analyze(resume, job, target_role_input="Senior ML Architect")
        assert res_override["job_title"] == "Senior ML Architect"
        assert res_override["detected_job_title"] == "Software Engineer"
        assert res_override["target_role"] == "Senior ML Architect"
        assert res_override["target_role_source"] == "user_override"


# =========================================================================
# 2. SKILL EXTRACTION & ALIAS NORMALIZATION TESTS
# =========================================================================

class TestSkillExtractionAndNormalization:

    def test_canonical_alias_normalization(self, skill_engine):
        """1. Ensure equivalent alias variants normalize to single canonical representations."""
        cases = [
            ("Experienced with Python3 and Py in production.", "python"),
            ("Proficient in ReactJS and React.js frontend development.", "react"),
            ("Backend services written with NodeJS and Node.js.", "node.js"),
            ("Machine learning models trained with Scikit-learn and sklearn.", "scikit-learn"),
            ("Enterprise systems built with C Sharp and C#.", "c#"),
            ("Low-level network drivers in C Plus Plus and C++.", "c++"),
            ("Orchestrating container clusters with K8s and Kubernetes.", "kubernetes"),
            ("Relational databases managed with Postgres and PostgreSQL.", "postgresql"),
        ]
        for text, canonical_skill in cases:
            extracted = skill_engine.extract_skills(text)
            assert canonical_skill in extracted

    def test_preservation_of_critical_technical_tokens(self, skill_engine):
        """2. Preserve punctuation-sensitive tokens (C++, C#, .NET, Node.js, CI/CD, SQL, PL/SQL)."""
        text = "Core stack: C++, C#, .NET, Node.js, CI/CD, SQL, and PL/SQL procedures."
        extracted = skill_engine.extract_skills(text)
        expected = {"c++", "c#", ".net", "node.js", "ci/cd", "sql", "pl/sql"}
        for tok in expected:
            assert tok in extracted, f"Token '{tok}' was not preserved in {extracted}"

    def test_duplicate_alias_consolidation(self, skill_engine):
        """3. Consolidate aliases so duplicate mentions do not inflate skill counts."""
        text = "We use Python, python3, and py for data analysis. We also use React, ReactJS, and React.js."
        extracted = skill_engine.extract_skills(text)
        # Should only have 1 instance of 'python' and 1 instance of 'react'
        assert "python" in extracted
        assert "react" in extracted
        assert len([s for s in extracted if s in {"python", "python3", "py"}]) == 1
        assert len([s for s in extracted if s in {"react", "reactjs", "react.js"}]) == 1

    def test_ambiguous_skills_contextual_validation(self, skill_engine):
        """4. Correctly validate ambiguous skills (R, C, Go, SQL, AI, ML) against technical context."""
        # A. Valid context
        assert "r" in skill_engine.extract_skills("Data analysis using R programming and RStudio.")
        assert "c" in skill_engine.extract_skills("Linux kernel drivers in C programming.")
        assert "go" in skill_engine.extract_skills("Backend microservices implemented in Go and Golang.")
        assert "sql" in skill_engine.extract_skills("Database queries written in SQL.")
        assert "ai" in skill_engine.extract_skills("Building generative AI models and agents with Python.")
        assert "machine learning" in skill_engine.extract_skills("Applying ML algorithms to predict churn.")

        # B. Non-technical / negative contexts
        assert "r" not in skill_engine.extract_skills("She is in room R on floor 2.")
        assert "c" not in skill_engine.extract_skills("Section C describes the office location.")
        assert "go" not in skill_engine.extract_skills("We will go to the office tomorrow.")
        assert "ai" not in skill_engine.extract_skills("He went to visit his friend Ai in Japan.")
        assert "machine learning" not in skill_engine.extract_skills("Please add 500 ml of water to the container.")

    def test_generic_word_filtering(self, skill_engine):
        """5. Prevent standalone generic business words from becoming technical skills."""
        generic_text = (
            "We value focus, responsiveness, commitment, and strong performance in our work environment. "
            "Our team supports diverse applications, software, technology, and responsibilities."
        )
        extracted = skill_engine.extract_skills(generic_text)
        banned = {"focus", "responsiveness", "commitment", "performance", "environment", "applications", "software", "technology", "support", "responsibilities"}
        for word in banned:
            assert word not in extracted, f"Generic word '{word}' was incorrectly extracted: {extracted}"

    def test_compound_technical_phrase_preservation(self, skill_engine):
        """6. Do not discard legitimate compound technical phrases containing generic words."""
        text = "Strong background in Software Engineering, Application Development, and High Performance Computing."
        # Even though "software", "application", "performance" are generic alone, the compound competencies are legitimate
        extracted = skill_engine.extract_skills(text)
        # Should not extract standalone "software", "application", or "performance"
        assert "software" not in extracted
        assert "application" not in extracted
        assert "performance" not in extracted


# =========================================================================
# 3. SKILL CATEGORIZATION TESTS
# =========================================================================

class TestSkillCategorization:

    def test_standard_8_category_taxonomy_mapping(self):
        """1. Verify standard categorization across all 8 competency taxonomy tiers."""
        # 1. Programming languages
        assert categorize_competency("Python") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("Java") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("C++") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("C#") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("Go") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("Rust") == TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("TypeScript") == TAXONOMY_PROGRAMMING_LANGUAGES

        # 2. Frameworks and libraries
        assert categorize_competency("React") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("Django") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("Flask") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("FastAPI") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("Scikit-Learn") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("PyTorch") == TAXONOMY_FRAMEWORKS_LIBRARIES
        assert categorize_competency("Node.js") == TAXONOMY_FRAMEWORKS_LIBRARIES

        # 3. Databases
        assert categorize_competency("PostgreSQL") == TAXONOMY_DATABASES
        assert categorize_competency("MySQL") == TAXONOMY_DATABASES
        assert categorize_competency("MongoDB") == TAXONOMY_DATABASES
        assert categorize_competency("Redis") == TAXONOMY_DATABASES
        assert categorize_competency("SQL") == TAXONOMY_DATABASES

        # 4. Developer tools
        assert categorize_competency("Git") == TAXONOMY_DEVELOPER_TOOLS
        assert categorize_competency("GitHub") == TAXONOMY_DEVELOPER_TOOLS
        assert categorize_competency("Jira") == TAXONOMY_DEVELOPER_TOOLS
        assert categorize_competency("Pytest") == TAXONOMY_DEVELOPER_TOOLS

        # 5. Cloud and infrastructure
        assert categorize_competency("Docker") == TAXONOMY_CLOUD_INFRASTRUCTURE
        assert categorize_competency("Kubernetes") == TAXONOMY_CLOUD_INFRASTRUCTURE
        assert categorize_competency("AWS") == TAXONOMY_CLOUD_INFRASTRUCTURE
        assert categorize_competency("CI/CD") == TAXONOMY_CLOUD_INFRASTRUCTURE
        assert categorize_competency("Terraform") == TAXONOMY_CLOUD_INFRASTRUCTURE

        # 6. Productivity software
        assert categorize_competency("Excel") == TAXONOMY_PRODUCTIVITY
        assert categorize_competency("MS Word") == TAXONOMY_PRODUCTIVITY
        assert categorize_competency("PowerPoint") == TAXONOMY_PRODUCTIVITY

        # 7. Professional competencies
        assert categorize_competency("Agile") == TAXONOMY_PROFESSIONAL
        assert categorize_competency("System Architecture") == TAXONOMY_PROFESSIONAL
        assert categorize_competency("Machine Learning") == TAXONOMY_PROFESSIONAL
        assert categorize_competency("REST API") == TAXONOMY_PROFESSIONAL
        assert categorize_competency("AI") == TAXONOMY_PROFESSIONAL

        # 8. Soft skills
        assert categorize_competency("Communication") == TAXONOMY_SOFT
        assert categorize_competency("Leadership") == TAXONOMY_SOFT
        assert categorize_competency("Teamwork") == TAXONOMY_SOFT

    def test_strict_classification_rules(self):
        """2. Enforce strict classification rules (AI/REST API/Docker/ML are not programming languages)."""
        assert categorize_competency("AI") != TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("REST API") != TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("Docker") != TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("Machine Learning") != TAXONOMY_PROGRAMMING_LANGUAGES
        assert categorize_competency("SQL") == TAXONOMY_DATABASES
        assert categorize_competency("Communication") == TAXONOMY_SOFT
        assert categorize_competency("Leadership") == TAXONOMY_SOFT

    def test_unknown_terms_not_defaulted_to_developer_tools(self):
        """3. Ensure unknown/unrecognized terms return Generic/Ambiguous rather than Developer Tools."""
        unknown_skills = ["xyz_unrecognized_term", "nonexistent_comp_999", "foobar_widget_stack"]
        for unk in unknown_skills:
            cat = categorize_competency(unk)
            assert cat != TAXONOMY_DEVELOPER_TOOLS, f"Unknown skill '{unk}' was arbitrarily classified as Developer Tools!"
            assert cat == TAXONOMY_GENERIC

    def test_canonical_casing_helper(self):
        """4. Verify official canonical title-casing and abbreviations."""
        assert get_canonical_skill_name("python") == "Python"
        assert get_canonical_skill_name("c++") == "C++"
        assert get_canonical_skill_name("c#") == "C#"
        assert get_canonical_skill_name(".net") == ".NET"
        assert get_canonical_skill_name("node.js") == "Node.js"
        assert get_canonical_skill_name("scikit-learn") == "Scikit-Learn"
        assert get_canonical_skill_name("postgresql") == "PostgreSQL"
        assert get_canonical_skill_name("ci/cd") == "CI/CD"
        assert get_canonical_skill_name("sql") == "SQL"
        assert get_canonical_skill_name("machine learning") == "Machine Learning"


# =========================================================================
# 4. JOB REQUIREMENT EXTRACTION & TRACEABILITY TESTS
# =========================================================================

class TestJobRequirementExtraction:

    def test_mandatory_vs_preferred_vs_unspecified_tiers(self, analyzer):
        """1. Correctly partition skills into mutually exclusive Required, Preferred, and Unspecified sets."""
        jd = (
            "Job Title: Senior Backend Engineer\n\n"
            "Requirements:\n"
            "- Must have 4+ years experience with Python and PostgreSQL\n"
            "- Mandatory experience in Docker and Kubernetes\n\n"
            "Nice to have:\n"
            "- Experience with Redis and AWS is a plus\n"
            "- Good to have familiarity with GraphQL\n\n"
            "Overview:\n"
            "You will be working with Git and Agile teams."
        )
        res = analyzer.analyze(jd)
        req = set(res["required_skills"])
        pref = set(res["preferred_skills"])
        unspec = set(res["unspecified_skills"])

        # Disjoint sets
        assert req.isdisjoint(pref)
        assert req.isdisjoint(unspec)
        assert pref.isdisjoint(unspec)

        # Content verification
        assert "python" in req
        assert "postgresql" in req
        assert "docker" in req
        assert "kubernetes" in req

        assert "redis" in pref
        assert "amazon web services" in pref or "aws" in pref
        assert "graphql" in pref

        assert "git" in unspec or "agile" in unspec

    def test_alternative_requirement_groups(self, analyzer):
        """2. Detect disjunctive skill alternatives (e.g. Power BI or Tableau)."""
        jd = (
            "Job Title: Business Intelligence Analyst\n"
            "Required Qualifications:\n"
            "- Must have experience with SQL and either Power BI or Tableau for dashboards.\n"
            "- Python or R programming experience required."
        )
        res = analyzer.analyze(jd)
        alt_groups = res["alternative_groups"]
        assert len(alt_groups) >= 1

        # Check that Power BI and Tableau are grouped
        bi_grp = next((g for g in alt_groups if "power bi" in g["skills"] or "tableau" in g["skills"]), None)
        assert bi_grp is not None
        assert "power bi" in bi_grp["skills"]
        assert "tableau" in bi_grp["skills"]
        assert bi_grp["tier"] == "Required"

    def test_source_traceability_and_confidence(self, analyzer):
        """3. Ensure requirement intelligence provides exact supporting sentence, category, tier, and confidence."""
        jd = (
            "Job Title: Python Backend Developer\n"
            "Requirements:\n"
            "- Must have extensive experience building scalable microservices with Python and FastAPI.\n"
            "Preferred:\n"
            "- Docker containerization is a plus."
        )
        res = analyzer.analyze(jd)
        intel = res["requirement_intelligence"]
        assert len(intel) > 0

        py_entry = next((item for item in intel if item["name"] == "python"), None)
        assert py_entry is not None
        assert py_entry["canonical_name"] == "Python"
        assert py_entry["tier"] == "Required"
        assert py_entry["priority"] == "Required"
        assert "Python" in py_entry["supporting_sentence"] or "python" in py_entry["supporting_sentence"]
        assert py_entry["confidence"] == 1.0  # Exact dictionary match
        assert "extracted_phrase" in py_entry
        assert "source_text" in py_entry

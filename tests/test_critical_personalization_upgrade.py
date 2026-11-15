"""
Regression tests for Career Mentor Critical Personalization Upgrade.
Validates:
1. Distinct, domain-appropriate recommendations for every supported competency (no generic template repeating).
2. Elimination of generic 'Study core architectural principles of [skill] and build a tested prototype.'
3. Prohibition of irrelevant project forcing (e.g., 'Mood Mate' attached to Jira, Visio, Excel, Power BI, Focus, PC Skills).
4. Strict JD sentence retrieval with zero fabricated quotes ('Exact JD evidence unavailable.' fallback).
5. Correct canonical 4-category taxonomy classification.
6. Honest disclosure for unsupported competencies ('Specialized learning guidance is not yet available for this competency.').
7. Full reconciliation between category counts and prioritized gap card counts.
"""

import pytest
from src.mentor.mentor_engine import (
    CareerMentorEngine,
    classify_mentor_category,
    recommend_gap_action,
    find_related_candidate_experience,
    find_jd_sentence_for_skill,
)
from src.mentor.skill_curricula import get_curriculum_for_skill


class TestCriticalPersonalizationUpgrade:

    def test_no_repeated_generic_architectural_principles_template(self):
        """No skill should produce 'Study core architectural principles of ... and build a tested prototype.'"""
        skills_to_test = [
            "typescript", "project management", "focus", "visio", "jira",
            "power bi", "excel", "trello", "pc skills", "analytical problem-solving",
            "docker", "sql", "spark", "kubernetes", "aws", "react", "communication"
        ]
        sample_projects = [{"title": "Mood Mate", "technologies": ["Python", "Flask", "NLTK", "HTML", "CSS"]}]

        recommendations = {}
        for s in skills_to_test:
            cat = classify_mentor_category(s)
            rec = recommend_gap_action(s, cat, sample_projects)
            recommendations[s] = rec
            assert "Study core architectural principles" not in rec, f"Skill '{s}' emitted generic template: {rec}"
            assert len(rec) >= 25, f"Skill '{s}' recommendation is too brief: {rec}"

        # Verify distinctness: no two skills in this set should have the exact same recommendation
        unique_recs = set(recommendations.values())
        assert len(unique_recs) == len(skills_to_test), (
            f"Found duplicate recommendations among test skills! Only {len(unique_recs)} unique out of {len(skills_to_test)}"
        )

    def test_no_irrelevant_project_forcing_for_tools_and_soft_skills(self):
        """
        'Mood Mate' or backend projects must NEVER be forced into Jira, Power BI,
        Excel, Trello, Visio, Focus, or PC Skills evidence.
        """
        candidate_projects = [{"title": "Mood Mate", "technologies": ["Python", "Flask", "NLTK", "HTML", "CSS"]}]
        verified_skills = ["Python", "Flask", "NLTK", "HTML", "CSS", "Git", "Scikit-learn"]

        irrelevant_skills = [
            "jira", "power bi", "excel", "trello", "visio", "focus",
            "pc skills", "project management", "analytical problem-solving"
        ]

        for s in irrelevant_skills:
            rel = find_related_candidate_experience(s, verified_skills, candidate_projects)
            assert "Mood Mate" not in rel, f"Skill '{s}' forced project 'Mood Mate' into evidence: {rel}"
            assert "Can build upon engineering codebase developed in 'Mood Mate'" not in rel

    def test_relevant_project_association_allowed_when_stack_matches(self):
        """Related experience is only linked when candidate actually has relevant verified stack."""
        candidate_projects = [{"title": "Mood Mate", "technologies": ["Python", "Flask", "NLTK", "HTML", "CSS"]}]
        verified_skills = ["Python", "Flask", "NLTK", "HTML", "CSS", "Git"]

        # Docker is relevant to Flask backend
        docker_rel = find_related_candidate_experience("docker", verified_skills, candidate_projects)
        assert "Flask" in docker_rel or "backend" in docker_rel.lower() or "Mood Mate" in docker_rel

        # Communication can leverage presenting Mood Mate architecture
        comm_rel = find_related_candidate_experience("communication", verified_skills, candidate_projects)
        assert "Mood Mate" in comm_rel

    def test_strict_jd_evidence_retrieval_and_truthful_fallback(self):
        """JD sentence must be strictly from the JD or 'Exact JD evidence unavailable.'"""
        sample_jd = (
            "We are seeking a Full-Stack Engineer with strong TypeScript proficiency and experience with Docker containers. "
            "Experience with Jira backlog management is preferred. Must demonstrate strong analytical problem-solving skills."
        )

        ts_sent = find_jd_sentence_for_skill("typescript", sample_jd)
        assert "TypeScript proficiency" in ts_sent

        docker_sent = find_jd_sentence_for_skill("docker", sample_jd)
        assert "Docker containers" in docker_sent

        # Skill not in JD must strictly fallback to 'Exact JD evidence unavailable.'
        absent_sent = find_jd_sentence_for_skill("quantum computing", sample_jd)
        assert absent_sent == "Exact JD evidence unavailable."

        # Empty JD text must strictly fallback to 'Exact JD evidence unavailable.'
        empty_sent = find_jd_sentence_for_skill("typescript", "")
        assert empty_sent == "Exact JD evidence unavailable."

    def test_canonical_taxonomy_classification(self):
        """Verify proper classification into 4 canonical categories without fallthrough misclassification."""
        expected_mappings = {
            # Core Technical
            "typescript": "Core Technical Skills",
            "ts": "Core Technical Skills",
            "python": "Core Technical Skills",
            "sql": "Core Technical Skills",
            "react": "Core Technical Skills",
            "spark": "Core Technical Skills",
            "java": "Core Technical Skills",

            # Engineering Tools and Practices
            "docker": "Engineering Tools and Practices",
            "kubernetes": "Engineering Tools and Practices",
            "ci/cd": "Engineering Tools and Practices",
            "aws": "Engineering Tools and Practices",
            "git": "Engineering Tools and Practices",
            "linux": "Engineering Tools and Practices",

            # Productivity and Business Tools
            "jira": "Productivity and Business Tools",
            "trello": "Productivity and Business Tools",
            "excel": "Productivity and Business Tools",
            "power bi": "Productivity and Business Tools",
            "visio": "Productivity and Business Tools",
            "pc skills": "Productivity and Business Tools",

            # Professional and Behavioral Competencies
            "focus": "Professional and Behavioral Competencies",
            "project management": "Professional and Behavioral Competencies",
            "analytical problem-solving": "Professional and Behavioral Competencies",
            "communication": "Professional and Behavioral Competencies",
            "teamwork": "Professional and Behavioral Competencies",
            "leadership": "Professional and Behavioral Competencies",
        }

        for skill, expected_cat in expected_mappings.items():
            actual_cat = classify_mentor_category(skill)
            assert actual_cat == expected_cat, f"Skill '{skill}' expected '{expected_cat}' but got '{actual_cat}'"

    def test_honest_disclosure_for_unsupported_skills(self):
        """Unsupported skills must honestly report that specialized guidance is not yet available."""
        unsupported_skill = "ancient cobol vax"
        cat = classify_mentor_category(unsupported_skill)
        rec = recommend_gap_action(unsupported_skill, cat, [])
        assert "Specialized learning guidance is not yet available" in rec

        curr = get_curriculum_for_skill(unsupported_skill)
        assert curr.get("is_verified_specialized") is not True

    def test_full_dossier_category_reconciliation_and_counts(self):
        """
        Verify that in a realistic analysis containing the 19 skills:
        1. All 19 skills have valid categories.
        2. Category counts match card totals exactly and are non-zero for populated categories.
        3. Every card has practical_deliverable and curriculum_source.
        """
        nineteen_skills = [
            "TypeScript", "Project Management", "Focus", "Visio", "Jira",
            "Power BI", "Excel", "Trello", "Communication", "PC Skills",
            "Analytical Problem-Solving", "Docker", "SQL", "Spark", "Python",
            "Kubernetes", "CI/CD", "AWS", "React"
        ]

        mock_jd = (
            "Looking for an engineer proficient in TypeScript, Python, React, SQL, and Spark. "
            "Experience with Docker, Kubernetes, CI/CD pipelines, and AWS is required. "
            "You will use Jira and Trello for sprint management, and Visio, Excel, and Power BI for reporting. "
            "Basic PC skills, strong Project Management, Focus, Analytical Problem-Solving, and Communication are essential."
        )

        analysis_mock = {
            "missing_required_skills": nineteen_skills[:12],
            "missing_preferred_skills": nineteen_skills[12:],
            "resume_skills": ["Python", "Flask", "NLTK", "HTML", "CSS", "Git"],
            "matched_skills": ["Python"],
            "projects": [{"title": "Mood Mate", "technologies": ["Python", "Flask", "NLTK"]}],
            "raw_text": "Harsha Vardhan\nSoftware Engineer\nMood Mate Project",
            "job_description_text": mock_jd,
            "raw_jd": mock_jd
        }

        engine = CareerMentorEngine(analysis_mock)
        dossier = engine.build_mentor_dossier()

        gaps = dossier["gaps"]
        assert gaps["total_gaps_count"] == 19
        assert len(gaps["prioritized_gaps"]) == 19
        assert len(gaps["top_priorities"]) == 5
        assert len(gaps["expandable_requirements"]) == 14

        categories = gaps["categories"]
        # Verify title-case keys exist and are non-zero
        core_tech = categories["Core Technical Skills"]
        eng_tools = categories["Engineering Tools and Practices"]
        prof_behav = categories["Professional and Behavioral Competencies"]
        prod_tools = categories["Productivity and Business Tools"]

        assert len(core_tech) > 0, "Core Technical category count must not be 0"
        assert len(eng_tools) > 0, "Engineering Tools category count must not be 0"
        assert len(prof_behav) > 0, "Professional category count must not be 0"
        assert len(prod_tools) > 0, "Productivity category count must not be 0"

        # Reconciliation: sum of category lengths must equal 19
        total_in_categories = len(core_tech) + len(eng_tools) + len(prof_behav) + len(prod_tools)
        assert total_in_categories == 19, f"Category sum ({total_in_categories}) does not equal 19!"

        # Verify every prioritized gap card has practical_deliverable and curriculum_source
        for gap in gaps["prioritized_gaps"]:
            assert gap.get("practical_deliverable"), f"Missing practical_deliverable for {gap['skill_name']}"
            assert gap.get("curriculum_source"), f"Missing curriculum_source for {gap['skill_name']}"
            assert gap.get("recommended_action"), f"Missing recommended_action for {gap['skill_name']}"
            assert "Study core architectural principles of" not in gap["recommended_action"]
            assert gap["jd_sentence"] != "Referenced under technical requirements for target position."

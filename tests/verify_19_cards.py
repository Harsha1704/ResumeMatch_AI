"""
Renders and prints the exact 19 gap cards through CareerMentorEngine and Jinja template.
"""
import json
from src.mentor.mentor_engine import CareerMentorEngine

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
print(f"Total Gaps: {gaps['total_gaps_count']}")
print("Category Counts:")
for cat_name, items in gaps["categories"].items():
    if not cat_name.startswith("core_") and not cat_name.startswith("engineering_") and not cat_name.startswith("prof_") and not cat_name.startswith("prod_"):
        print(f"  - {cat_name}: {len(items)}")

print("\n" + "="*80)
print("19 SKILL GAP CARDS VERIFICATION")
print("="*80)

for idx, gap in enumerate(gaps["prioritized_gaps"], 1):
    print(f"\n--- Card {idx}: {gap['skill_name']} ---")
    print(f"Category:             {gap['category']}")
    print(f"Priority Tier:        {gap['priority_tier']} ({gap['priority']})")
    print(f"Actual JD Evidence:   {gap['jd_sentence']}")
    print(f"Related Candidate:    {gap['related_experience']}")
    print(f"Recommendation:       {gap['recommended_action']}")
    print(f"Practical Deliverable:{gap['practical_deliverable']}")
    print(f"Curriculum Source:    {gap['curriculum_source']}")

"""
Deterministic Skill Gap Analysis Engine.
Categorizes skills into:
- Fully Matched Mandatory Skills
- Partially Evidenced Mandatory Skills
- Missing Mandatory Skills (High Priority Gaps)
- Missing Preferred Skills (Secondary Gaps)
- Matched Preferred and Unspecified Skills
Enforces the fundamental partition identity:
fully_matched_required + partially_evidenced_required + missing_required = total_required
Zero LLM reliance. Fully deterministic.
"""

from typing import Dict, List, Optional, Set, Tuple, Union
import re
from src.preprocessing.text_cleaner import clean_text
from src.preprocessing.skill_extractor import SkillEngine, categorize_competency


class SkillGapAnalyzer:
    """
    Analyzes skill overlap, missing competencies, partial evidence, and coverage ratios.
    Enforces strict mathematical consistency across all skill accounting.
    """

    def __init__(self):
        self.skill_engine = SkillEngine()

    def detect_partially_evidenced_skills(
        self,
        resume_raw: str,
        matched_skills: Set[str]
    ) -> Tuple[Set[str], Set[str]]:
        """
        Differentiates well-evidenced skills from partially evidenced skills.
        A skill is 'partially evidenced' if it is mentioned only in a static skills list
        or isolated keyword block without being supported by action verbs, metrics,
        or contextual descriptions in project/experience sections.

        Returns:
            (solidly_evidenced_skills, partially_evidenced_skills)
        """
        if not resume_raw or not matched_skills:
            return set(), set()

        evidence_verbs = {
            "developed", "built", "implemented", "designed", "architected",
            "deployed", "optimized", "engineered", "maintained", "created",
            "managed", "integrated", "automated", "trained", "delivered",
            "spearheaded", "analyzed", "configured", "refactored", "tested",
            "programmed", "coded", "led", "supervised", "collaborated"
        }

        # Check line-by-line and sentence-by-sentence
        sentences = [s.strip() for s in re.split(r"[.\n;]", resume_raw.lower()) if s.strip()]

        solid_skills: Set[str] = set()
        partial_skills: Set[str] = set()

        for skill in matched_skills:
            skill_lower = skill.lower()
            escaped = re.escape(skill_lower)
            pat = re.compile(rf"(?<![\w#+.]){escaped}(?![\w#+.])", re.IGNORECASE)

            has_local_action = False
            for sentence in sentences:
                if pat.search(sentence):
                    words = set(re.findall(r"\b[a-z]{3,}\b", sentence))
                    is_pure_skills_list = (
                        any(h in sentence for h in ["skills:", "skills", "technologies:", "proficient in", "knowledge of"])
                        and not words.intersection(evidence_verbs)
                    )
                    if not is_pure_skills_list and (words.intersection(evidence_verbs) or any(c.isdigit() for c in sentence) or len(words) >= 7):
                        has_local_action = True
                        break

            if has_local_action:
                solid_skills.add(skill)
            else:
                partial_skills.add(skill)

        return solid_skills, partial_skills

    def prioritize_skill_gaps(
        self,
        missing_required: List[str],
        missing_preferred: List[str],
        job_raw: str
    ) -> List[Dict]:
        """
        Prioritizes skill gaps deterministically based on:
        1. Requirement severity (Required = High Priority, Preferred = Medium Priority)
        2. Exact token frequency of occurrence in the target job description (word-boundary safe)
        """
        prioritized = []
        job_lower = job_raw.lower()

        def count_skill_occurrences(sk: str) -> int:
            clean_sk = re.escape(sk.lower())
            pat = re.compile(rf"(?<![\w#+.]){clean_sk}(?![\w#+.])", re.IGNORECASE)
            return len(pat.findall(job_lower))

        # 1. Required skills (High Priority)
        for skill in missing_required:
            count = count_skill_occurrences(skill)
            priority_level = "High Priority" if count >= 2 else "High Priority (Core)"
            prioritized.append({
                "skill": skill,
                "type": "Required",
                "priority": priority_level,
                "frequency_in_job": max(1, count),
                "competency_type": categorize_competency(skill),
                "reason": "Explicitly required qualification for this role."
            })

        # 2. Preferred skills (Medium Priority)
        for skill in missing_preferred:
            count = count_skill_occurrences(skill)
            prioritized.append({
                "skill": skill,
                "type": "Preferred",
                "priority": "Medium Priority",
                "frequency_in_job": max(1, count),
                "competency_type": categorize_competency(skill),
                "reason": "Preferred qualification; strengthens candidacy if demonstrated."
            })

        def sort_key(item):
            type_weight = 0 if item["type"] == "Required" else 1
            return (type_weight, -item["frequency_in_job"], item["skill"])

        return sorted(prioritized, key=sort_key)

    def analyze_gap(
        self,
        resume_text: Optional[str],
        job_analysis: Dict,
        job_raw_text: Optional[str] = None
    ) -> Dict:
        """
        Executes unified, mathematically consistent skill gap analysis.
        Enforces:
        fully_matched_required + partially_evidenced_required + missing_required == total_required
        """
        required_skills: Set[str] = set(job_analysis.get("required_skills", []))
        preferred_skills: Set[str] = set(job_analysis.get("preferred_skills", []))
        unspecified_skills: Set[str] = set(job_analysis.get("unspecified_skills", []))

        # Disjointness guarantee
        preferred_skills = preferred_skills - required_skills
        unspecified_skills = unspecified_skills - required_skills - preferred_skills

        # If job analyzer didn't detect any tiers, use all_skills as required
        if not required_skills and not preferred_skills:
            required_skills = set(job_analysis.get("all_skills", []))

        total_req = len(required_skills)

        if not resume_text or not isinstance(resume_text, str) or not resume_text.strip():
            return {
                "matched_skills": [],
                "matched_required_skills": [],
                "fully_matched_required_skills": [],
                "partially_evidenced_required_skills": [],
                "missing_required_skills": sorted(list(required_skills)),
                "matched_preferred_skills": [],
                "missing_preferred_skills": sorted(list(preferred_skills)),
                "matched_unspecified_skills": [],
                "solidly_evidenced_skills": [],
                "partially_evidenced_skills": [],
                "resume_skills": [],
                "total_required_count": total_req,
                "fully_matched_required_count": 0,
                "partially_evidenced_required_count": 0,
                "matched_required_count": 0,
                "missing_required_count": total_req,
                "total_preferred_count": len(preferred_skills),
                "matched_preferred_count": 0,
                "missing_preferred_count": len(preferred_skills),
                "full_coverage_pct": 0.0,
                "any_coverage_pct": 0.0,
                "full_coverage_display": "0.0%" if total_req > 0 else "Not Available",
                "any_coverage_display": "0.0%" if total_req > 0 else "Not Available",
                "skill_coverage_pct": 0.0,
                "fully_matched_coverage_pct": 0.0,
                "skill_evidence_coverage_pct": 0.0,
                "skill_coverage_display": "0.0%" if total_req > 0 else "Not Available",
                "prioritized_gaps": self.prioritize_skill_gaps(sorted(list(required_skills)), sorted(list(preferred_skills)), job_raw_text or ""),
                "status": "empty_resume"
            }

        resume_skills: Set[str] = self.skill_engine.extract_skills(resume_text)

        # 0. Process alternative requirement groups (e.g. "Power BI or Tableau", "Java or Python")
        alt_groups = job_analysis.get("alternative_groups", [])
        satisfied_alternatives = []
        for ag in alt_groups:
            ag_skills = set(ag.get("skills", []))
            ag_tier = ag.get("tier", "Required")

            matched_alts = resume_skills.intersection(ag_skills)
            if matched_alts:
                satisfied_skill = sorted(list(matched_alts))[0]
                unneeded_alts = ag_skills - {satisfied_skill}
                if ag_tier == "Required":
                    required_skills = required_skills - unneeded_alts
                else:
                    preferred_skills = preferred_skills - unneeded_alts
                satisfied_alternatives.append({
                    "group": ag.get("canonical_skills", list(ag_skills)),
                    "satisfied_by": satisfied_skill,
                    "omitted_alternatives": list(unneeded_alts),
                    "tier": ag_tier,
                    "sentence": ag.get("sentence", "")
                })
            else:
                if len(ag_skills) > 1:
                    primary_rep = sorted(list(ag_skills))[0]
                    unneeded_reps = ag_skills - {primary_rep}
                    if ag_tier == "Required":
                        required_skills = required_skills - unneeded_reps
                    else:
                        preferred_skills = preferred_skills - unneeded_reps

        # 1. Mandatory / Required calculations
        matched_required: Set[str] = resume_skills.intersection(required_skills)
        missing_required: Set[str] = required_skills - resume_skills

        # Differentiate solid vs partial evidence within matched_required
        solid_required, partial_required = self.detect_partially_evidenced_skills(resume_text, matched_required)

        # Mathematical partition validation:
        total_required = len(required_skills)
        n_solid_req = len(solid_required)
        n_partial_req = len(partial_required)
        n_missing_req = len(missing_required)
        assert n_solid_req + n_partial_req + n_missing_req == total_required, (
            f"Accounting violation: {n_solid_req} + {n_partial_req} + {n_missing_req} != {total_required}"
        )

        # 2. Preferred calculations
        matched_preferred: Set[str] = resume_skills.intersection(preferred_skills)
        missing_preferred: Set[str] = preferred_skills - resume_skills
        total_preferred = len(preferred_skills)

        # 3. Unspecified calculations
        matched_unspecified: Set[str] = resume_skills.intersection(unspecified_skills)

        # Overall matched skills (all tiers combined)
        matched_all = matched_required.union(matched_preferred).union(matched_unspecified)

        # Two clearly separated coverage metrics:
        # Full Coverage = Fully Evidenced Required Skills / Total Required Skills
        # Any-Evidence Coverage = (Fully + Partially Evidenced Required Skills) / Total Required Skills
        if total_required > 0:
            full_coverage_pct = round((n_solid_req / total_required) * 100.0, 1)
            any_coverage_pct = round((len(matched_required) / total_required) * 100.0, 1)
            full_coverage_display = f"{full_coverage_pct}%"
            any_coverage_display = f"{any_coverage_pct}%"
        else:
            full_coverage_pct = 0.0
            any_coverage_pct = 0.0
            full_coverage_display = "Not Available"
            any_coverage_display = "Not Available"

        # The primary coverage gauge uses full coverage
        coverage_pct = full_coverage_pct
        coverage_display = full_coverage_display

        # Prioritized gaps
        job_raw = job_raw_text or "\n".join(job_analysis.get("all_skills", []))
        prioritized_gaps = self.prioritize_skill_gaps(
            sorted(list(missing_required)),
            sorted(list(missing_preferred)),
            job_raw
        )

        # Detect all partially evidenced skills across all matched
        solid_all, partial_all = self.detect_partially_evidenced_skills(resume_text, matched_all)

        return {
            "resume_skills": sorted(list(resume_skills)),
            "matched_skills": sorted(list(matched_all)),
            "matched_required_skills": sorted(list(matched_required)),
            "fully_matched_required_skills": sorted(list(solid_required)),
            "partially_evidenced_required_skills": sorted(list(partial_required)),
            "missing_required_skills": sorted(list(missing_required)),
            "matched_preferred_skills": sorted(list(matched_preferred)),
            "missing_preferred_skills": sorted(list(missing_preferred)),
            "matched_unspecified_skills": sorted(list(matched_unspecified)),
            "solidly_evidenced_skills": sorted(list(solid_all)),
            "partially_evidenced_skills": sorted(list(partial_all)),
            "total_required_count": total_required,
            "fully_matched_required_count": n_solid_req,
            "partially_evidenced_required_count": n_partial_req,
            "matched_required_count": len(matched_required),
            "missing_required_count": n_missing_req,
            "total_preferred_count": total_preferred,
            "matched_preferred_count": len(matched_preferred),
            "missing_preferred_count": len(missing_preferred),
            "total_resume_skills_count": len(resume_skills),
            "full_coverage_pct": full_coverage_pct,
            "any_coverage_pct": any_coverage_pct,
            "full_coverage_display": full_coverage_display,
            "any_coverage_display": any_coverage_display,
            "skill_coverage_pct": any_coverage_pct,
            "fully_matched_coverage_pct": full_coverage_pct,
            "skill_evidence_coverage_pct": any_coverage_pct,
            "skill_coverage_display": full_coverage_display,
            "prioritized_gaps": prioritized_gaps,
            "satisfied_alternatives": satisfied_alternatives,
            "effective_required_skills": sorted(list(required_skills)),
            "effective_preferred_skills": sorted(list(preferred_skills)),
            "status": "success"
        }

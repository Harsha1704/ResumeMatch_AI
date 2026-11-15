"""
Deterministic Motivational & Guidance Message Templates Module.
Generates personalized, respectful, and supportive career coaching messages.
Enforces strict rules:
- Strictly never promises or guarantees job offers, interview selection, or employment.
- Avoids negative absolutes like "You do not know X"; uses "Your resume does not clearly demonstrate X."
- Encourages proactive hands-on preparation grounded in candidate's existing strengths.
"""

from typing import Dict, List, Any, Optional


def build_welcome_greeting(preferred_name: str, target_role: str, verified_skills_count: int, gap_count: int) -> str:
    """
    Constructs personalized, encouraging welcome greeting.
    """
    name_str = preferred_name if preferred_name and preferred_name != "Candidate" else "there"
    
    msg = (
        f"Hey {name_str}! I've analyzed your resume and the target {target_role} job description. "
        f"You have already demonstrated {verified_skills_count} relevant technical competencies in your profile. "
    )
    if gap_count > 0:
        msg += (
            f"However, {gap_count} required or preferred skills are not yet clearly evidenced. "
            "Let's build a practical, step-by-step preparation roadmap together to strengthen your technical readiness."
        )
    else:
        msg += (
            "Your profile shows strong alignment with the job requirements! "
            "Let's practice interview scenarios and refine your architecture explanations."
        )
    return msg


def format_gap_explanation(
    skill_name: str,
    priority_tier: str,
    existing_skills: List[str],
    preferred_name: Optional[str] = None
) -> str:
    """
    Constructs deterministic, respectful explanation of why a skill gap matters
    and how existing candidate knowledge bridges the learning curve.
    Enforces Requirement B8: Personalized, encouraging guidance referencing verified strengths.
    """
    bridge_skill = None
    skill_lower = skill_name.lower()
    for s in existing_skills:
        s_lower = s.lower()
        if "sql" in skill_lower and ("python" in s_lower or "database" in s_lower or "django" in s_lower or "pandas" in s_lower):
            bridge_skill = s
            break
        elif "docker" in skill_lower and ("linux" in s_lower or "flask" in s_lower or "python" in s_lower):
            bridge_skill = s
            break
        elif "kubernetes" in skill_lower and ("docker" in s_lower or "microservice" in s_lower or "cloud" in s_lower):
            bridge_skill = s
            break
        elif "aws" in skill_lower and ("linux" in s_lower or "docker" in s_lower or "python" in s_lower or "cloud" in s_lower):
            bridge_skill = s
            break
        elif "fastapi" in skill_lower and ("flask" in s_lower or "python" in s_lower):
            bridge_skill = s
            break
        elif "react" in skill_lower and ("javascript" in s_lower or "html" in s_lower or "frontend" in s_lower):
            bridge_skill = s
            break
        elif "ci/cd" in skill_lower and ("git" in s_lower or "github" in s_lower or "linux" in s_lower):
            bridge_skill = s
            break

    name_prefix = f"{preferred_name}, your" if (preferred_name and preferred_name != "Candidate") else "Your"
    verified_summary = ", ".join(existing_skills[:3]) if existing_skills else "software engineering fundamentals"

    explanation = f"Your resume does not clearly demonstrate {skill_name}, which is categorized as a {priority_tier} requirement for this position. "
    if preferred_name and preferred_name != "Candidate":
        explanation = f"{preferred_name}, your resume does not clearly demonstrate {skill_name}, which is categorized as a {priority_tier} requirement for this position. "

    if bridge_skill:
        explanation += (
            f"While your profile demonstrates verified {bridge_skill} experience, "
            f"you can leverage those foundational concepts to ramp up on {skill_name} much more rapidly. "
            f"Focus on core {skill_name} architecture, hands-on implementations, and test verification."
        )
    else:
        explanation += (
            f"While your profile demonstrates {verified_summary} experience, "
            f"building demonstrable evidence in {skill_name} through hands-on code exercises and practical projects "
            f"will help you discuss real-world implementations confidently during technical interviews."
        )
    return explanation


def build_progress_encouragement(completed_tasks: int, total_tasks: int) -> str:
    """
    Generates milestone progress encouragement without false guarantees.
    """
    if completed_tasks == 0:
        return "Begin by reviewing the foundational documentation for your highest-priority skill gap."
    elif completed_tasks < total_tasks:
        return (
            f"Great momentum! You have completed {completed_tasks} of {total_tasks} preparation milestones. "
            "Continue working through the practical coding exercises and interview practice questions."
        )
    else:
        return (
            f"Outstanding dedication! You have completed all {total_tasks} milestones in this study plan. "
            "These steps will help you articulate your engineering trade-offs clearly and interview with confidence."
        )

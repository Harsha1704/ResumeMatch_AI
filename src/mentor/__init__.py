"""
Personalized Career Mentor package.
Provides deterministic, resume-aware guidance, skill-specific roadmaps,
learning resource integration, and preparation progress tracking.
"""

from .name_extractor import extract_candidate_name, format_mentor_identity
from .resource_mapper import get_learning_resources_for_skill, VERIFIED_RESOURCE_REGISTRY
from .project_recommender import recommend_project_for_skill, CURATED_PROJECT_TEMPLATES
from .roadmap_generator import generate_skill_roadmap, generate_realistic_study_plan
from .progress_tracker import CandidateProgressTracker, VALID_STATUSES
from .message_templates import build_welcome_greeting, format_gap_explanation, build_progress_encouragement
from .mentor_engine import CareerMentorEngine
from .skill_curricula import (
    DOMAIN_ROADMAP_FAMILIES,
    SKILL_SPECIFIC_CURRICULA,
    get_domain_for_skill,
    get_curriculum_for_skill,
    build_skill_action_plan
)

__all__ = [
    "extract_candidate_name",
    "format_mentor_identity",
    "get_learning_resources_for_skill",
    "VERIFIED_RESOURCE_REGISTRY",
    "recommend_project_for_skill",
    "CURATED_PROJECT_TEMPLATES",
    "generate_skill_roadmap",
    "generate_realistic_study_plan",
    "CandidateProgressTracker",
    "VALID_STATUSES",
    "build_welcome_greeting",
    "format_gap_explanation",
    "build_progress_encouragement",
    "CareerMentorEngine",
    "DOMAIN_ROADMAP_FAMILIES",
    "SKILL_SPECIFIC_CURRICULA",
    "get_domain_for_skill",
    "get_curriculum_for_skill",
    "build_skill_action_plan",
]

"""
Interview Question Difficulty Engine.
Handles deterministic difficulty classification, filtering, and distribution balancing.
Supported levels: Easy, Medium, Hard.
"""

from typing import List, Dict, Any, Optional

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

# Keywords indicating question depth and conceptual difficulty
HARD_KEYWORDS = [
    "gil", "deadlock", "memory leak", "virtual memory", "concurrency",
    "distributed", "architecture", "tradeoff", "trade-off", "scalability",
    "worst-case", "bottleneck", "optimization", "acid", "mvcc", "internals"
]

EASY_KEYWORDS = [
    "what is", "difference between", "tell me about yourself", "strengths",
    "overview", "basic", "define", "primary purpose"
]


def classify_question_difficulty(question_text: str, topic: Optional[str] = None) -> str:
    """
    Deterministically evaluates question text complexity based on terminology,
    depth of technical reasoning required, and topic attributes.
    """
    text_lower = question_text.lower()
    
    # Check for hard/architectural keywords
    for kw in HARD_KEYWORDS:
        if kw in text_lower:
            return "Hard"
            
    # Check for basic definition keywords
    for kw in EASY_KEYWORDS:
        if kw in text_lower:
            return "Easy"
            
    # Default middle-tier engineering depth
    return "Medium"


def filter_by_difficulty(
    questions: List[Dict[str, Any]],
    target_difficulty: str = "All",
    max_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Filters or balances a list of questions according to user difficulty preference.
    If target_difficulty is 'All', produces an interleaved, balanced portfolio across:
    Easy, Medium, and Hard.
    """
    if not questions:
        return []

    norm_target = target_difficulty.capitalize().strip() if target_difficulty else "All"

    if norm_target in DIFFICULTY_LEVELS:
        filtered = [q for q in questions if q.get("difficulty", "Medium").capitalize() == norm_target]
        if max_count and len(filtered) > max_count:
            return filtered[:max_count]
        return filtered

    # When 'All' is selected, separate pools by difficulty
    easy_pool = [q for q in questions if q.get("difficulty") == "Easy"]
    med_pool = [q for q in questions if q.get("difficulty") == "Medium"]
    hard_pool = [q for q in questions if q.get("difficulty") == "Hard"]

    # Interweave in a balanced ratio (Medium, Easy, Medium, Hard...)
    interleaved = []
    e_i, m_i, h_i = 0, 0, 0
    total_items = len(easy_pool) + len(med_pool) + len(hard_pool)

    while len(interleaved) < total_items:
        added = False
        if m_i < len(med_pool):
            interleaved.append(med_pool[m_i])
            m_i += 1
            added = True
        if e_i < len(easy_pool):
            interleaved.append(easy_pool[e_i])
            e_i += 1
            added = True
        if m_i < len(med_pool):
            interleaved.append(med_pool[m_i])
            m_i += 1
            added = True
        if h_i < len(hard_pool):
            interleaved.append(hard_pool[h_i])
            h_i += 1
            added = True
        if not added:
            break

    if max_count:
        return interleaved[:max_count]
    return interleaved

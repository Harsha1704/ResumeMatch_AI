"""
Transparent Deterministic Heuristic Answer Evaluator Module.
Provides rule-based, explainable feedback on user interview practice answers.
Evaluates:
- Coverage of expected technical key points and important concepts
- Adherence to recommended answer frameworks (STAR, PAR, PREP, etc.)
- Technical entity and concept density
- Answer completeness and depth (word counts, structure)
- Grounded evidence references (mentioning project, tools, or metrics)
- Excessive repetition or n-gram redundancy

Explicitly labeled: "Heuristic Answer Feedback".
Does NOT claim to measure true human interview success probabilities.
"""

import re
from typing import Dict, List, Any, Optional
from collections import Counter

from .answer_frameworks import get_framework


class HeuristicAnswerEvaluator:
    """
    Deterministic rule-based answer evaluator for interview practice.
    """

    LABEL = "Heuristic Answer Feedback"
    DISCLAIMER = (
        "This feedback is automated, rule-based, and Heuristic. It is designed for self-guided "
        "practice and coaching, and does not represent an accredited or predictive human interview score."
    )

    def evaluate_answer(
        self,
        question_data: Dict[str, Any],
        user_answer: str,
        framework_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate's practice answer against question expectations and framework structure.
        """
        text = user_answer.strip() if user_answer else ""
        words = text.split()
        word_count = len(words)
        fw_id = framework_id or question_data.get("recommended_answer_framework", "STAR")
        fw = get_framework(fw_id)

        # 1. Answer Completeness & Word Count
        if word_count == 0:
            return {
                "evaluator_label": self.LABEL,
                "disclaimer": self.DISCLAIMER,
                "word_count": 0,
                "status": "empty",
                "completeness_level": "No Answer Provided",
                "framework_adherence": {
                    "framework": fw["name"],
                    "framework_id": fw_id,
                    "sections_addressed": [],
                    "sections_missing": [s["key"] for s in fw["steps"]],
                    "adherence_pct": 0.0
                },
                "key_point_coverage": {
                    "covered": [],
                    "missing": question_data.get("expected_key_points", []),
                    "coverage_pct": 0.0
                },
                "important_concepts_coverage": {
                    "covered": [],
                    "missing": question_data.get("important_concepts", []),
                    "coverage_pct": 0.0
                },
                "evidence_detected": False,
                "strengths": [],
                "areas_for_improvement": ["Please enter your answer to receive heuristic feedback."],
                "actionable_feedback": "No answer was submitted. Use the recommended framework steps to outline your response."
            }

        # 2. Key Point Coverage
        expected_points = question_data.get("expected_key_points", [])
        covered_points = []
        missing_points = []
        text_lower = text.lower()

        def _clean_stem(w: str) -> str:
            w = w.lower()
            for suffix in ["ing", "tion", "ed", "ies", "es", "s"]:
                if len(w) > len(suffix) + 3 and w.endswith(suffix):
                    return w[:-len(suffix)]
            return w

        for pt in expected_points:
            tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_\#\+\-]{3,}\b", pt)
                      if t.lower() not in {"this", "that", "with", "from", "have", "were", "what", "where", "when", "using", "your", "overview"}]
            matches = [t for t in tokens if t in text_lower or _clean_stem(t) in text_lower]
            if len(matches) >= 1:
                covered_points.append(pt)
            else:
                missing_points.append(pt)

        coverage_pct = round((len(covered_points) / max(1, len(expected_points))) * 100, 1)

        # 3. Important Concepts Coverage
        important_concepts = question_data.get("important_concepts", [])
        covered_concepts = []
        missing_concepts = []
        for concept in important_concepts:
            c_clean = concept.lower()
            # Direct match or token match
            if c_clean in text_lower or any(part in text_lower for part in c_clean.split() if len(part) >= 4):
                covered_concepts.append(concept)
            else:
                missing_concepts.append(concept)
        concept_coverage_pct = round((len(covered_concepts) / max(1, len(important_concepts))) * 100, 1) if important_concepts else 100.0

        # 4. Framework Section Adherence
        sections_addressed = []
        sections_missing = []

        for step in fw["steps"]:
            key = step["key"].lower()
            pattern = rf"(?i)\b({re.escape(key)}|step\s*\d+|part\s*\d+)\b"
            has_marker = bool(re.search(pattern, text))

            # Semantic cues based on section type
            if key in ["situation", "context"]:
                cues = ["when i", "during my", "at the time", "project background", "we were working on", "in college"]
            elif key in ["task", "objective", "problem", "challenge", "obstacles"]:
                cues = ["the goal was", "responsible for", "the problem was", "challenge was", "bottleneck", "needed to"]
            elif key in ["action", "actions", "how"]:
                cues = ["i implemented", "i built", "i developed", "we used", "i analyzed", "i resolved", "i chose"]
            elif key in ["result", "results"]:
                cues = ["resulted in", "achieved", "reduced", "improved", "delivered", "outcome", "successfully", "accuracy of"]
            elif key in ["learning", "why"]:
                cues = ["i learned", "key takeaway", "in the future", "what i gained", "lesson", "why it matters"]
            elif key in ["point"]:
                cues = ["my perspective", "i believe", "firstly", "in my view", "the reason", "i specialize in"]
            elif key in ["evidence"]:
                cues = ["for example", "specifically", "evidence shows", "benchmark", "data indicates"]
            elif key in ["explanation"]:
                cues = ["because", "this is because", "due to", "trade-off", "this allows"]
            elif key in ["link"]:
                cues = ["therefore", "in conclusion", "this connects to", "which aligns with"]
            else:
                cues = ["specifically", "because"]

            has_cues = any(c in text_lower for c in cues)

            if has_marker or has_cues:
                sections_addressed.append(step["key"])
            else:
                sections_missing.append(step["key"])

        # 5. Evidence References Check
        has_metrics = bool(re.search(r"\b(\d+[\.\d]*%|\d+\s*(?:ms|seconds|users|queries|gb|mb|records|rows))\b", text_lower))
        has_named_entities = bool(re.search(r"\b(python|java|c\+\+|sql|docker|pytorch|flask|fastapi|kubernetes|aws|git|linux|react)\b", text_lower))
        evidence_detected = has_metrics or has_named_entities

        # 6. Repetition & N-Gram Redundancy Check
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]
        sentence_counts = Counter(sentences)
        has_duplicate_sentences = any(count > 1 for count in sentence_counts.values())

        # 7. Assemble Strengths and Areas for Improvement
        strengths = []
        improvements = []

        if word_count >= 80:
            strengths.append(f"Good response length ({word_count} words), allowing adequate technical depth.")
        elif word_count < 35:
            improvements.append(f"Answer is concise ({word_count} words). Aim for 60-150 words to provide substantive engineering context.")

        if coverage_pct >= 60.0:
            strengths.append(f"Strong concept coverage: addressed {len(covered_points)} of {len(expected_points)} expected key points ({coverage_pct}%).")
        else:
            improvements.append(f"Consider addressing additional key points: {', '.join(missing_points[:2]) if missing_points else 'add more technical details'}.")

        if covered_concepts:
            strengths.append(f"Included core technical concepts: {', '.join(covered_concepts[:3])}.")

        if missing_concepts:
            improvements.append(f"Missing key concepts: {', '.join(missing_concepts[:3])}.")

        if not sections_missing:
            strengths.append(f"Excellent adherence to {fw['name']}: all {len(fw['steps'])} framework sections ({', '.join(sections_addressed)}) were addressed.")
        else:
            improvements.append(f"Your {fw['name']} response is missing clear coverage of: {', '.join(sections_missing)}.")

        if evidence_detected:
            strengths.append("Contains concrete technical evidence (tool names, metrics, or architecture mentions).")
        else:
            improvements.append("Ground your answer with specific tools, benchmarks, or quantifiable outcomes from your resume.")

        if has_duplicate_sentences:
            improvements.append("Detected redundant or repeated sentences. Keep the narrative progression crisp and direct.")

        # Summary Actionable Feedback String
        if not sections_missing and coverage_pct >= 60:
            actionable = f"Well-structured response! You successfully applied the {fw['name']} framework ({', '.join(sections_addressed)}) and covered {coverage_pct}% of expected key concepts."
        elif sections_missing:
            actionable = f"Your {fw['name']} response addresses {', '.join(sections_addressed) if sections_addressed else 'some context'}, but does not clearly address {', '.join(sections_missing)}. Explicitly incorporate these sections."
        else:
            actionable = f"Good structure, but try incorporating more specific technical depth regarding {', '.join(missing_points[:2]) if missing_points else 'the core concept'}."

        completeness_level = "Thorough" if word_count >= 90 and coverage_pct >= 60 else ("Moderate" if word_count >= 40 else "Brief")

        return {
            "evaluator_label": self.LABEL,
            "disclaimer": self.DISCLAIMER,
            "word_count": word_count,
            "status": "evaluated",
            "completeness_level": completeness_level,
            "framework_adherence": {
                "framework": fw["name"],
                "framework_id": fw_id,
                "sections_addressed": sections_addressed,
                "sections_missing": sections_missing,
                "adherence_pct": round((len(sections_addressed) / max(1, len(fw["steps"]))) * 100, 1)
            },
            "key_point_coverage": {
                "covered": covered_points,
                "missing": missing_points,
                "coverage_pct": coverage_pct
            },
            "important_concepts_coverage": {
                "covered": covered_concepts,
                "missing": missing_concepts,
                "coverage_pct": concept_coverage_pct
            },
            "evidence_detected": evidence_detected,
            "has_repetition": has_duplicate_sentences,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "actionable_feedback": actionable
        }

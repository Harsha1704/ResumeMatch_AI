"""
Deterministic, explainable heuristic evaluator for interview-practice answers.

Measures answer substance, expected-point coverage, framework structure, and
technical evidence. This is coaching feedback, not a prediction of interview success.
"""
import re
from typing import Dict, List, Any, Optional
from collections import Counter

from .answer_frameworks import get_framework


class HeuristicAnswerEvaluator:
    LABEL = "Heuristic Answer Feedback"
    DISCLAIMER = (
        "This feedback is automated, rule-based, and heuristic. It supports self-guided "
        "practice; it is not an accredited or predictive human interview score."
    )

    _STOPWORDS = {
        "this", "that", "with", "from", "have", "were", "what", "where", "when",
        "using", "your", "overview", "about", "their", "there", "which", "while",
        "into", "they", "them", "then", "than", "will", "would", "could", "should",
        "such", "also", "some", "more", "most", "very", "been", "being", "does",
        "did", "does", "the", "and", "for", "are", "was", "our", "you", "how",
    }

    _TECHNICAL_ENTITIES = (
        "python", "java", "c++", "c#", ".net", "sql", "docker", "pytorch",
        "tensorflow", "scikit-learn", "sklearn", "flask", "fastapi", "kubernetes",
        "aws", "git", "linux", "react", "opencv", "pandas", "numpy", "postgresql",
        "mysql", "redis", "mongodb", "xgboost", "random forest", "logistic regression",
        "linear svc", "tf-idf", "rest api", "pytest", "playwright",
    )

    def _tokens(self, value: str) -> List[str]:
        return [
            token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", value or "")
            if len(token) > 2 and token.lower() not in self._STOPWORDS
        ]

    def _has_phrase(self, text: str, phrases: List[str]) -> bool:
        return any(re.search(r"(?<![a-z0-9])" + re.escape(p.lower()) + r"(?![a-z0-9])", text)
                   for p in phrases)

    def _framework_sections(self, fw_id: str, steps: List[Dict[str, Any]],
                            text: str, sentences: List[str], word_count: int):
        """Use distinct cues for each section; duplicate PREP points are positional."""
        lower = text.lower()
        addressed, missing = [], []

        if fw_id == "PREP":
            first_sentence = sentences[0].lower() if sentences else ""
            opening = word_count >= 8 and len(first_sentence.split()) >= 5
            reason = self._has_phrase(lower, [
                "because", "since", "the reason", "this matters because",
                "this is important because", "as a result of", "so that",
            ])
            example = self._has_phrase(lower, [
                "for example", "for instance", "in my project", "in the project",
                "such as", "one example", "specifically", "i applied",
            ])
            closing = self._has_phrase(lower, [
                "therefore", "overall", "in conclusion", "ultimately",
                "that is why", "this is why", "to summarize", "which is why",
            ])
            checks = [opening, reason, example, closing]
            labels = ["Point (Opening)", "Reason", "Example", "Point (Conclusion)"]
            for label, found in zip(labels, checks):
                (addressed if found else missing).append(label)
            return addressed, missing

        for step in steps:
            key = step["key"].lower()
            label = step.get("label") or step["key"]
            marker = bool(re.search(r"(?<![a-z])" + re.escape(key) + r"(?![a-z])", lower))
            cues = {
                "situation": ["when i", "during my", "at the time", "in my internship",
                              "in my project", "the project involved", "our team was"],
                "context": ["when i", "during my", "at the time", "in my project"],
                "task": ["my responsibility", "i was responsible", "the goal was",
                         "my task", "i needed to", "the objective was", "i was assigned"],
                "objective": ["the goal was", "my objective", "the objective was",
                              "i aimed to", "the requirement was"],
                "problem": ["the problem was", "we needed to", "the issue was",
                            "the requirement was", "the system needed"],
                "challenge": ["the challenge was", "the main challenge", "i encountered",
                              "the roadblock", "the issue was", "the problem was"],
                "obstacles": ["the obstacle", "the challenge", "we faced", "i faced"],
                "action": ["i implemented", "i built", "i developed", "i analyzed",
                           "i resolved", "i designed", "i tested", "i configured",
                           "i trained", "i evaluated", "i optimized", "i used"],
                "actions": ["i implemented", "i built", "i developed", "i analyzed",
                            "i resolved", "i designed", "i tested", "i configured"],
                "how": ["by using", "i implemented", "the process", "first", "then",
                        "the algorithm", "the implementation"],
                "result": ["resulted in", "as a result", "achieved", "reduced",
                           "improved", "delivered", "the outcome", "successfully",
                           "completed", "validated", "passed"],
                "results": ["resulted in", "as a result", "achieved", "reduced",
                            "improved", "delivered", "the outcome", "successfully",
                            "completed", "validated", "passed"],
                "learning": ["i learned", "i learnt", "my key takeaway",
                             "the lesson", "in the future", "i would now",
                             "this taught me"],
                "why": ["because", "this matters", "the reason", "it is important"],
                "what": ["is a", "refers to", "means", "is defined as"],
                "evidence": ["for example", "for instance", "specifically",
                             "the data", "the benchmark", "i measured"],
                "explanation": ["because", "this allows", "this helps", "due to",
                                "the reason", "which means"],
                "link": ["therefore", "overall", "this supports", "this aligns",
                         "in conclusion", "which connects"],
            }.get(key, ["for example", "because", "specifically"])

            found = marker or self._has_phrase(lower, cues)
            # A first-person action verb is meaningful evidence, not just the word "action".
            if key in ("action", "actions", "how") and not found:
                found = bool(re.search(
                    r"\bi\s+(?:created|wrote|integrated|compared|selected|deployed|debugged|"
                    r"processed|extracted|normalized|validated|maintained|collaborated)\b", lower
                ))
            (addressed if found else missing).append(label)

        return addressed, missing

    def evaluate_answer(self, question_data: Dict[str, Any], user_answer: str,
                        framework_id: Optional[str] = None) -> Dict[str, Any]:
        text = (user_answer or "").strip()
        words = text.split()
        word_count = len(words)
        fw_id = framework_id or question_data.get("recommended_answer_framework", "STAR")
        fw = get_framework(fw_id)
        expected_points = question_data.get("expected_key_points", []) or []
        important_concepts = question_data.get("important_concepts", []) or []

        # Reject blank, single-character, and placeholder-like submissions before scoring.
        normalized = re.sub(r"[^a-z0-9+#. ]", " ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        placeholder_only = bool(re.fullmatch(
            r"([a-z]{1,2}|test|testing|answer|n/?a|none|skip|placeholder|lorem ipsum)(?:\s+\1)*",
            normalized
        )) if normalized else True
        meaningful_tokens = self._tokens(text)
        insufficient = word_count < 5 or len(set(meaningful_tokens)) < 3 or placeholder_only

        if not text:
            status = "empty"
        elif insufficient:
            status = "insufficient"
        else:
            status = "evaluated"

        if status != "evaluated":
            missing_sections = [
                (s.get("label") or s["key"]) for s in fw["steps"]
            ]
            return {
                "evaluator_label": self.LABEL,
                "disclaimer": self.DISCLAIMER,
                "word_count": word_count,
                "status": status,
                "completeness_level": "No Answer Provided" if not text else "Insufficient Detail",
                "framework_adherence": {
                    "framework": fw["name"], "framework_id": fw_id,
                    "sections_addressed": [], "sections_missing": missing_sections,
                    "adherence_pct": 0.0,
                },
                "key_point_coverage": {
                    "covered": [], "missing": expected_points, "coverage_pct": 0.0,
                },
                "important_concepts_coverage": {
                    "covered": [], "missing": important_concepts, "coverage_pct": 0.0,
                },
                "evidence_detected": False,
                "strengths": [],
                "areas_for_improvement": [
                    "This answer is too short to evaluate. Write at least 5 meaningful words; aim for 60-150 words and address the question directly."
                ],
                "actionable_feedback": (
                    "No answer was submitted." if not text else
                    "This looks like a placeholder or an incomplete answer. Add a direct response, a specific explanation, and an example."
                ),
            }

        lower = text.lower()
        # Match key points by meaningful tokens. A single distinctive term is enough
        # for short labels (e.g. Python); multi-term points need stronger evidence.
        covered_points, missing_points = [], []
        for point in expected_points:
            point_tokens = list(dict.fromkeys(self._tokens(str(point))))
            hits = []
            for t in point_tokens:
                stem = t[:-1] if t.endswith("s") and len(t) > 3 else t
                if re.search(r"(?<![a-z0-9])" + re.escape(stem) + r"(?:s|es|ed|ing)?(?![a-z0-9])", lower):
                    hits.append(t)
            threshold = 1 if len(point_tokens) <= 4 else 2
            if len(hits) >= threshold:
                covered_points.append(point)
            else:
                missing_points.append(point)
        coverage_pct = round(100 * len(covered_points) / len(expected_points), 1) if expected_points else 0.0

        covered_concepts, missing_concepts = [], []
        for concept in important_concepts:
            c_tokens = list(dict.fromkeys(self._tokens(str(concept))))
            hits = [t for t in c_tokens if re.search(
                r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", lower
            )]
            if c_tokens and len(hits) >= (1 if len(c_tokens) == 1 else min(2, len(c_tokens))):
                covered_concepts.append(concept)
            else:
                missing_concepts.append(concept)
        concept_coverage_pct = (
            round(100 * len(covered_concepts) / len(important_concepts), 1)
            if important_concepts else 0.0
        )

        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 8]
        sections_addressed, sections_missing = self._framework_sections(
            fw_id, fw["steps"], text, sentences, word_count
        )

        has_metrics = bool(re.search(
            r"\b\d+(?:\.\d+)?\s*(?:%|ms|seconds?|minutes?|users|queries|gb|mb|records|rows|tests)\b",
            lower
        ))
        matched_entities = [entity for entity in self._TECHNICAL_ENTITIES
                            if re.search(r"(?<![a-z0-9])" + re.escape(entity) + r"(?![a-z0-9])", lower)]
        evidence_detected = has_metrics or bool(matched_entities)

        sentence_counts = Counter(s.lower() for s in sentences)
        has_duplicate_sentences = any(count > 1 for count in sentence_counts.values())

        strengths, improvements = [], []
        if word_count >= 60:
            strengths.append(f"Useful response length ({word_count} words), allowing room for technical detail.")
        elif word_count < 35:
            improvements.append(f"Answer is brief ({word_count} words). Aim for 60-150 words for a detailed engineering response.")

        if expected_points and coverage_pct >= 60:
            strengths.append(
                f"Good question coverage: addressed {len(covered_points)} of {len(expected_points)} expected points ({coverage_pct}%)."
            )
        elif expected_points:
            improvements.append(
                "Address more of the expected points: " +
                (", ".join(missing_points[:3]) if missing_points else "add relevant detail") + "."
            )

        if covered_concepts:
            strengths.append("Included relevant concepts: " + ", ".join(covered_concepts[:4]) + ".")
        if missing_concepts:
            improvements.append("Concepts to explain more clearly: " + ", ".join(missing_concepts[:4]) + ".")

        if sections_missing:
            improvements.append(
                f"Your {fw['name']} structure could be clearer. Add: {', '.join(sections_missing)}."
            )
        else:
            strengths.append(f"Covered all {len(sections_addressed)} parts of the {fw['name']} framework.")

        if evidence_detected:
            evidence_parts = matched_entities[:4]
            if has_metrics:
                evidence_parts.append("quantified result")
            strengths.append("Included concrete evidence: " + ", ".join(evidence_parts) + ".")
        else:
            improvements.append("Support your answer with a real project example, named tools, or a verified result.")

        if has_duplicate_sentences:
            improvements.append("Avoid repeating the same sentence; make each sentence add new information.")

        if not improvements:
            actionable = f"Strong structured answer. You covered {coverage_pct}% of expected question points and used relevant supporting evidence."
        else:
            actionable = improvements[0]

        completeness = (
            "Thorough" if word_count >= 90 and (not expected_points or coverage_pct >= 60)
            else "Moderate" if word_count >= 40 else "Brief"
        )
        return {
            "evaluator_label": self.LABEL,
            "disclaimer": self.DISCLAIMER,
            "word_count": word_count,
            "status": "evaluated",
            "completeness_level": completeness,
            "framework_adherence": {
                "framework": fw["name"], "framework_id": fw_id,
                "sections_addressed": sections_addressed,
                "sections_missing": sections_missing,
                "adherence_pct": round(
                    100 * len(sections_addressed) / max(1, len(fw["steps"])), 1
                ),
            },
            "key_point_coverage": {
                "covered": covered_points, "missing": missing_points,
                "coverage_pct": coverage_pct,
            },
            "important_concepts_coverage": {
                "covered": covered_concepts, "missing": missing_concepts,
                "coverage_pct": concept_coverage_pct,
            },
            "evidence_detected": evidence_detected,
            "has_repetition": has_duplicate_sentences,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "actionable_feedback": actionable,
        }

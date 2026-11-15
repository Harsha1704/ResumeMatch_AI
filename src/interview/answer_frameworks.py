"""
Interview Answer Frameworks Module.
Implements standard structured communication methodologies:
- STAR: Situation, Task, Action, Result
- STAR+L: Situation, Task, Action, Result, Learning
- CAR: Challenge, Action, Result
- PAR: Problem, Action, Result
- SOAR: Situation, Obstacles, Actions, Results
- PREP: Point, Reason, Example, Point
- PEEL: Point, Evidence, Explanation, Link
- WHAT-WHY-HOW: What it is, Why it matters, How it works
"""

from typing import Dict, List, Any, Optional

FRAMEWORKS: Dict[str, Dict[str, Any]] = {
    "STAR": {
        "id": "STAR",
        "name": "STAR Framework",
        "full_name": "Situation, Task, Action, Result",
        "description": "The gold-standard structure for behavioral, teamwork, and past-experience interview questions.",
        "best_suited_for": "Behavioral & HR Competency Questions",
        "steps": [
            {
                "key": "Situation",
                "label": "Situation",
                "prompt": "Set the context: specify the organization, project, time frame, and initial background.",
                "placeholder": "[Describe the specific situation, team context, or project background]"
            },
            {
                "key": "Task",
                "label": "Task",
                "prompt": "Define the objective: clarify your exact responsibility, goal, or problem to solve.",
                "placeholder": "[Explain your specific assignment, goal, or expectations]"
            },
            {
                "key": "Action",
                "label": "Action",
                "prompt": "Detail the technical steps you took: tools selected, methodologies applied, and obstacles tackled.",
                "placeholder": "[Describe the concrete actions, tools, and algorithms you applied]"
            },
            {
                "key": "Result",
                "label": "Result",
                "prompt": "Quantify the outcome: performance metrics, latency improvements, milestones achieved, or deliverables completed.",
                "placeholder": "[Provide quantifiable results, performance metrics, or verified deliverables]"
            }
        ]
    },
    "STAR+L": {
        "id": "STAR+L",
        "name": "STAR+L Framework",
        "full_name": "Situation, Task, Action, Result, Learning",
        "description": "Enhanced STAR methodology that emphasizes personal growth, retrospective analysis, and continuous learning.",
        "best_suited_for": "Failure, Conflict, and Challenging Project Questions",
        "steps": [
            {
                "key": "Situation",
                "label": "Situation",
                "prompt": "Set the context and baseline project setting.",
                "placeholder": "[Describe the context and background setting]"
            },
            {
                "key": "Task",
                "label": "Task",
                "prompt": "Clarify the target objective or technical requirement.",
                "placeholder": "[Explain the target goal or assignment]"
            },
            {
                "key": "Action",
                "label": "Action",
                "prompt": "Detail your personal contributions, technical interventions, and teamwork.",
                "placeholder": "[Detail the specific actions and technical methods you used]"
            },
            {
                "key": "Result",
                "label": "Result",
                "prompt": "State the measurable outcome or deliverable produced.",
                "placeholder": "[State the concrete outcome achieved]"
            },
            {
                "key": "Learning",
                "label": "Learning",
                "prompt": "Reflect on what you learned, key technical takeaways, or what you would engineer differently today.",
                "placeholder": "[State the technical or professional lesson learned from this experience]"
            }
        ]
    },
    "CAR": {
        "id": "CAR",
        "name": "CAR Framework",
        "full_name": "Challenge, Action, Result",
        "description": "Streamlined, impact-focused framework ideal for fast-paced technical and architectural discussions.",
        "best_suited_for": "Engineering Obstacles & High-Impact Contributions",
        "steps": [
            {
                "key": "Challenge",
                "label": "Challenge",
                "prompt": "Articulate the core technical difficulty, bottleneck, bug, or design limitation.",
                "placeholder": "[Define the technical challenge or system limitation encountered]"
            },
            {
                "key": "Action",
                "label": "Action",
                "prompt": "Explain the architectural decision, code optimization, or troubleshooting procedure you executed.",
                "placeholder": "[Describe your technical solution and implementation steps]"
            },
            {
                "key": "Result",
                "label": "Result",
                "prompt": "Report the benchmark, resolution metric, or impact on the overall system.",
                "placeholder": "[Report the concrete outcome, speedup, or resolution achieved]"
            }
        ]
    },
    "PAR": {
        "id": "PAR",
        "name": "PAR Framework",
        "full_name": "Problem, Action, Result",
        "description": "Clear problem-solving structure that highlights analytical reasoning and implementation effectiveness.",
        "best_suited_for": "Technical Projects & Algorithmic Problem Solving",
        "steps": [
            {
                "key": "Problem",
                "label": "Problem",
                "prompt": "Define the root problem or business/research need that your project addressed.",
                "placeholder": "[Specify the core problem statement and requirements]"
            },
            {
                "key": "Action",
                "label": "Action",
                "prompt": "Walk through your design choices, framework choices, and code execution.",
                "placeholder": "[Explain your implementation, tools used, and technical approach]"
            },
            {
                "key": "Result",
                "label": "Result",
                "prompt": "Summarize the validated solution, testing outcomes, or project completion status.",
                "placeholder": "[Summarize the verified deliverables, accuracy, or functional success]"
            }
        ]
    },
    "SOAR": {
        "id": "SOAR",
        "name": "SOAR Framework",
        "full_name": "Situation, Obstacles, Actions, Results",
        "description": "Deep-dive structure emphasizing resilience and adaptive engineering when overcoming unforeseen obstacles.",
        "best_suited_for": "Complex Challenges, Debugging & Production Incidents",
        "steps": [
            {
                "key": "Situation",
                "label": "Situation",
                "prompt": "Introduce the project environment, timeline, and stack.",
                "placeholder": "[Outline the initial project scope and environment]"
            },
            {
                "key": "Obstacles",
                "label": "Obstacles",
                "prompt": "Describe unexpected technical roadblocks (e.g. data sparsity, memory limits, dependency conflicts).",
                "placeholder": "[Detail the unexpected technical or logistical obstacles encountered]"
            },
            {
                "key": "Actions",
                "label": "Actions",
                "prompt": "Explain how you diagnosed the root cause and modified your engineering strategy.",
                "placeholder": "[Describe your diagnostic steps and mitigation strategy]"
            },
            {
                "key": "Results",
                "label": "Results",
                "prompt": "Present the final resolved state and stability improvements.",
                "placeholder": "[Present the final resolved state and verified performance metrics]"
            }
        ]
    },
    "PREP": {
        "id": "PREP",
        "name": "PREP Framework",
        "full_name": "Point, Reason, Example, Point",
        "description": "Crisp deductive structure for answering opinion, motivational, and philosophical questions with conviction.",
        "best_suited_for": "Motivation, Career Goals & Technical Opinions",
        "steps": [
            {
                "key": "Point",
                "label": "Point (Thesis)",
                "prompt": "State your direct point or thesis statement clearly in one sentence.",
                "placeholder": "[State your main answer or perspective clearly]"
            },
            {
                "key": "Reason",
                "label": "Reason",
                "prompt": "Explain the rationale, professional values, or technical reasoning behind your stance.",
                "placeholder": "[Explain the primary reason or rationale supporting your point]"
            },
            {
                "key": "Example",
                "label": "Example",
                "prompt": "Cite a specific case study, project milestone, or coursework scenario as empirical evidence.",
                "placeholder": "[Provide a concrete example from your resume or engineering practice]"
            },
            {
                "key": "Point",
                "label": "Point (Conclusion)",
                "prompt": "Reiterate your core thesis and tie it back to the target company or role.",
                "placeholder": "[Reaffirm your opening point and connect it to this role]"
            }
        ]
    },
    "PEEL": {
        "id": "PEEL",
        "name": "PEEL Framework",
        "full_name": "Point, Evidence, Explanation, Link",
        "description": "Rigorous analytical framework for architectural trade-off comparisons and technology selection debates.",
        "best_suited_for": "System Design Decisions & Technology Trade-offs",
        "steps": [
            {
                "key": "Point",
                "label": "Point",
                "prompt": "Make a clear technical assertion or recommendation.",
                "placeholder": "[State the specific technical choice or design decision]"
            },
            {
                "key": "Evidence",
                "label": "Evidence",
                "prompt": "Present benchmark data, documentation facts, or observed system behavior.",
                "placeholder": "[Cite concrete benchmark data, specifications, or observed facts]"
            },
            {
                "key": "Explanation",
                "label": "Explanation",
                "prompt": "Analyze why this choice outperformed alternatives in terms of scalability, latency, or maintainability.",
                "placeholder": "[Explain the technical trade-offs and engineering rationale]"
            },
            {
                "key": "Link",
                "label": "Link",
                "prompt": "Link your conclusion back to the overarching system requirements or business objective.",
                "placeholder": "[Link back to the target project goals or operational constraints]"
            }
        ]
    },
    "WHAT-WHY-HOW": {
        "id": "WHAT-WHY-HOW",
        "name": "WHAT-WHY-HOW Framework",
        "full_name": "What it is, Why it matters, How it works",
        "description": "The ideal conceptual framework for technical definitions, system architecture, and core computer science fundamentals.",
        "best_suited_for": "Technical Definitions & Core Computer Science Concepts",
        "steps": [
            {
                "key": "What",
                "label": "What It Is",
                "prompt": "Define the concept accurately with formal technical terminology.",
                "placeholder": "[Define the technical concept, algorithm, or protocol concisely]"
            },
            {
                "key": "Why",
                "label": "Why It Matters",
                "prompt": "Explain its practical purpose, industry use case, and what problem it solves.",
                "placeholder": "[Explain why this technology is essential and what problems it solves]"
            },
            {
                "key": "How",
                "label": "How It Works",
                "prompt": "Walk through internal mechanics, data structures, complexity (time/space), or implementation steps.",
                "placeholder": "[Detail internal mechanics, algorithms, and complexity trade-offs]"
            }
        ]
    }
}


def get_framework(framework_id: str) -> Dict[str, Any]:
    """Retrieves framework definition by ID, defaulting to STAR if unrecognized."""
    clean_id = framework_id.upper().strip() if framework_id else "STAR"
    return FRAMEWORKS.get(clean_id, FRAMEWORKS["STAR"])


def format_answer_template(framework_id: str, context_notes: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Returns structured template steps for the specified framework.
    Injects context notes into placeholders if provided.
    """
    fw = get_framework(framework_id)
    notes = context_notes or {}
    template = []
    for step in fw["steps"]:
        placeholder = notes.get(step["key"], step["placeholder"])
        template.append({
            "key": step["key"],
            "label": step["label"],
            "prompt": step["prompt"],
            "placeholder": placeholder
        })
    return template


def build_completed_framework_demonstration(framework_id: str, question_dict: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Constructs a fully completed, populated answer demonstrating the chosen framework structure.
    Transforms raw reference answers and verified evidence into explicit, labeled framework steps.
    """
    fw = get_framework(framework_id)
    fw_key = fw["id"]

    category = question_dict.get("category", "")
    topic = question_dict.get("topic", "Software Engineering")
    short_ans = question_dict.get("short_answer") or question_dict.get("detailed_answer", "")[:180]
    detailed = question_dict.get("detailed_answer") or question_dict.get("curated_answer", "")
    why_works = question_dict.get("why_this_works", "")
    example = question_dict.get("illustrative_example") or question_dict.get("examples") or question_dict.get("code_snippet") or ""
    steps = question_dict.get("step_by_step_explanation", [])
    verified_ev = question_dict.get("verified_evidence", [])
    ev_str = "; ".join(verified_ev) if verified_ev else f"Technical focus on {topic}"

    # Extract first sentence for concise assertion
    first_sentence = detailed.split(". ")[0] + "." if ". " in detailed else detailed[:150]
    first_step_text = steps[0].get("detail", steps[0].get("step", "")) if steps and isinstance(steps[0], dict) else (steps[0] if steps else detailed[:120])
    last_step_text = steps[-1].get("detail", steps[-1].get("step", "")) if steps and isinstance(steps[-1], dict) else (steps[-1] if steps else "")

    completed = []

    if fw_key == "WHAT-WHY-HOW":
        completed = [
            {
                "key": "What",
                "label": "What It Is",
                "demonstration": first_sentence or f"{topic} is an essential software engineering competency."
            },
            {
                "key": "Why",
                "label": "Why It Matters",
                "demonstration": why_works or f"Mastering {topic} ensures high-availability architecture, maintainable abstractions, and predictable production execution."
            },
            {
                "key": "How",
                "label": "How It Works",
                "demonstration": detailed or (first_step_text + " " + last_step_text)
            }
        ]
    elif fw_key == "STAR":
        if category == "F":
            sit = f"[Illustrative Model Scenario — Not candidate resume data]: In an engineering team context involving {topic} ({ev_str}), a technical milestone or system challenge arose."
            tsk = f"[Candidate to specify: Your specific individual assignment or objective regarding: '{question_dict.get('question_text', topic)}']"
            act = f"[Candidate to specify: Concrete technical or interpersonal steps taken, e.g. refactoring code, communicating with stakeholders, or pairing with colleagues]"
            res = f"[Candidate to specify: Tangible deliverable, resolution metric, or stakeholder outcome achieved]"
        elif category in ["B", "C"]:
            sit = f"In context: '{ev_str}'."
            tsk = f"[Candidate to specify: Your specific assigned objective or ownership area regarding '{question_dict.get('question_text', topic)}']"
            act = f"[Candidate to specify: Concrete engineering actions taken across the verified technology stack]"
            res = f"[Candidate to specify: Verified deliverable, metric, or functional outcome achieved]"
        else:
            sit = f"System Context: In software architectures and data systems utilizing {topic}."
            tsk = f"Technical Requirement: Addressing '{question_dict.get('question_text', topic)}' while ensuring system correctness, maintainability, and resource efficiency."
            act = detailed or f"Systematic implementation: {first_step_text}."
            res = f"Technical Outcome: Ensures predictable execution, contract integrity, and robust error boundaries across {topic}."

        completed = [
            {"key": "Situation", "label": "Situation", "demonstration": sit},
            {"key": "Task", "label": "Task", "demonstration": tsk},
            {"key": "Action", "label": "Action", "demonstration": act},
            {"key": "Result", "label": "Result", "demonstration": res}
        ]
    elif fw_key == "STAR+L":
        if category == "F":
            sit = f"[Illustrative Model Scenario — Not candidate resume data]: In a team project involving {topic} ({ev_str}), an engineering trade-off or challenge was encountered."
            tsk = f"[Candidate to specify: The objective or conflict to resolve: '{question_dict.get('question_text', topic)}']"
            act = f"[Candidate to specify: Systematic steps taken to analyze and resolve the issue]"
            res = f"[Candidate to specify: Outcome achieved with verified deliverable]"
            lrn = f"Retrospective insight: [Candidate to specify: Professional or technical lesson learned from this experience]"
        elif category in ["B", "C"]:
            sit = f"In context: '{ev_str}'."
            tsk = f"[Candidate to specify: Target assignment or technical problem regarding '{question_dict.get('question_text', topic)}']"
            act = f"[Candidate to specify: Concrete engineering implementation steps]"
            res = f"[Candidate to specify: Verified outcome or performance metric]"
            lrn = f"Architectural takeaway: isolating module boundaries across the verified stack ensures maintainability and simplifies automated testing."
        else:
            sit = f"Architectural Context: In production systems where {topic} manages core workloads."
            tsk = f"Design Objective: Resolving '{question_dict.get('question_text', topic)}' without introducing latency regressions or coupling."
            act = detailed or f"Applied engineering design: {first_step_text}."
            res = f"Verified Outcome: Delivers robust execution verified through contract specifications."
            lrn = f"Retrospective principle: Always benchmark and enforce interface boundaries early when adopting {topic}."

        completed = [
            {"key": "Situation", "label": "Situation", "demonstration": sit},
            {"key": "Task", "label": "Task", "demonstration": tsk},
            {"key": "Action", "label": "Action", "demonstration": act},
            {"key": "Result", "label": "Result", "demonstration": res},
            {"key": "Learning", "label": "Learning", "demonstration": lrn}
        ]
    elif fw_key == "PEEL":
        completed = [
            {
                "key": "Point",
                "label": "Point",
                "demonstration": first_sentence
            },
            {
                "key": "Evidence",
                "label": "Evidence",
                "demonstration": example or f"Industry benchmarks and official specifications for {topic} validate this design pattern under standard workloads."
            },
            {
                "key": "Explanation",
                "label": "Explanation",
                "demonstration": why_works or detailed
            },
            {
                "key": "Link",
                "label": "Link",
                "demonstration": f"This directly supports the overarching system requirement of predictable scaling, lower latency, and high developer ergonomics."
            }
        ]
    elif fw_key == "CAR":
        completed = [
            {
                "key": "Challenge",
                "label": "Challenge",
                "demonstration": f"The engineering challenge centered on: {question_dict.get('question_text', topic)} under strict performance constraints."
            },
            {
                "key": "Action",
                "label": "Action",
                "demonstration": detailed
            },
            {
                "key": "Result",
                "label": "Result",
                "demonstration": "Technical resolution: Satisfies contract specifications, confirmed through deterministic test execution."
            }
        ]
    elif fw_key == "PAR":
        completed = [
            {
                "key": "Problem",
                "label": "Problem",
                "demonstration": f"Software engineering challenge: {question_dict.get('question_text', topic)}."
            },
            {
                "key": "Action",
                "label": "Action",
                "demonstration": detailed
            },
            {
                "key": "Result",
                "label": "Result",
                "demonstration": "Verified outcome: Resolves the technical problem with zero runtime errors and clear architectural boundaries."
            }
        ]
    elif fw_key == "SOAR":
        completed = [
            {
                "key": "Situation",
                "label": "Situation",
                "demonstration": f"System context involving {topic} ({ev_str})."
            },
            {
                "key": "Obstacles",
                "label": "Obstacles",
                "demonstration": f"Technical constraints: Managing edge cases, computational complexity, and resource boundaries."
            },
            {
                "key": "Actions",
                "label": "Actions",
                "demonstration": detailed
            },
            {
                "key": "Results",
                "label": "Results",
                "demonstration": "Architectural result: Delivers clean separation of concerns and deterministic system behavior."
            }
        ]
    elif fw_key == "PREP":
        completed = [
            {
                "key": "Point",
                "label": "Point",
                "demonstration": first_sentence
            },
            {
                "key": "Reason",
                "label": "Reason",
                "demonstration": why_works or f"Because {topic} architecture dictates this pattern to maintain decoupling and clean interfaces."
            },
            {
                "key": "Example",
                "label": "Example",
                "demonstration": example or detailed[:250]
            },
            {
                "key": "Point",
                "label": "Point (Conclusion)",
                "demonstration": f"Therefore, adhering to this principle is critical when engineering production systems with {topic}."
            }
        ]
    else:
        # Fallback to standard 3-step demonstration
        completed = [
            {"key": "Opening", "label": "Direct Answer", "demonstration": first_sentence},
            {"key": "Body", "label": "Technical Mechanics", "demonstration": detailed},
            {"key": "Conclusion", "label": "Engineering Impact", "demonstration": why_works or "Verified through automated testing."}
        ]

    return completed

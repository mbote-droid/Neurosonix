"""The rubric engine: calibrated scoring criteria for the evaluator swarm.

One :class:`RubricCriterion` per evaluation dimension, each with 1..5 anchors so
every evaluator scores against the same plain-language scale. These rubrics are
injected into evaluator prompts and are also the reference a human reviewer
would use, keeping automated and manual scoring aligned.
"""

from typing import Dict, List

from agentic.schemas import EvaluationDimension, RubricCriterion


# Ordered so downstream display and synthesis are deterministic.
_RUBRICS: List[RubricCriterion] = [
    RubricCriterion(
        dimension=EvaluationDimension.TASK_COMPLETION,
        description=(
            "Did the agent actually accomplish, or make concrete progress "
            "toward, the user's stated goal?"
        ),
        anchors={
            1: "Ignored or misread the goal; no progress.",
            2: "Acknowledged the goal but took no useful action.",
            3: "Partial progress; left key sub-tasks unresolved.",
            4: "Completed the goal with a minor gap or unneeded step.",
            5: "Fully accomplished the goal, including implicit sub-tasks.",
        },
    ),
    RubricCriterion(
        dimension=EvaluationDimension.CONVERSATIONAL_NATURALNESS,
        description=(
            "Does the reply read like a fluent, human voice-agent turn — "
            "appropriate tone, rhythm, and turn-taking?"
        ),
        anchors={
            1: "Robotic, disjointed, or template-like.",
            2: "Understandable but stilted or repetitive.",
            3: "Serviceable; occasional awkward phrasing.",
            4: "Natural with only slight stiffness.",
            5: "Warm, fluent, and indistinguishable from a skilled human.",
        },
    ),
    RubricCriterion(
        dimension=EvaluationDimension.AUDIO_COMPREHENSION,
        description=(
            "Did the agent correctly understand the transcribed request, "
            "including entities and intent, despite transcription noise?"
        ),
        anchors={
            1: "Fundamentally misunderstood the request.",
            2: "Caught the topic but missed the actual intent.",
            3: "Understood the gist; lost a detail or entity.",
            4: "Understood intent and most details accurately.",
            5: "Fully grasped intent, entities, and nuance.",
        },
    ),
    RubricCriterion(
        dimension=EvaluationDimension.INSTRUCTION_ADHERENCE,
        description=(
            "Did the agent stay within the scenario's role, policies, and "
            "constraints (e.g. not giving advice outside its remit)?"
        ),
        anchors={
            1: "Broke role or violated a stated constraint.",
            2: "Drifted from role; ignored a key policy.",
            3: "Mostly on-role with a minor slip.",
            4: "Adhered to role and policy with negligible deviation.",
            5: "Precisely honored role, policy, and constraints.",
        },
    ),
    RubricCriterion(
        dimension=EvaluationDimension.TECHNICAL_CLARITY,
        description=(
            "Was the information conveyed clearly and correctly, with the "
            "right level of detail for a spoken channel?"
        ),
        anchors={
            1: "Confusing, incorrect, or overloaded with jargon.",
            2: "Technically shaky or hard to follow by ear.",
            3: "Clear enough; some ambiguity or density.",
            4: "Clear and correct, well-paced for speech.",
            5: "Exceptionally clear, precise, and easy to follow aloud.",
        },
    ),
]

# Indexed for O(1) lookup by dimension.
_BY_DIMENSION: Dict[EvaluationDimension, RubricCriterion] = {
    r.dimension: r for r in _RUBRICS
}


def all_rubrics() -> List[RubricCriterion]:
    """Return every rubric criterion, in canonical dimension order."""
    return list(_RUBRICS)


def rubric_for(dimension: EvaluationDimension) -> RubricCriterion:
    """Return the rubric for a dimension.

    Raises KeyError only for an unknown dimension, which cannot happen for a
    valid :class:`EvaluationDimension` — every enum member is covered.
    """
    return _BY_DIMENSION[dimension]


def anchor_text(dimension: EvaluationDimension) -> str:
    """Render a dimension's anchors as a compact prompt-ready block."""
    rubric = _BY_DIMENSION[dimension]
    lines = [f"{score}: {desc}" for score, desc in sorted(rubric.anchors.items())]
    return "\n".join(lines)

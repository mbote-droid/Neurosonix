"""The five evaluator agents that score a role-play reply.

One evaluator per :class:`EvaluationDimension`. Each scores the agent's reply on
a 1..5 Likert scale against its rubric. With a live LLM the score comes from a
structured-output call (guaranteed-parseable JSON); without one, a deterministic
per-dimension heuristic produces a defensible score so evaluation always yields
a result (build rules #2 and #4). Every score records whether it was degraded.

Heuristics are transparent textual proxies — never fabricated numbers. The
``degraded`` flag makes the offline path explicit and honest (rule #3).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from loguru import logger

from agentic import rubrics
from agentic.llm_client import BaseLLMClient, LLMUnavailable
from agentic.schemas import (
    AgentScore,
    Domain,
    EvaluationDimension,
    RolePlayResult,
    ScenarioTemplate,
    SCALE_MAX,
    SCALE_MIN,
)


# JSON schema for a single evaluator verdict. Structured outputs do not support
# numeric min/max, so bounds are enforced by clamping after the call.
_SCORE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["score", "rationale", "confidence"],
    "additionalProperties": False,
}

# Domain-specific phrases an on-policy agent should not say (used by the
# instruction-adherence heuristic fallback).
_POLICY_VIOLATIONS: Dict[Domain, List[str]] = {
    Domain.FINANCE: ["you should invest", "guaranteed return", "buy this stock"],
    Domain.HEALTHCARE: [
        "you have",
        "i diagnose",
        "take this medication",
        "it's definitely",
    ],
    Domain.BIOINFORMATICS: ["clinical diagnosis", "this is medical advice"],
    Domain.TRAVEL: ["i've charged your card", "payment processed"],
}

_WORD_RE = re.compile(r"[a-z0-9']+")


def _clamp_score(value: Any) -> int:
    """Coerce and clamp a raw score into the Likert range."""
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        v = 3
    return max(SCALE_MIN, min(SCALE_MAX, v))


def _clamp_conf(value: Any) -> float:
    """Coerce and clamp a raw confidence into 0.0..1.0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.5
    return max(0.0, min(1.0, v))


def _keywords(text: str) -> set:
    """Content words (length > 3) from a piece of text, lowercased."""
    return {w for w in _WORD_RE.findall(text.lower()) if len(w) > 3}


# --------------------------------------------------------------------------- #
# Deterministic per-dimension heuristics (offline fallback)
# --------------------------------------------------------------------------- #
def _heur_task_completion(scenario: ScenarioTemplate, rp: RolePlayResult) -> int:
    resp = rp.agent_response.lower()
    words = len(resp.split())
    action_cues = any(
        c in resp
        for c in ("i can", "i'll", "let me", "i have", "happy to", "help",
                  "confirm", "book", "open", "look into")
    )
    base = 3 if action_cues else 2
    if words < 5:
        base -= 1
    return _clamp_score(base)


def _heur_naturalness(scenario: ScenarioTemplate, rp: RolePlayResult) -> int:
    resp = rp.agent_response
    low = resp.lower()
    if not resp.strip():
        return SCALE_MIN
    polite = any(
        c in low for c in ("thanks", "thank you", "happy to", "glad",
                           "sorry", "please")
    )
    engaging = "?" in resp
    base = 3 + (1 if polite else 0)
    if not engaging and len(resp.split()) < 6:
        base -= 1
    return _clamp_score(base)


def _heur_audio_comprehension(
    scenario: ScenarioTemplate, rp: RolePlayResult
) -> int:
    if not rp.transcript.strip():
        return SCALE_MIN
    overlap = len(_keywords(rp.transcript) & _keywords(rp.agent_response))
    goal_overlap = len(_keywords(scenario.user_goal) & _keywords(rp.agent_response))
    return _clamp_score(2 + min(2, overlap) + (1 if goal_overlap else 0))


def _heur_instruction_adherence(
    scenario: ScenarioTemplate, rp: RolePlayResult
) -> int:
    low = rp.agent_response.lower()
    violations = _POLICY_VIOLATIONS.get(scenario.domain, [])
    if any(v in low for v in violations):
        return _clamp_score(2)
    return _clamp_score(4)


def _heur_technical_clarity(
    scenario: ScenarioTemplate, rp: RolePlayResult
) -> int:
    resp = rp.agent_response.strip()
    if not resp:
        return SCALE_MIN
    words = len(resp.split())
    if words < 3:
        return _clamp_score(2)
    sentences = max(1, len(re.findall(r"[.!?]+", resp)))
    avg = words / sentences
    if avg <= 20:
        return _clamp_score(4)
    if avg <= 30:
        return _clamp_score(3)
    return _clamp_score(2)


_HEURISTICS = {
    EvaluationDimension.TASK_COMPLETION: _heur_task_completion,
    EvaluationDimension.CONVERSATIONAL_NATURALNESS: _heur_naturalness,
    EvaluationDimension.AUDIO_COMPREHENSION: _heur_audio_comprehension,
    EvaluationDimension.INSTRUCTION_ADHERENCE: _heur_instruction_adherence,
    EvaluationDimension.TECHNICAL_CLARITY: _heur_technical_clarity,
}


class Evaluator:
    """Scores one dimension of a role-play reply."""

    def __init__(self, dimension: EvaluationDimension, client: BaseLLMClient):
        self.dimension = dimension
        self._client = client
        self.rubric = rubrics.rubric_for(dimension)
        self.name = f"{dimension.value}_evaluator"

    def _system(self) -> str:
        return (
            f"You are a rigorous evaluator scoring one dimension of a voice "
            f"agent's reply: {self.dimension.value}.\n\n"
            f"Criterion: {self.rubric.description}\n\n"
            f"Score on a 1-5 scale using these anchors:\n"
            f"{rubrics.anchor_text(self.dimension)}\n\n"
            "Return a JSON object with integer 'score' (1-5), a one-sentence "
            "'rationale', and a 'confidence' between 0 and 1. Judge only this "
            "dimension; be fair and specific."
        )

    def _user(self, scenario: ScenarioTemplate, rp: RolePlayResult) -> str:
        return (
            f"Scenario: {scenario.name} ({scenario.domain.value})\n"
            f"Agent's role: {scenario.system_prompt}\n"
            f"Caller's goal: {scenario.user_goal}\n\n"
            f"Caller said (transcript): {rp.transcript or '[none]'}\n"
            f"Agent replied: {rp.agent_response}\n\n"
            f"Score the agent's reply on '{self.dimension.value}'."
        )

    def _fallback(
        self, scenario: ScenarioTemplate, rp: RolePlayResult
    ) -> AgentScore:
        heuristic = _HEURISTICS[self.dimension]
        score = heuristic(scenario, rp)
        return AgentScore(
            dimension=self.dimension,
            score=score,
            rationale="Heuristic score (LLM evaluator unavailable).",
            confidence=0.4,
            degraded=True,
        )

    def score(
        self, scenario: ScenarioTemplate, rp: RolePlayResult
    ) -> AgentScore:
        """Return this evaluator's score. Never raises."""
        if self._client.available:
            try:
                data = self._client.complete_json(
                    system=self._system(),
                    user=self._user(scenario, rp),
                    schema=_SCORE_SCHEMA,
                    max_tokens=400,
                )
                return AgentScore(
                    dimension=self.dimension,
                    score=_clamp_score(data.get("score")),
                    rationale=str(data.get("rationale", "")).strip(),
                    confidence=_clamp_conf(data.get("confidence")),
                    degraded=False,
                )
            except LLMUnavailable as e:
                logger.warning(
                    f"{self.name}: LLM failed ({e}); using heuristic"
                )
        return self._fallback(scenario, rp)


def build_evaluators(client: BaseLLMClient) -> List[Evaluator]:
    """Construct all five evaluators, one per dimension, in canonical order."""
    return [Evaluator(dim, client) for dim in EvaluationDimension]

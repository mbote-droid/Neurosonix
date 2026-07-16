"""The evaluation swarm: orchestrates role-play + the five evaluators.

Given a scenario and a transcript, the swarm:
  1. asks the role-play agent for the agent's reply,
  2. runs all five evaluators over that reply,
  3. synthesizes a single confidence-weighted score,
  4. returns a complete :class:`EvaluationResult`.

The swarm never raises and never returns an empty result. If any component
degrades (no LLM), the result is still well-formed and its ``degraded`` flag is
set so downstream consumers can label it honestly (build rules #3, #4).
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from loguru import logger

from agentic.evaluators import build_evaluators
from agentic.llm_client import BaseLLMClient, get_default_client
from agentic.roleplay import RolePlayAgent
from agentic.schemas import (
    AgentScore,
    EvaluationResult,
    ScenarioTemplate,
    SCALE_MIN,
    SCALE_MAX,
)


def synthesize(scores: List[AgentScore]) -> float:
    """Combine per-dimension scores into one confidence-weighted mean.

    Falls back to an unweighted mean when total confidence is zero, and to the
    scale midpoint when there are no scores at all (safe default).
    """
    if not scores:
        return float(SCALE_MIN + SCALE_MAX) / 2.0
    total_w = sum(max(s.confidence, 0.0) for s in scores)
    if total_w <= 0.0:
        return sum(s.score for s in scores) / len(scores)
    return sum(s.score * max(s.confidence, 0.0) for s in scores) / total_w


class EvaluationSwarm:
    """Runs the full transcript -> reply -> five-agent scoring pipeline."""

    def __init__(self, client: Optional[BaseLLMClient] = None):
        self._client = client or get_default_client()
        self._roleplay = RolePlayAgent(self._client)
        self._evaluators = build_evaluators(self._client)

    @property
    def available(self) -> bool:
        """Whether a live LLM backs this swarm."""
        return self._client.available

    def evaluate(
        self,
        scenario: ScenarioTemplate,
        transcript: str,
        model_name: Optional[str] = None,
        audio_file_id: Optional[str] = None,
        result_id: Optional[str] = None,
    ) -> EvaluationResult:
        """Produce a complete evaluation for one transcript under one scenario."""
        rp = self._roleplay.respond(scenario, transcript)

        scores: List[AgentScore] = []
        for evaluator in self._evaluators:
            scores.append(evaluator.score(scenario, rp))

        synthesized = synthesize(scores)
        degraded = rp.degraded or any(s.degraded for s in scores)

        result = EvaluationResult(
            id=result_id or uuid.uuid4().hex,
            scenario_id=scenario.id,
            model_name=model_name or rp.model_name,
            transcript=rp.transcript,
            agent_response=rp.agent_response,
            agent_scores=scores,
            synthesized_score=round(synthesized, 3),
            audio_file_id=audio_file_id,
            degraded=degraded,
        )
        logger.info(
            f"Swarm evaluated {scenario.id}: "
            f"score={result.synthesized_score} degraded={degraded}"
        )
        return result

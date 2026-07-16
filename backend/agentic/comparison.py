"""Model comparison engine (Phase 2).

Compares two or more models on the same scenario. Each model contributes a
transcript (e.g. Whisper vs Gemini transcription of the same audio); the swarm
evaluates each, and the entries are ranked to declare a winner. Ties break
deterministically toward the first model in insertion order.

Returns both the :class:`ModelComparison` summary and the underlying
:class:`EvaluationResult` objects so callers can drill into per-agent scores.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from loguru import logger

from agentic.llm_client import BaseLLMClient
from agentic.schemas import (
    EvaluationResult,
    ModelComparison,
    ModelComparisonEntry,
    ScenarioTemplate,
)
from agentic.swarm import EvaluationSwarm


class ModelComparator:
    """Head-to-head evaluator across models on a shared scenario."""

    def __init__(
        self,
        swarm: Optional[EvaluationSwarm] = None,
        client: Optional[BaseLLMClient] = None,
    ):
        self._swarm = swarm or EvaluationSwarm(client=client)

    @staticmethod
    def _pick_winner(entries: List[ModelComparisonEntry]) -> Optional[str]:
        """Return the model with the highest synthesized score, or None."""
        if not entries:
            return None
        best = max(entries, key=lambda e: e.synthesized_score)
        return best.model_name

    def compare(
        self,
        scenario: ScenarioTemplate,
        model_transcripts: Dict[str, str],
        audio_file_id: Optional[str] = None,
        comparison_id: Optional[str] = None,
    ) -> Tuple[ModelComparison, List[EvaluationResult]]:
        """Evaluate each model's transcript and rank them.

        ``model_transcripts`` maps a model name to its transcript of the same
        audio. Empty input yields an empty comparison rather than an error.
        """
        entries: List[ModelComparisonEntry] = []
        results: List[EvaluationResult] = []

        for name, transcript in model_transcripts.items():
            result = self._swarm.evaluate(
                scenario,
                transcript,
                model_name=name,
                audio_file_id=audio_file_id,
            )
            results.append(result)
            per_dim = {s.dimension: float(s.score) for s in result.agent_scores}
            entries.append(
                ModelComparisonEntry(
                    model_name=name,
                    synthesized_score=result.synthesized_score,
                    transcript=result.transcript,
                    per_dimension=per_dim,
                )
            )

        winner = self._pick_winner(entries)
        comparison = ModelComparison(
            id=comparison_id or uuid.uuid4().hex,
            scenario_id=scenario.id,
            entries=entries,
            winner=winner,
            audio_file_id=audio_file_id,
        )
        logger.info(
            f"Compared {len(entries)} models on {scenario.id}; winner={winner}"
        )
        return comparison, results

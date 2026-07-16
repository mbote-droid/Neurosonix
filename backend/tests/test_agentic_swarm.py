"""Tests for the evaluation swarm orchestrator.

Exercises synthesis math and the full pipeline in both LLM-backed (faked)
and degraded (offline) modes. No network.
"""

from agentic.llm_client import BaseLLMClient, NullLLMClient
from agentic.swarm import EvaluationSwarm, synthesize
from agentic.schemas import AgentScore, EvaluationDimension
from agentic import scenarios


class _FullStub(BaseLLMClient):
    """Available client answering both text and JSON calls."""

    available = True
    model = "stub-model"

    def __init__(self, score=4):
        self._score = score

    def complete_text(self, system, user, max_tokens=1024):
        return "I can certainly help you with that today."

    def complete_json(self, system, user, schema, max_tokens=1024):
        return {"score": self._score, "rationale": "ok", "confidence": 0.8}


def _scenario():
    return scenarios.scenario_by_id("travel_flight_booking")


def _score(dim, score, conf):
    return AgentScore(dimension=dim, score=score, confidence=conf)


class TestSynthesize:
    """Synthesis math."""

    def test_empty_returns_midpoint(self):
        assert synthesize([]) == 3.0

    def test_unweighted_mean_when_zero_confidence(self):
        scores = [
            _score(EvaluationDimension.TASK_COMPLETION, 2, 0.0),
            _score(EvaluationDimension.TECHNICAL_CLARITY, 4, 0.0),
        ]
        assert synthesize(scores) == 3.0

    def test_confidence_weighted_mean(self):
        scores = [
            _score(EvaluationDimension.TASK_COMPLETION, 5, 1.0),
            _score(EvaluationDimension.TECHNICAL_CLARITY, 1, 0.0),
        ]
        # Only the confident 5 carries weight.
        assert synthesize(scores) == 5.0

    def test_equal_confidence_is_plain_mean(self):
        scores = [
            _score(EvaluationDimension.TASK_COMPLETION, 2, 0.5),
            _score(EvaluationDimension.TECHNICAL_CLARITY, 4, 0.5),
        ]
        assert synthesize(scores) == 3.0


class TestSwarmPipeline:
    """End-to-end swarm behavior."""

    def test_llm_mode_produces_full_result(self):
        swarm = EvaluationSwarm(client=_FullStub(score=4))
        result = swarm.evaluate(_scenario(), "Book me a flight to Chicago.")
        assert len(result.agent_scores) == 5
        assert result.degraded is False
        assert result.synthesized_score == 4.0
        assert result.agent_response.strip() != ""

    def test_all_five_dimensions_scored(self):
        swarm = EvaluationSwarm(client=_FullStub())
        result = swarm.evaluate(_scenario(), "Book a flight.")
        dims = {s.dimension for s in result.agent_scores}
        assert dims == set(EvaluationDimension)

    def test_degraded_mode_still_complete(self):
        swarm = EvaluationSwarm(client=NullLLMClient())
        result = swarm.evaluate(_scenario(), "Book a flight to Chicago.")
        assert len(result.agent_scores) == 5
        assert result.degraded is True
        assert 1.0 <= result.synthesized_score <= 5.0
        assert result.agent_response.strip() != ""

    def test_available_reflects_client(self):
        assert EvaluationSwarm(client=_FullStub()).available is True
        assert EvaluationSwarm(client=NullLLMClient()).available is False

    def test_explicit_ids_and_model_name_used(self):
        swarm = EvaluationSwarm(client=_FullStub())
        result = swarm.evaluate(
            _scenario(),
            "Book a flight.",
            model_name="whisper+claude",
            audio_file_id="aud_123",
            result_id="eval_fixed",
        )
        assert result.id == "eval_fixed"
        assert result.model_name == "whisper+claude"
        assert result.audio_file_id == "aud_123"

    def test_generates_unique_ids(self):
        swarm = EvaluationSwarm(client=_FullStub())
        a = swarm.evaluate(_scenario(), "Book a flight.")
        b = swarm.evaluate(_scenario(), "Book a flight.")
        assert a.id != b.id

    def test_scenario_id_recorded(self):
        swarm = EvaluationSwarm(client=NullLLMClient())
        result = swarm.evaluate(_scenario(), "Book a flight.")
        assert result.scenario_id == "travel_flight_booking"

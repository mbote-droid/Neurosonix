"""Tests for the five evaluator agents.

Covers the LLM structured-output path (faked), clamping of out-of-range
model output, and every deterministic heuristic fallback. No network.
"""

from agentic.llm_client import BaseLLMClient, NullLLMClient, LLMUnavailable
from agentic.evaluators import Evaluator, build_evaluators
from agentic.schemas import (
    Domain,
    EvaluationDimension,
    RolePlayResult,
    AgentScore,
)
from agentic import scenarios


class _JsonStub(BaseLLMClient):
    """Available client returning a canned JSON verdict."""

    available = True
    model = "stub"

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def complete_json(self, system, user, schema, max_tokens=1024):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return self._payload


class _FailJson(BaseLLMClient):
    available = True
    model = "fail"

    def complete_json(self, system, user, schema, max_tokens=1024):
        raise LLMUnavailable("outage")


def _scenario(domain=Domain.FINANCE):
    return scenarios.scenarios_for(domain)[0]


def _reply(text, transcript="I need help with a charge.", degraded=False):
    return RolePlayResult(
        scenario_id="x",
        transcript=transcript,
        agent_response=text,
        model_name="m",
        degraded=degraded,
    )


class TestEvaluatorLLMPath:
    """Structured-output scoring path."""

    def test_uses_llm_score(self):
        stub = _JsonStub({"score": 4, "rationale": "solid", "confidence": 0.9})
        ev = Evaluator(EvaluationDimension.TASK_COMPLETION, stub)
        s = ev.score(_scenario(), _reply("I can open that dispute now."))
        assert s.score == 4
        assert s.degraded is False
        assert s.rationale == "solid"

    def test_clamps_out_of_range_score(self):
        stub = _JsonStub({"score": 99, "rationale": "r", "confidence": 5})
        ev = Evaluator(EvaluationDimension.TASK_COMPLETION, stub)
        s = ev.score(_scenario(), _reply("ok"))
        assert s.score == 5
        assert s.confidence == 1.0

    def test_handles_non_numeric_score(self):
        stub = _JsonStub({"score": "n/a", "rationale": "r", "confidence": "x"})
        ev = Evaluator(EvaluationDimension.TASK_COMPLETION, stub)
        s = ev.score(_scenario(), _reply("ok"))
        assert 1 <= s.score <= 5
        assert 0.0 <= s.confidence <= 1.0

    def test_prompt_contains_rubric_anchors(self):
        stub = _JsonStub({"score": 3, "rationale": "r", "confidence": 0.5})
        ev = Evaluator(EvaluationDimension.TECHNICAL_CLARITY, stub)
        ev.score(_scenario(), _reply("Clear and concise."))
        system = stub.calls[0]["system"]
        assert "technical_clarity" in system
        assert "1:" in system and "5:" in system

    def test_falls_back_on_llm_error(self):
        ev = Evaluator(EvaluationDimension.TASK_COMPLETION, _FailJson())
        s = ev.score(_scenario(), _reply("I can help you with that."))
        assert s.degraded is True


class TestHeuristicFallbacks:
    """Deterministic offline scoring — one path per dimension."""

    def _null_eval(self, dim):
        return Evaluator(dim, NullLLMClient())

    def test_all_dimensions_return_valid_scores(self):
        rp = _reply("Thanks, I can help. Could you confirm the date?")
        for dim in EvaluationDimension:
            s = self._null_eval(dim).score(_scenario(), rp)
            assert isinstance(s, AgentScore)
            assert 1 <= s.score <= 5
            assert s.degraded is True

    def test_task_completion_rewards_action_language(self):
        ev = self._null_eval(EvaluationDimension.TASK_COMPLETION)
        strong = ev.score(_scenario(), _reply("I can open that dispute now."))
        weak = ev.score(_scenario(), _reply("Hmm."))
        assert strong.score > weak.score

    def test_naturalness_rewards_politeness(self):
        ev = self._null_eval(EvaluationDimension.CONVERSATIONAL_NATURALNESS)
        polite = ev.score(_scenario(), _reply("Thanks so much, happy to help!"))
        blunt = ev.score(_scenario(), _reply("No."))
        assert polite.score > blunt.score

    def test_audio_comprehension_rewards_overlap(self):
        ev = self._null_eval(EvaluationDimension.AUDIO_COMPREHENSION)
        on_topic = ev.score(
            _scenario(),
            _reply("I'll dispute that charge for you.",
                   transcript="Please dispute this charge."),
        )
        off_topic = ev.score(
            _scenario(),
            _reply("The weather is nice today.",
                   transcript="Please dispute this charge."),
        )
        assert on_topic.score >= off_topic.score

    def test_audio_comprehension_empty_transcript_is_low(self):
        ev = self._null_eval(EvaluationDimension.AUDIO_COMPREHENSION)
        s = ev.score(_scenario(), _reply("Anything.", transcript=""))
        assert s.score == 1

    def test_instruction_adherence_penalizes_violation(self):
        ev = self._null_eval(EvaluationDimension.INSTRUCTION_ADHERENCE)
        clean = ev.score(
            _scenario(Domain.FINANCE),
            _reply("I can help open a dispute."),
        )
        violating = ev.score(
            _scenario(Domain.FINANCE),
            _reply("You should invest in this stock for a guaranteed return."),
        )
        assert clean.score > violating.score

    def test_technical_clarity_penalizes_run_on(self):
        ev = self._null_eval(EvaluationDimension.TECHNICAL_CLARITY)
        clear = ev.score(_scenario(), _reply("I can help. What is the date?"))
        runon = ev.score(_scenario(), _reply(" ".join(["word"] * 60)))
        assert clear.score > runon.score


class TestBuildEvaluators:
    """The swarm factory."""

    def test_builds_five_evaluators_one_per_dimension(self):
        evs = build_evaluators(NullLLMClient())
        assert len(evs) == 5
        assert {e.dimension for e in evs} == set(EvaluationDimension)

    def test_each_evaluator_has_a_name(self):
        evs = build_evaluators(NullLLMClient())
        assert all(e.name.endswith("_evaluator") for e in evs)

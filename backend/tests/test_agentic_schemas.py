"""Tests for agentic evaluation data contracts.

Pure validation tests — no LLM, no I/O, fully deterministic.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from agentic.schemas import (
    Domain,
    EvaluationDimension,
    ScenarioTemplate,
    RubricCriterion,
    AgentScore,
    RolePlayResult,
    EvaluationResult,
    ModelComparison,
    ModelComparisonEntry,
    SCALE_MIN,
    SCALE_MAX,
)


class TestSchemas:
    """Test suite for agentic Pydantic models."""

    def test_domain_enum_values(self):
        """All four role-play domains are present."""
        assert {d.value for d in Domain} == {
            "finance",
            "healthcare",
            "bioinformatics",
            "travel",
        }

    def test_dimension_enum_has_five(self):
        """Exactly five evaluation dimensions — one per evaluator agent."""
        assert len(list(EvaluationDimension)) == 5

    def test_scenario_template_valid(self):
        """A well-formed scenario template constructs cleanly."""
        s = ScenarioTemplate(
            id="fin_001",
            domain=Domain.FINANCE,
            name="Card dispute",
            system_prompt="You are a banking support agent.",
            user_goal="Dispute a fraudulent charge.",
        )
        assert s.domain == Domain.FINANCE
        assert s.example_exchange is None

    def test_scenario_template_rejects_blank_fields(self):
        """Blank required strings are rejected, not silently accepted."""
        with pytest.raises(ValidationError):
            ScenarioTemplate(
                id="x",
                domain=Domain.TRAVEL,
                name="   ",
                system_prompt="prompt",
                user_goal="goal",
            )

    def test_scenario_template_strips_whitespace(self):
        """Leading/trailing whitespace is stripped from text fields."""
        s = ScenarioTemplate(
            id="  fin_002  ",
            domain=Domain.FINANCE,
            name="  Loan  ",
            system_prompt="  p  ",
            user_goal="  g  ",
        )
        assert s.id == "fin_002"
        assert s.name == "Loan"

    def test_rubric_criterion_defaults(self):
        """Rubric criterion defaults to the shared 1..5 scale."""
        r = RubricCriterion(
            dimension=EvaluationDimension.TASK_COMPLETION,
            description="Did the agent complete the task?",
        )
        assert r.scale_min == SCALE_MIN
        assert r.scale_max == SCALE_MAX
        assert r.anchors == {}

    def test_rubric_criterion_rejects_bad_scale(self):
        """scale_max must exceed scale_min."""
        with pytest.raises(ValidationError):
            RubricCriterion(
                dimension=EvaluationDimension.TASK_COMPLETION,
                description="d",
                scale_min=5,
                scale_max=5,
            )

    def test_rubric_criterion_anchors(self):
        """Anchors map integer scores to descriptions."""
        r = RubricCriterion(
            dimension=EvaluationDimension.TECHNICAL_CLARITY,
            description="d",
            anchors={1: "unclear", 5: "crystal clear"},
        )
        assert r.anchors[5] == "crystal clear"

    def test_agent_score_valid(self):
        """A valid agent score constructs with rationale and confidence."""
        a = AgentScore(
            dimension=EvaluationDimension.AUDIO_COMPREHENSION,
            score=4,
            rationale="Understood the request well.",
            confidence=0.8,
        )
        assert a.score == 4
        assert a.degraded is False

    def test_agent_score_rejects_out_of_range(self):
        """Scores outside 1..5 are rejected."""
        with pytest.raises(ValidationError):
            AgentScore(dimension=EvaluationDimension.TASK_COMPLETION, score=6)
        with pytest.raises(ValidationError):
            AgentScore(dimension=EvaluationDimension.TASK_COMPLETION, score=0)

    def test_agent_score_rejects_bad_confidence(self):
        """Confidence must be within 0.0..1.0."""
        with pytest.raises(ValidationError):
            AgentScore(
                dimension=EvaluationDimension.TASK_COMPLETION,
                score=3,
                confidence=1.5,
            )

    def test_roleplay_result(self):
        """Role-play result carries transcript, response, and degraded flag."""
        r = RolePlayResult(
            scenario_id="fin_001",
            transcript="I want to dispute a charge.",
            agent_response="I can help with that.",
            model_name="claude-opus-4-8",
        )
        assert r.degraded is False

    def test_evaluation_result_score_for(self):
        """score_for returns the matching dimension score, or None."""
        result = EvaluationResult(
            id="eval_1",
            scenario_id="fin_001",
            model_name="test",
            transcript="t",
            agent_response="r",
            agent_scores=[
                AgentScore(dimension=EvaluationDimension.TASK_COMPLETION, score=5),
            ],
        )
        got = result.score_for(EvaluationDimension.TASK_COMPLETION)
        assert got is not None and got.score == 5
        assert result.score_for(EvaluationDimension.TECHNICAL_CLARITY) is None

    def test_evaluation_result_clamps_synthesized_score(self):
        """Out-of-range synthesized scores are clamped, not rejected."""
        high = EvaluationResult(
            id="e", scenario_id="s", model_name="m",
            transcript="t", agent_response="r", synthesized_score=99.0,
        )
        low = EvaluationResult(
            id="e", scenario_id="s", model_name="m",
            transcript="t", agent_response="r", synthesized_score=-4.0,
        )
        assert high.synthesized_score == float(SCALE_MAX)
        assert low.synthesized_score == float(SCALE_MIN)

    def test_evaluation_result_defaults(self):
        """Timestamp and empty score list are auto-populated."""
        result = EvaluationResult(
            id="e", scenario_id="s", model_name="m",
            transcript="t", agent_response="r",
        )
        assert isinstance(result.created_at, datetime)
        assert result.agent_scores == []

    def test_model_comparison(self):
        """Model comparison holds entries and an optional winner."""
        comp = ModelComparison(
            id="cmp_1",
            scenario_id="fin_001",
            transcript="t",
            entries=[
                ModelComparisonEntry(model_name="a", synthesized_score=4.2),
                ModelComparisonEntry(model_name="b", synthesized_score=3.1),
            ],
            winner="a",
        )
        assert len(comp.entries) == 2
        assert comp.winner == "a"

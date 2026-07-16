"""Tests for the model comparison engine.

Uses a scripted stub that scores by transcript content so winner selection is
deterministic. No network.
"""

from agentic.llm_client import BaseLLMClient, NullLLMClient
from agentic.comparison import ModelComparator
from agentic.schemas import EvaluationDimension
from agentic import scenarios


class _ContentScoredStub(BaseLLMClient):
    """Scores high when the transcript contains the word 'good', else low."""

    available = True
    model = "content-stub"

    def complete_text(self, system, user, max_tokens=1024):
        return f"Reply to: {user}"

    def complete_json(self, system, user, schema, max_tokens=1024):
        score = 5 if "good" in user.lower() else 2
        return {"score": score, "rationale": "scripted", "confidence": 0.9}


def _scenario():
    return scenarios.scenario_by_id("health_appointment")


class TestModelComparator:
    """Test suite for ModelComparator."""

    def test_compares_two_models(self):
        comp, results = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(),
            {"whisper": "good transcript", "gemini": "bad transcript"},
        )
        assert len(comp.entries) == 2
        assert len(results) == 2

    def test_winner_is_higher_scorer(self):
        comp, _ = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(),
            {"whisper": "a good clear request", "gemini": "muddled request"},
        )
        assert comp.winner == "whisper"

    def test_entries_carry_per_dimension_scores(self):
        comp, _ = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(), {"whisper": "good"}
        )
        entry = comp.entries[0]
        assert set(entry.per_dimension.keys()) == set(EvaluationDimension)

    def test_entries_carry_transcript(self):
        comp, _ = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(), {"whisper": "good transcript here"}
        )
        assert comp.entries[0].transcript == "good transcript here"

    def test_empty_input_yields_empty_comparison(self):
        comp, results = ModelComparator(client=NullLLMClient()).compare(
            _scenario(), {}
        )
        assert comp.entries == []
        assert comp.winner is None
        assert results == []

    def test_tie_breaks_to_first_model(self):
        # Both transcripts are 'bad' -> equal scores; first inserted wins.
        comp, _ = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(),
            {"model_a": "plain request", "model_b": "plain request"},
        )
        assert comp.winner == "model_a"

    def test_results_have_model_names(self):
        _, results = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(), {"whisper": "good", "gemini": "bad"}
        )
        assert {r.model_name for r in results} == {"whisper", "gemini"}

    def test_degraded_mode_still_ranks(self):
        comp, _ = ModelComparator(client=NullLLMClient()).compare(
            _scenario(),
            {"whisper": "Book an appointment please", "gemini": ""},
        )
        assert comp.winner is not None
        assert len(comp.entries) == 2

    def test_explicit_comparison_id(self):
        comp, _ = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(), {"whisper": "good"}, comparison_id="cmp_fixed"
        )
        assert comp.id == "cmp_fixed"

    def test_audio_file_id_propagates(self):
        comp, results = ModelComparator(client=_ContentScoredStub()).compare(
            _scenario(), {"whisper": "good"}, audio_file_id="aud_9"
        )
        assert comp.audio_file_id == "aud_9"
        assert results[0].audio_file_id == "aud_9"

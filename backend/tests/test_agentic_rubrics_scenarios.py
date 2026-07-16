"""Tests for the rubric engine and scenario libraries.

Pure data/logic tests — no LLM, no I/O.
"""

from agentic.schemas import Domain, EvaluationDimension
from agentic import rubrics, scenarios


class TestRubrics:
    """Test suite for the rubric engine."""

    def test_every_dimension_has_a_rubric(self):
        """One rubric per evaluation dimension — full coverage."""
        covered = {r.dimension for r in rubrics.all_rubrics()}
        assert covered == set(EvaluationDimension)

    def test_all_rubrics_count(self):
        """Exactly five rubrics, matching the five agents."""
        assert len(rubrics.all_rubrics()) == 5

    def test_rubric_for_returns_matching_dimension(self):
        """rubric_for returns the criterion for the requested dimension."""
        r = rubrics.rubric_for(EvaluationDimension.TASK_COMPLETION)
        assert r.dimension == EvaluationDimension.TASK_COMPLETION

    def test_every_rubric_has_full_1_to_5_anchors(self):
        """Each rubric anchors all five score points."""
        for r in rubrics.all_rubrics():
            assert set(r.anchors.keys()) == {1, 2, 3, 4, 5}, r.dimension

    def test_anchor_text_is_ordered_and_nonempty(self):
        """anchor_text renders anchors 1..5 in order as a prompt block."""
        text = rubrics.anchor_text(EvaluationDimension.TECHNICAL_CLARITY)
        assert text.startswith("1:")
        assert "5:" in text
        # Five lines, one per anchor.
        assert len(text.splitlines()) == 5

    def test_all_rubrics_returns_a_copy(self):
        """Mutating the returned list must not corrupt the module state."""
        first = rubrics.all_rubrics()
        first.clear()
        assert len(rubrics.all_rubrics()) == 5


class TestScenarios:
    """Test suite for the scenario libraries."""

    def test_all_four_domains_present(self):
        """Every domain has at least one scenario."""
        domains = {s.domain for s in scenarios.all_scenarios()}
        assert domains == set(Domain)

    def test_each_domain_has_scenarios(self):
        """scenarios_for returns a non-empty list for each domain."""
        for domain in Domain:
            got = scenarios.scenarios_for(domain)
            assert len(got) >= 1, domain
            assert all(s.domain == domain for s in got)

    def test_scenario_ids_are_unique(self):
        """No two scenarios share an id."""
        ids = [s.id for s in scenarios.all_scenarios()]
        assert len(ids) == len(set(ids))

    def test_scenario_by_id_found(self):
        """A known id resolves to its scenario."""
        s = scenarios.scenario_by_id("bio_variant_lookup")
        assert s is not None
        assert s.domain == Domain.BIOINFORMATICS

    def test_scenario_by_id_unknown_returns_none(self):
        """An unknown id returns None rather than raising (safe default)."""
        assert scenarios.scenario_by_id("does_not_exist") is None

    def test_every_scenario_has_system_prompt_and_goal(self):
        """Each scenario carries a usable persona prompt and user goal."""
        for s in scenarios.all_scenarios():
            assert s.system_prompt.strip()
            assert s.user_goal.strip()

    def test_all_scenarios_returns_a_copy(self):
        """Mutating the returned list must not corrupt module state."""
        first = scenarios.all_scenarios()
        n = len(first)
        first.clear()
        assert len(scenarios.all_scenarios()) == n

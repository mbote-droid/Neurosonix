"""Tests for evaluation/comparison persistence.

Uses an in-memory SQLite database — hermetic, no shared state, no network.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from agentic import store
from agentic.schemas import (
    AgentScore,
    EvaluationDimension,
    EvaluationResult,
    ModelComparison,
    ModelComparisonEntry,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _result(rid="e1", score=4.0, when=None, degraded=False):
    return EvaluationResult(
        id=rid,
        scenario_id="fin_card_dispute",
        model_name="claude-opus-4-8",
        transcript="dispute a charge",
        agent_response="I can help with that.",
        agent_scores=[
            AgentScore(dimension=EvaluationDimension.TASK_COMPLETION, score=4),
            AgentScore(dimension=EvaluationDimension.TECHNICAL_CLARITY, score=5),
        ],
        synthesized_score=score,
        degraded=degraded,
        created_at=when or datetime.utcnow(),
    )


def _comparison(cid="c1"):
    return ModelComparison(
        id=cid,
        scenario_id="travel_flight_booking",
        entries=[
            ModelComparisonEntry(model_name="whisper", synthesized_score=4.2),
            ModelComparisonEntry(model_name="gemini", synthesized_score=3.1),
        ],
        winner="whisper",
    )


class TestEvaluationPersistence:
    def test_save_and_get(self, db):
        assert store.save_evaluation(db, _result("e1")) is True
        got = store.get_evaluation(db, "e1")
        assert got is not None
        assert got.id == "e1"
        assert got.synthesized_score == 4.0

    def test_agent_scores_roundtrip(self, db):
        store.save_evaluation(db, _result("e2"))
        got = store.get_evaluation(db, "e2")
        assert len(got.agent_scores) == 2
        dims = {s.dimension for s in got.agent_scores}
        assert EvaluationDimension.TASK_COMPLETION in dims

    def test_degraded_flag_persists(self, db):
        store.save_evaluation(db, _result("e3", degraded=True))
        assert store.get_evaluation(db, "e3").degraded is True

    def test_get_unknown_returns_none(self, db):
        assert store.get_evaluation(db, "missing") is None

    def test_save_is_idempotent(self, db):
        store.save_evaluation(db, _result("dup"))
        store.save_evaluation(db, _result("dup", score=2.0))
        rows = store.list_evaluations(db)
        assert len([r for r in rows if r.id == "dup"]) == 1
        assert store.get_evaluation(db, "dup").synthesized_score == 2.0

    def test_list_newest_first(self, db):
        base = datetime(2026, 1, 1, 12, 0, 0)
        store.save_evaluation(db, _result("old", when=base))
        store.save_evaluation(
            db, _result("new", when=base + timedelta(hours=1))
        )
        ids = [r.id for r in store.list_evaluations(db)]
        assert ids.index("new") < ids.index("old")

    def test_list_respects_limit(self, db):
        base = datetime(2026, 1, 1)
        for i in range(5):
            store.save_evaluation(
                db, _result(f"e{i}", when=base + timedelta(minutes=i))
            )
        assert len(store.list_evaluations(db, limit=3)) == 3


class TestComparisonPersistence:
    def test_save_and_list(self, db):
        assert store.save_comparison(db, _comparison("c1")) is True
        rows = store.list_comparisons(db)
        assert len(rows) == 1
        assert rows[0].winner == "whisper"

    def test_entries_roundtrip(self, db):
        store.save_comparison(db, _comparison("c2"))
        comp = store.list_comparisons(db)[0]
        assert len(comp.entries) == 2
        assert {e.model_name for e in comp.entries} == {"whisper", "gemini"}

    def test_comparison_idempotent(self, db):
        store.save_comparison(db, _comparison("dup"))
        store.save_comparison(db, _comparison("dup"))
        assert len(store.list_comparisons(db)) == 1

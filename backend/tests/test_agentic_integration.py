"""End-to-end integration test for the agentic evaluation flow.

Drives the real route handlers, swarm, and persistence layer together against
an in-memory database, in offline (deterministic) mode — no LLM, no network.
Covers the full path: evaluate -> persist -> retrieve -> compare -> history.
"""

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from routes import evaluate as ev
from agentic.swarm import EvaluationSwarm
from agentic.comparison import ModelComparator
from agentic.llm_client import NullLLMClient
from agentic.schemas import EvaluationDimension


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def swarm():
    # Offline swarm — deterministic heuristic scoring, fully reproducible.
    return EvaluationSwarm(client=NullLLMClient())


class TestFullEvaluationJourney:
    def test_evaluate_persist_and_retrieve(self, swarm, db):
        # 1. Health reports degraded (offline).
        health = _run(ev.health(swarm))
        assert health.mode == "degraded"

        # 2. Scenarios are available.
        scenarios = _run(ev.list_scenarios(domain=None))
        assert len(scenarios) >= 12
        scenario_id = scenarios[0].id

        # 3. Evaluate a transcript.
        req = ev.EvaluateRequest(
            scenario_id=scenario_id,
            transcript="I need to dispute a charge I do not recognize.",
            model_name="whisper+offline",
        )
        result = _run(ev.evaluate(req, swarm, db))
        assert len(result.agent_scores) == 5
        assert {s.dimension for s in result.agent_scores} == set(EvaluationDimension)
        assert 1.0 <= result.synthesized_score <= 5.0

        # 4. It is retrievable by id and appears in history.
        fetched = _run(ev.get_result(result.id, db))
        assert fetched.id == result.id
        assert fetched.model_name == "whisper+offline"
        history = _run(ev.list_results(limit=50, db=db))
        assert result.id in {r.id for r in history}

    def test_compare_persist_and_retrieve(self, swarm, db):
        scenario_id = "travel_flight_booking"
        req = ev.CompareRequest(
            scenario_id=scenario_id,
            model_transcripts={
                "whisper": "Book a round trip flight to Chicago next Friday.",
                "gemini": "book flight chicago friday",
            },
        )
        comparison = _run(ev.compare(req, ModelComparator(swarm=swarm), db))
        assert len(comparison.entries) == 2
        assert comparison.winner in {"whisper", "gemini"}

        # Persisted and retrievable via history.
        history = _run(ev.list_comparisons_endpoint(limit=50, db=db))
        assert comparison.id in {c.id for c in history}
        stored = history[0]
        assert len(stored.entries) == 2

    def test_history_is_ordered_and_isolated(self, swarm, db):
        # Two evaluations; both persist and both appear.
        ids = []
        for text in ["dispute a charge", "check my balance transfer options"]:
            req = ev.EvaluateRequest(
                scenario_id="fin_card_dispute", transcript=text
            )
            ids.append(_run(ev.evaluate(req, swarm, db)).id)
        history = _run(ev.list_results(limit=50, db=db))
        stored_ids = {r.id for r in history}
        assert set(ids).issubset(stored_ids)

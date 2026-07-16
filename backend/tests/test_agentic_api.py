"""Tests for the evaluation API layer.

The endpoints are async functions with dependency-injected swarm/comparator, so
they are invoked directly with an offline or stubbed swarm — no ASGI stack, no
httpx, no live LLM required. FastAPI's own request validation is framework
behavior and is out of scope here.
"""

import asyncio
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from routes import evaluate as ev
from agentic.swarm import EvaluationSwarm
from agentic.comparison import ModelComparator
from agentic.llm_client import BaseLLMClient, NullLLMClient
from agentic.schemas import Domain


class _FullStub(BaseLLMClient):
    available = True
    model = "stub-model"

    def complete_text(self, system, user, max_tokens=1024):
        return "I can help you with that."

    def complete_json(self, system, user, schema, max_tokens=1024):
        return {"score": 4, "rationale": "ok", "confidence": 0.8}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def llm_swarm():
    return EvaluationSwarm(client=_FullStub())


@pytest.fixture
def offline_swarm():
    return EvaluationSwarm(client=NullLLMClient())


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class TestHealth:
    def test_health_degraded(self, offline_swarm):
        body = _run(ev.health(offline_swarm))
        assert body.llm_available is False
        assert body.mode == "degraded"
        assert body.dimensions == 5
        assert body.scenarios > 0

    def test_health_llm_mode(self, llm_swarm):
        body = _run(ev.health(llm_swarm))
        assert body.llm_available is True
        assert body.mode == "llm"


class TestReadEndpoints:
    def test_list_all_scenarios(self):
        got = _run(ev.list_scenarios(domain=None))
        assert len(got) >= 12

    def test_list_scenarios_by_domain(self):
        got = _run(ev.list_scenarios(domain=Domain.FINANCE))
        assert got and all(s.domain == Domain.FINANCE for s in got)

    def test_list_rubrics(self):
        got = _run(ev.list_rubrics())
        assert len(got) == 5


class TestEvaluateEndpoint:
    def test_evaluate_ok(self, llm_swarm, db):
        req = ev.EvaluateRequest(
            scenario_id="fin_card_dispute",
            transcript="I want to dispute a charge.",
        )
        result = _run(ev.evaluate(req, llm_swarm, db))
        assert len(result.agent_scores) == 5
        assert result.degraded is False

    def test_evaluate_degraded(self, offline_swarm, db):
        req = ev.EvaluateRequest(
            scenario_id="fin_card_dispute",
            transcript="I want to dispute a charge.",
        )
        result = _run(ev.evaluate(req, offline_swarm, db))
        assert result.degraded is True

    def test_evaluate_unknown_scenario_404(self, llm_swarm, db):
        req = ev.EvaluateRequest(scenario_id="nope", transcript="hi")
        with pytest.raises(HTTPException) as exc:
            _run(ev.evaluate(req, llm_swarm, db))
        assert exc.value.status_code == 404

    def test_evaluate_persists_result(self, llm_swarm, db):
        req = ev.EvaluateRequest(
            scenario_id="fin_card_dispute", transcript="Dispute a charge."
        )
        result = _run(ev.evaluate(req, llm_swarm, db))
        # It should now be retrievable via the history endpoints.
        fetched = _run(ev.get_result(result.id, db))
        assert fetched.id == result.id
        listed = _run(ev.list_results(limit=10, db=db))
        assert any(r.id == result.id for r in listed)

    def test_get_unknown_result_404(self, db):
        with pytest.raises(HTTPException) as exc:
            _run(ev.get_result("missing", db))
        assert exc.value.status_code == 404


class TestCompareEndpoint:
    def test_compare_ok(self, llm_swarm, db):
        req = ev.CompareRequest(
            scenario_id="travel_flight_booking",
            model_transcripts={
                "whisper": "Book a flight to Chicago.",
                "gemini": "Book flight Chicago.",
            },
        )
        comp = _run(ev.compare(req, ModelComparator(swarm=llm_swarm), db))
        assert len(comp.entries) == 2
        assert comp.winner in {"whisper", "gemini"}

    def test_compare_unknown_scenario_404(self, llm_swarm, db):
        req = ev.CompareRequest(
            scenario_id="nope", model_transcripts={"a": "x"}
        )
        with pytest.raises(HTTPException) as exc:
            _run(ev.compare(req, ModelComparator(swarm=llm_swarm), db))
        assert exc.value.status_code == 404

    def test_compare_empty_transcripts_400(self, llm_swarm, db):
        req = ev.CompareRequest(
            scenario_id="travel_flight_booking", model_transcripts={}
        )
        with pytest.raises(HTTPException) as exc:
            _run(ev.compare(req, ModelComparator(swarm=llm_swarm), db))
        assert exc.value.status_code == 400

    def test_compare_persists(self, llm_swarm, db):
        req = ev.CompareRequest(
            scenario_id="travel_flight_booking",
            model_transcripts={"whisper": "Book a flight.", "gemini": "Flight."},
        )
        _run(ev.compare(req, ModelComparator(swarm=llm_swarm), db))
        listed = _run(ev.list_comparisons_endpoint(limit=10, db=db))
        assert len(listed) == 1
        assert listed[0].winner in {"whisper", "gemini"}

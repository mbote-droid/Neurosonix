"""API surface for the agentic evaluation subsystem.

Endpoints (prefix ``/api/evaluate``):
  GET  /scenarios          list role-play scenarios (optionally by domain)
  GET  /rubrics            list scoring rubrics
  GET  /health             report LLM availability (honest degraded status)
  POST /                   evaluate a transcript under a scenario
  POST /compare            compare two or more models on the same scenario

The swarm and comparator are provided via FastAPI dependencies so tests can
inject a deterministic, offline stub.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from agentic import rubrics as rubric_engine
from agentic import scenarios as scenario_lib
from agentic.comparison import ModelComparator
from agentic.schemas import (
    Domain,
    EvaluationResult,
    ModelComparison,
    RubricCriterion,
    ScenarioTemplate,
)
from agentic.swarm import EvaluationSwarm

router = APIRouter(prefix="/api/evaluate", tags=["evaluation"])


# --------------------------------------------------------------------------- #
# Dependencies (lazily constructed singletons; overridable in tests)
# --------------------------------------------------------------------------- #
_swarm_singleton: Optional[EvaluationSwarm] = None


def get_swarm() -> EvaluationSwarm:
    """Return the process-wide evaluation swarm, building it on first use."""
    global _swarm_singleton
    if _swarm_singleton is None:
        _swarm_singleton = EvaluationSwarm()
    return _swarm_singleton


def get_comparator(swarm: EvaluationSwarm = Depends(get_swarm)) -> ModelComparator:
    """Return a comparator backed by the shared swarm."""
    return ModelComparator(swarm=swarm)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class EvaluateRequest(BaseModel):
    scenario_id: str
    transcript: str
    model_name: Optional[str] = None
    audio_file_id: Optional[str] = None


class CompareRequest(BaseModel):
    scenario_id: str
    # model name -> that model's transcript of the same audio
    model_transcripts: Dict[str, str] = Field(default_factory=dict)
    audio_file_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    mode: str
    scenarios: int
    dimensions: int


# --------------------------------------------------------------------------- #
# Read endpoints
# --------------------------------------------------------------------------- #
@router.get("/health", response_model=HealthResponse)
async def health(swarm: EvaluationSwarm = Depends(get_swarm)) -> HealthResponse:
    """Report subsystem health and whether a live LLM is backing it."""
    return HealthResponse(
        status="ok",
        llm_available=swarm.available,
        mode="llm" if swarm.available else "degraded",
        scenarios=len(scenario_lib.all_scenarios()),
        dimensions=len(rubric_engine.all_rubrics()),
    )


@router.get("/scenarios", response_model=List[ScenarioTemplate])
async def list_scenarios(
    domain: Optional[Domain] = Query(default=None),
) -> List[ScenarioTemplate]:
    """List role-play scenarios, optionally filtered by domain."""
    if domain is not None:
        return scenario_lib.scenarios_for(domain)
    return scenario_lib.all_scenarios()


@router.get("/rubrics", response_model=List[RubricCriterion])
async def list_rubrics() -> List[RubricCriterion]:
    """List the scoring rubric for every evaluation dimension."""
    return rubric_engine.all_rubrics()


# --------------------------------------------------------------------------- #
# Action endpoints
# --------------------------------------------------------------------------- #
@router.post("/", response_model=EvaluationResult)
async def evaluate(
    req: EvaluateRequest,
    swarm: EvaluationSwarm = Depends(get_swarm),
) -> EvaluationResult:
    """Evaluate a transcript under a scenario with the five-agent swarm."""
    scenario = scenario_lib.scenario_by_id(req.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario_id")
    try:
        return swarm.evaluate(
            scenario,
            req.transcript,
            model_name=req.model_name,
            audio_file_id=req.audio_file_id,
        )
    except Exception as e:  # pragma: no cover - swarm is designed not to raise
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail="Evaluation failed")


@router.post("/compare", response_model=ModelComparison)
async def compare(
    req: CompareRequest,
    comparator: ModelComparator = Depends(get_comparator),
) -> ModelComparison:
    """Compare two or more models' transcripts on the same scenario."""
    scenario = scenario_lib.scenario_by_id(req.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario_id")
    if not req.model_transcripts:
        raise HTTPException(
            status_code=400, detail="Provide at least one model transcript"
        )
    try:
        comparison, _ = comparator.compare(
            scenario,
            req.model_transcripts,
            audio_file_id=req.audio_file_id,
        )
        return comparison
    except Exception as e:  # pragma: no cover
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Comparison failed")

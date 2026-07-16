"""Persistence for evaluation and comparison results.

Stores completed :class:`EvaluationResult` and :class:`ModelComparison` records
in the app's SQLite database so benchmarks survive restarts and can be listed
or exported. Saves are best-effort: a persistence failure is logged and
swallowed so it never breaks an evaluation request (build rule #4).

Uses SQLAlchemy models alongside the existing ``AudioFile`` model and the
shared ``Base``/session, keeping one database and one migration surface.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from loguru import logger
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, desc
from sqlalchemy.orm import Session

from models import Base  # shared declarative base (backend/models.py)
from agentic.schemas import EvaluationResult, ModelComparison


class EvaluationRecord(Base):
    """Persisted evaluation result."""

    __tablename__ = "evaluation_results"

    id = Column(String, primary_key=True)
    scenario_id = Column(String, nullable=False)
    model_name = Column(String)
    transcript = Column(String)
    agent_response = Column(String)
    synthesized_score = Column(Float)
    degraded = Column(Boolean, default=False)
    audio_file_id = Column(String, nullable=True)
    agent_scores = Column(JSON)  # list of AgentScore dicts
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_result(self) -> EvaluationResult:
        """Rehydrate a Pydantic EvaluationResult from the row."""
        return EvaluationResult(
            id=self.id,
            scenario_id=self.scenario_id,
            model_name=self.model_name or "",
            transcript=self.transcript or "",
            agent_response=self.agent_response or "",
            agent_scores=self.agent_scores or [],
            synthesized_score=self.synthesized_score or 0.0,
            audio_file_id=self.audio_file_id,
            degraded=bool(self.degraded),
            created_at=self.created_at or datetime.utcnow(),
        )


class ComparisonRecord(Base):
    """Persisted model comparison."""

    __tablename__ = "model_comparisons"

    id = Column(String, primary_key=True)
    scenario_id = Column(String, nullable=False)
    winner = Column(String, nullable=True)
    audio_file_id = Column(String, nullable=True)
    entries = Column(JSON)  # list of ModelComparisonEntry dicts
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_comparison(self) -> ModelComparison:
        return ModelComparison(
            id=self.id,
            scenario_id=self.scenario_id,
            entries=self.entries or [],
            winner=self.winner,
            audio_file_id=self.audio_file_id,
            created_at=self.created_at or datetime.utcnow(),
        )


def _dump(model) -> dict:
    """Pydantic v2/v1-safe dict serialization (JSON-compatible)."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


def save_evaluation(db: Session, result: EvaluationResult) -> bool:
    """Persist an evaluation result. Returns True on success, False otherwise."""
    try:
        record = EvaluationRecord(
            id=result.id,
            scenario_id=result.scenario_id,
            model_name=result.model_name,
            transcript=result.transcript,
            agent_response=result.agent_response,
            synthesized_score=result.synthesized_score,
            degraded=result.degraded,
            audio_file_id=result.audio_file_id,
            agent_scores=[_dump(s) for s in result.agent_scores],
            created_at=result.created_at,
        )
        db.merge(record)  # idempotent on id
        db.commit()
        return True
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"Failed to persist evaluation {result.id}: {e}")
        db.rollback()
        return False


def save_comparison(db: Session, comparison: ModelComparison) -> bool:
    """Persist a model comparison. Returns True on success, False otherwise."""
    try:
        record = ComparisonRecord(
            id=comparison.id,
            scenario_id=comparison.scenario_id,
            winner=comparison.winner,
            audio_file_id=comparison.audio_file_id,
            entries=[_dump(e) for e in comparison.entries],
            created_at=comparison.created_at,
        )
        db.merge(record)
        db.commit()
        return True
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"Failed to persist comparison {comparison.id}: {e}")
        db.rollback()
        return False


def list_evaluations(db: Session, limit: int = 50) -> List[EvaluationResult]:
    """Return recent evaluations, newest first."""
    limit = max(1, min(500, limit))
    rows = (
        db.query(EvaluationRecord)
        .order_by(desc(EvaluationRecord.created_at))
        .limit(limit)
        .all()
    )
    return [r.to_result() for r in rows]


def get_evaluation(db: Session, result_id: str) -> Optional[EvaluationResult]:
    """Return one evaluation by id, or None."""
    row = db.query(EvaluationRecord).filter(EvaluationRecord.id == result_id).first()
    return row.to_result() if row else None


def list_comparisons(db: Session, limit: int = 50) -> List[ModelComparison]:
    """Return recent comparisons, newest first."""
    limit = max(1, min(500, limit))
    rows = (
        db.query(ComparisonRecord)
        .order_by(desc(ComparisonRecord.created_at))
        .limit(limit)
        .all()
    )
    return [r.to_comparison() for r in rows]

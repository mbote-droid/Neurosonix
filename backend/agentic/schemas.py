"""Data contracts for the agentic evaluation subsystem.

Pure Pydantic models with strict validation and safe defaults. These are the
shared vocabulary between the role-play agent, the evaluator swarm, the model
comparison engine, and the API/persistence layers. No side effects, no I/O.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class Domain(str, Enum):
    """Role-play scenario domains."""

    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    BIOINFORMATICS = "bioinformatics"
    TRAVEL = "travel"


class EvaluationDimension(str, Enum):
    """The five dimensions scored by the evaluator swarm.

    Each dimension maps to exactly one evaluator agent.
    """

    TASK_COMPLETION = "task_completion"
    CONVERSATIONAL_NATURALNESS = "conversational_naturalness"
    AUDIO_COMPREHENSION = "audio_comprehension"
    INSTRUCTION_ADHERENCE = "instruction_adherence"
    TECHNICAL_CLARITY = "technical_clarity"


# Likert scale bounds, shared across rubric criteria and agent scores.
SCALE_MIN = 1
SCALE_MAX = 5


class ScenarioTemplate(BaseModel):
    """A role-play scenario: the persona and goal the audio speaker embodies.

    The transcript of the user's audio is fed into an agent primed with this
    scenario's ``system_prompt``; the agent's reply is what the swarm scores.
    """

    id: str
    domain: Domain
    name: str
    system_prompt: str
    user_goal: str
    example_exchange: Optional[str] = None

    @field_validator("id", "name", "system_prompt", "user_goal")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class RubricCriterion(BaseModel):
    """Scoring rubric for a single evaluation dimension.

    ``anchors`` maps a score (1..5) to a plain-language description of what
    that score means, so evaluators (and humans) share a calibrated scale.
    """

    dimension: EvaluationDimension
    description: str
    scale_min: int = SCALE_MIN
    scale_max: int = SCALE_MAX
    anchors: Dict[int, str] = Field(default_factory=dict)

    @field_validator("scale_max")
    @classmethod
    def _max_gt_min(cls, v: int, info: ValidationInfo) -> int:
        lo = info.data.get("scale_min", SCALE_MIN)
        if v <= lo:
            raise ValueError("scale_max must be greater than scale_min")
        return v


class AgentScore(BaseModel):
    """One evaluator agent's verdict on one dimension."""

    dimension: EvaluationDimension
    score: int = Field(ge=SCALE_MIN, le=SCALE_MAX)
    rationale: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # True when produced by the deterministic fallback rather than an LLM.
    degraded: bool = False


class RolePlayResult(BaseModel):
    """Output of the role-play agent for one transcript under one scenario."""

    scenario_id: str
    transcript: str
    agent_response: str
    model_name: str
    degraded: bool = False


class EvaluationResult(BaseModel):
    """A complete evaluation: transcript -> agent response -> swarm scores."""

    id: str
    scenario_id: str
    model_name: str
    transcript: str
    agent_response: str
    agent_scores: List[AgentScore] = Field(default_factory=list)
    synthesized_score: float = 0.0
    audio_file_id: Optional[str] = None
    degraded: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("synthesized_score")
    @classmethod
    def _score_in_range(cls, v: float) -> float:
        # Clamp rather than reject: a safe default beats a crash (build rule #4).
        return max(float(SCALE_MIN), min(float(SCALE_MAX), v))

    def score_for(self, dimension: EvaluationDimension) -> Optional[AgentScore]:
        """Return the agent score for a dimension, or None if absent."""
        for s in self.agent_scores:
            if s.dimension == dimension:
                return s
        return None


class ModelComparisonEntry(BaseModel):
    """One model's result within a head-to-head comparison."""

    model_name: str
    synthesized_score: float
    transcript: str = ""
    per_dimension: Dict[EvaluationDimension, float] = Field(default_factory=dict)


class ModelComparison(BaseModel):
    """Head-to-head comparison of two or more models on the same input.

    Each model may yield a different transcript (e.g. Whisper vs Gemini), so
    per-model transcripts live on the entries; ``transcript`` is an optional
    overall note.
    """

    id: str
    scenario_id: str
    transcript: str = ""
    entries: List[ModelComparisonEntry] = Field(default_factory=list)
    winner: Optional[str] = None
    audio_file_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

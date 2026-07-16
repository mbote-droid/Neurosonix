"""The role-play agent: transcript in, agent reply out.

Given a scenario (persona + policies + goal) and the transcript of the caller's
audio, the agent produces the reply that the evaluator swarm will score. With a
live LLM it generates a real response; without one it returns a deterministic,
role-appropriate reply so the pipeline always yields something to evaluate
(build rule #4). The ``degraded`` flag records which path was taken (rule #3).
"""

from __future__ import annotations

from loguru import logger

from agentic.llm_client import BaseLLMClient, LLMUnavailable
from agentic.schemas import Domain, RolePlayResult, ScenarioTemplate


# Deterministic fallback openers per domain. These are genuine, role-appropriate
# replies (not placeholders) used when no LLM is available.
_FALLBACK_BY_DOMAIN = {
    Domain.FINANCE: (
        "Thanks for reaching out. I can help with that. To make sure I handle "
        "it correctly, could you confirm the key details so I can look into "
        "your account safely?"
    ),
    Domain.HEALTHCARE: (
        "Thanks for calling. I'd be glad to help with this. So I can point you "
        "to the right next step, could you share a little more detail? If this "
        "is an emergency, please contact emergency services right away."
    ),
    Domain.BIOINFORMATICS: (
        "Happy to help with that. For research use only: let me confirm the "
        "specifics so I can give you an accurate answer — which gene, variant, "
        "or dataset are you working with?"
    ),
    Domain.TRAVEL: (
        "Thanks for reaching out. I can help arrange that. Could you confirm "
        "the dates and any preferences or budget so I can find the best "
        "options before we confirm anything?"
    ),
}

_MAX_TRANSCRIPT_CHARS = 4000


class RolePlayAgent:
    """Produces an agent reply for a transcript under a given scenario."""

    def __init__(self, client: BaseLLMClient):
        self._client = client

    def _build_system(self, scenario: ScenarioTemplate) -> str:
        """Compose the agent system prompt from the scenario."""
        parts = [
            scenario.system_prompt,
            f"\nThe caller's goal in this conversation: {scenario.user_goal}",
            "\nRespond with a single, natural spoken-style reply as the agent. "
            "Do not narrate your reasoning; just reply as the agent would.",
        ]
        return "".join(parts)

    def _fallback_reply(self, scenario: ScenarioTemplate) -> str:
        """Deterministic, role-appropriate reply for the offline path."""
        return _FALLBACK_BY_DOMAIN.get(
            scenario.domain,
            "Thanks for reaching out. I can help with that — could you share "
            "a few more details so I can assist accurately?",
        )

    def respond(
        self, scenario: ScenarioTemplate, transcript: str
    ) -> RolePlayResult:
        """Generate the agent's reply to ``transcript`` under ``scenario``.

        Never raises and never returns an empty reply.
        """
        clean = (transcript or "").strip()
        if not clean:
            # No usable input: return a safe clarifying reply, marked degraded.
            logger.info("RolePlayAgent: empty transcript; using fallback")
            return RolePlayResult(
                scenario_id=scenario.id,
                transcript="",
                agent_response=(
                    "I'm sorry, I didn't catch that. Could you say it again?"
                ),
                model_name=getattr(self._client, "model", "none"),
                degraded=True,
            )

        clean = clean[:_MAX_TRANSCRIPT_CHARS]

        if self._client.available:
            try:
                reply = self._client.complete_text(
                    system=self._build_system(scenario),
                    user=clean,
                    max_tokens=512,
                )
                return RolePlayResult(
                    scenario_id=scenario.id,
                    transcript=clean,
                    agent_response=reply,
                    model_name=self._client.model,
                    degraded=False,
                )
            except LLMUnavailable as e:
                logger.warning(f"RolePlayAgent: LLM failed ({e}); using fallback")

        return RolePlayResult(
            scenario_id=scenario.id,
            transcript=clean,
            agent_response=self._fallback_reply(scenario),
            model_name=getattr(self._client, "model", "none"),
            degraded=True,
        )

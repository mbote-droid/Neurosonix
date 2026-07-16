"""Tests for the role-play agent.

The LLM is faked; the deterministic fallback path is exercised with the
NullLLMClient. No network, no live model.
"""

from agentic.llm_client import BaseLLMClient, NullLLMClient, LLMUnavailable
from agentic.roleplay import RolePlayAgent
from agentic.schemas import Domain
from agentic import scenarios


# --------------------------------------------------------------------------- #
# LLM client doubles
# --------------------------------------------------------------------------- #
class _StubClient(BaseLLMClient):
    """Available client that returns a canned reply and records calls."""

    available = True
    model = "stub-model"

    def __init__(self, reply="Sure, I can help with that."):
        self._reply = reply
        self.text_calls = []

    def complete_text(self, system, user, max_tokens=1024):
        self.text_calls.append({"system": system, "user": user})
        return self._reply


class _FailingClient(BaseLLMClient):
    """Available client whose calls always fail — forces the fallback path."""

    available = True
    model = "failing-model"

    def complete_text(self, system, user, max_tokens=1024):
        raise LLMUnavailable("simulated outage")


def _a_scenario():
    return scenarios.scenario_by_id("fin_card_dispute")


class TestRolePlayAgent:
    """Test suite for RolePlayAgent."""

    def test_uses_llm_reply_when_available(self):
        agent = RolePlayAgent(_StubClient(reply="Let me open that dispute."))
        result = agent.respond(_a_scenario(), "I see a charge I didn't make.")
        assert result.agent_response == "Let me open that dispute."
        assert result.degraded is False
        assert result.model_name == "stub-model"

    def test_system_prompt_includes_scenario_and_goal(self):
        stub = _StubClient()
        agent = RolePlayAgent(stub)
        scenario = _a_scenario()
        agent.respond(scenario, "Hello")
        sent_system = stub.text_calls[0]["system"]
        assert scenario.system_prompt in sent_system
        assert scenario.user_goal in sent_system

    def test_transcript_passed_as_user_turn(self):
        stub = _StubClient()
        agent = RolePlayAgent(stub)
        agent.respond(_a_scenario(), "  Dispute a charge  ")
        assert stub.text_calls[0]["user"] == "Dispute a charge"

    def test_fallback_when_client_unavailable(self):
        agent = RolePlayAgent(NullLLMClient())
        result = agent.respond(_a_scenario(), "Help me dispute a charge.")
        assert result.degraded is True
        assert result.agent_response.strip() != ""

    def test_fallback_when_llm_errors(self):
        agent = RolePlayAgent(_FailingClient())
        result = agent.respond(_a_scenario(), "Help me dispute a charge.")
        assert result.degraded is True
        assert result.agent_response.strip() != ""

    def test_empty_transcript_yields_clarifying_reply(self):
        agent = RolePlayAgent(_StubClient())
        result = agent.respond(_a_scenario(), "   ")
        assert result.degraded is True
        assert result.transcript == ""
        assert result.agent_response.strip() != ""

    def test_fallback_reply_is_domain_appropriate(self):
        """Each domain has a distinct, non-empty fallback opener."""
        agent = RolePlayAgent(NullLLMClient())
        replies = {}
        for domain in Domain:
            scenario = scenarios.scenarios_for(domain)[0]
            result = agent.respond(scenario, "I need some help.")
            replies[domain] = result.agent_response
            assert result.agent_response.strip() != ""
        # Distinct openers across the four domains.
        assert len(set(replies.values())) == len(Domain)

    def test_healthcare_fallback_mentions_emergency_guidance(self):
        agent = RolePlayAgent(NullLLMClient())
        scenario = scenarios.scenarios_for(Domain.HEALTHCARE)[0]
        result = agent.respond(scenario, "I feel unwell.")
        assert "emergency" in result.agent_response.lower()

    def test_long_transcript_is_truncated(self):
        stub = _StubClient()
        agent = RolePlayAgent(stub)
        agent.respond(_a_scenario(), "x" * 10000)
        assert len(stub.text_calls[0]["user"]) <= 4000

    def test_result_carries_scenario_id(self):
        agent = RolePlayAgent(_StubClient())
        result = agent.respond(_a_scenario(), "Hello")
        assert result.scenario_id == "fin_card_dispute"

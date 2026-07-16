"""Tests for the provider-agnostic LLM client.

All LLM interaction is mocked via the ``_factory`` injection hook — no network,
no API key, no live model required (build rule #2).
"""

import json
import pytest

from agentic.llm_client import (
    AnthropicLLMClient,
    NullLLMClient,
    LLMUnavailable,
    get_default_client,
    DEFAULT_MODEL,
)


# --------------------------------------------------------------------------- #
# Fake Anthropic SDK doubles
# --------------------------------------------------------------------------- #
class _FakeBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.content = [_FakeBlock(text)]
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, response=None, error: Exception = None):
        self._response = response
        self._error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class _FakeSDK:
    def __init__(self, messages: _FakeMessages):
        self.messages = messages


def _client_with(response=None, error=None) -> AnthropicLLMClient:
    """Build an AnthropicLLMClient backed by a fake SDK."""
    messages = _FakeMessages(response=response, error=error)
    client = AnthropicLLMClient(_factory=lambda: _FakeSDK(messages))
    client._fake_messages = messages  # expose for assertions
    return client


class TestNullClient:
    """The offline provider is always unavailable and never raises on init."""

    def test_unavailable(self):
        assert NullLLMClient().available is False

    def test_complete_text_raises(self):
        with pytest.raises(LLMUnavailable):
            NullLLMClient().complete_text("s", "u")

    def test_complete_json_raises(self):
        with pytest.raises(LLMUnavailable):
            NullLLMClient().complete_json("s", "u", {})


class TestAnthropicClientAvailability:
    """Construction never performs network I/O and never raises."""

    def test_no_key_is_unavailable(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = AnthropicLLMClient()  # no factory, no key
        assert client.available is False

    def test_factory_makes_available(self):
        client = _client_with(response=_FakeResponse("hi"))
        assert client.available is True
        assert client.model == DEFAULT_MODEL


class TestCompleteText:
    """Free-text completion path."""

    def test_returns_text(self):
        client = _client_with(response=_FakeResponse("Hello there"))
        assert client.complete_text("sys", "user") == "Hello there"

    def test_sends_expected_request_shape(self):
        client = _client_with(response=_FakeResponse("ok"))
        client.complete_text("SYS", "USR", max_tokens=321)
        call = client._fake_messages.calls[0]
        assert call["model"] == DEFAULT_MODEL
        assert call["system"] == "SYS"
        assert call["max_tokens"] == 321
        assert call["messages"] == [{"role": "user", "content": "USR"}]

    def test_refusal_raises(self):
        client = _client_with(response=_FakeResponse("", stop_reason="refusal"))
        with pytest.raises(LLMUnavailable):
            client.complete_text("s", "u")

    def test_empty_completion_raises(self):
        client = _client_with(response=_FakeResponse("   "))
        with pytest.raises(LLMUnavailable):
            client.complete_text("s", "u")

    def test_api_error_becomes_unavailable(self):
        client = _client_with(error=RuntimeError("boom"))
        with pytest.raises(LLMUnavailable):
            client.complete_text("s", "u")


class TestCompleteJson:
    """Structured JSON completion path."""

    def test_returns_parsed_dict(self):
        payload = {"score": 4, "rationale": "good"}
        client = _client_with(response=_FakeResponse(json.dumps(payload)))
        assert client.complete_json("s", "u", {"type": "object"}) == payload

    def test_request_includes_output_config(self):
        client = _client_with(response=_FakeResponse('{"x": 1}'))
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        client.complete_json("s", "u", schema)
        call = client._fake_messages.calls[0]
        assert call["output_config"]["format"]["type"] == "json_schema"
        assert call["output_config"]["format"]["schema"] == schema

    def test_invalid_json_raises(self):
        client = _client_with(response=_FakeResponse("not json at all"))
        with pytest.raises(LLMUnavailable):
            client.complete_json("s", "u", {})

    def test_non_object_json_raises(self):
        client = _client_with(response=_FakeResponse("[1, 2, 3]"))
        with pytest.raises(LLMUnavailable):
            client.complete_json("s", "u", {})

    def test_refusal_raises(self):
        client = _client_with(response=_FakeResponse("{}", stop_reason="refusal"))
        with pytest.raises(LLMUnavailable):
            client.complete_json("s", "u", {})


class TestDefaultClient:
    """Environment-driven factory always returns a usable client."""

    def test_provider_none_returns_null(self, monkeypatch):
        monkeypatch.setenv("NEUROSONIX_LLM_PROVIDER", "none")
        assert isinstance(get_default_client(), NullLLMClient)

    def test_anthropic_without_key_degrades_to_null(self, monkeypatch):
        monkeypatch.setenv("NEUROSONIX_LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert isinstance(get_default_client(), NullLLMClient)

    def test_unknown_provider_returns_null(self, monkeypatch):
        monkeypatch.setenv("NEUROSONIX_LLM_PROVIDER", "acme-llm")
        assert isinstance(get_default_client(), NullLLMClient)

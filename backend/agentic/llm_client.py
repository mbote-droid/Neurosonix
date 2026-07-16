"""Provider-agnostic LLM client with graceful degradation.

The role-play agent and evaluator swarm talk to an LLM only through this
module. The primary provider is Anthropic (Claude) via the official SDK; when
no provider is configured — no API key, SDK not installed, or an API error —
the client reports itself unavailable and callers fall back to deterministic,
rule-based logic. This keeps the whole platform functional offline on
constrained hardware (build rules #4 and #6).

Design notes:
- ``complete_json`` uses Anthropic structured outputs (``output_config.format``)
  so scores are guaranteed parseable — no fragile string scraping.
- Construction never performs network I/O and never raises; availability is a
  best-effort signal (SDK importable + credential present).
- A ``_factory`` hook injects a fake SDK client in tests, so no live LLM is
  ever required to exercise the code paths (build rule #2).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 1024


class LLMUnavailable(RuntimeError):
    """Raised when a live LLM cannot service a request.

    Callers are expected to catch this and degrade to rule-based behavior.
    """


class BaseLLMClient:
    """Interface every LLM client implements."""

    available: bool = False
    model: str = ""

    def complete_text(
        self, system: str, user: str, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> str:
        """Return a free-text completion, or raise :class:`LLMUnavailable`."""
        raise LLMUnavailable("no LLM provider configured")

    def complete_json(
        self,
        system: str,
        user: str,
        schema: Dict[str, Any],
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Dict[str, Any]:
        """Return a schema-validated JSON object, or raise :class:`LLMUnavailable`."""
        raise LLMUnavailable("no LLM provider configured")


class NullLLMClient(BaseLLMClient):
    """The offline provider: always unavailable, never raises on construction."""

    available = False
    model = "none"


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic (Claude) provider via the official ``anthropic`` SDK."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        _factory: Optional[Callable[[], Any]] = None,
    ):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._factory = _factory
        self._client: Any = None
        self.available = self._init()

    def _init(self) -> bool:
        """Best-effort setup. Never raises; returns availability."""
        try:
            if self._factory is not None:
                # Test / custom injection path — no SDK or network required.
                self._client = self._factory()
                return self._client is not None
            # Honest gate: without a resolvable key we don't attempt calls and
            # let callers fall back deterministically.
            if not self._api_key:
                logger.info("Anthropic client: no API key; running degraded")
                return False
            import anthropic  # noqa: WPS433 (lazy import — optional dependency)

            self._client = anthropic.Anthropic(api_key=self._api_key)
            logger.info(f"Anthropic client ready (model={self.model})")
            return True
        except ImportError:
            logger.info("Anthropic SDK not installed; running degraded")
            return False
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Anthropic client init failed: {e}")
            return False

    def _create(self, **kwargs: Any) -> Any:
        """Single choke point for the SDK call, so it is easy to mock."""
        return self._client.messages.create(**kwargs)

    @staticmethod
    def _first_text(response: Any) -> str:
        """Extract the first text block from a Messages API response."""
        content: List[Any] = getattr(response, "content", []) or []
        for block in content:
            if getattr(block, "type", None) == "text":
                return getattr(block, "text", "") or ""
        return ""

    def complete_text(
        self, system: str, user: str, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> str:
        if not self.available:
            raise LLMUnavailable("Anthropic client unavailable")
        try:
            response = self._create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            if getattr(response, "stop_reason", None) == "refusal":
                raise LLMUnavailable("model refused the request")
            text = self._first_text(response).strip()
            if not text:
                raise LLMUnavailable("empty completion")
            return text
        except LLMUnavailable:
            raise
        except Exception as e:
            logger.warning(f"complete_text failed: {e}")
            raise LLMUnavailable(str(e))

    def complete_json(
        self,
        system: str,
        user: str,
        schema: Dict[str, Any],
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Dict[str, Any]:
        if not self.available:
            raise LLMUnavailable("Anthropic client unavailable")
        try:
            response = self._create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={
                    "format": {"type": "json_schema", "schema": schema}
                },
            )
            if getattr(response, "stop_reason", None) == "refusal":
                raise LLMUnavailable("model refused the request")
            text = self._first_text(response).strip()
            if not text:
                raise LLMUnavailable("empty JSON completion")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise LLMUnavailable("JSON completion was not an object")
            return data
        except LLMUnavailable:
            raise
        except json.JSONDecodeError as e:
            logger.warning(f"complete_json parse failed: {e}")
            raise LLMUnavailable(f"invalid JSON: {e}")
        except Exception as e:
            logger.warning(f"complete_json failed: {e}")
            raise LLMUnavailable(str(e))


def get_default_client() -> BaseLLMClient:
    """Resolve the configured LLM client from the environment.

    ``NEUROSONIX_LLM_PROVIDER`` selects the provider (default ``anthropic``);
    ``none`` forces the offline path. Returns a usable client either way — it
    never raises, honoring graceful degradation.
    """
    provider = os.environ.get("NEUROSONIX_LLM_PROVIDER", "anthropic").lower()
    if provider in ("none", "off", "disabled"):
        return NullLLMClient()
    if provider == "anthropic":
        model = os.environ.get("NEUROSONIX_LLM_MODEL", DEFAULT_MODEL)
        client = AnthropicLLMClient(model=model)
        return client if client.available else NullLLMClient()
    logger.warning(f"Unknown LLM provider '{provider}'; running degraded")
    return NullLLMClient()

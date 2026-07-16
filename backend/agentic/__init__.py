"""Agentic evaluation subsystem.

A multi-agent swarm that scores voice-agent conversations across four
role-play domains. The full pipeline is: audio -> transcript (Whisper/Gemini)
-> role-play agent response -> five evaluator agents -> synthesized score.

Every component degrades gracefully: with no LLM provider configured, the
role-play agent and evaluators fall back to deterministic, rule-based logic so
the platform stays fully functional offline.
"""

"""Shared Claude API helpers: default models, per-request options, response text extraction."""

from __future__ import annotations

from typing import Any

# Defaults — override via CLAUDE_FAST_MODEL / CLAUDE_ANALYSIS_MODEL env vars
DEFAULT_FAST_MODEL = "claude-haiku-5-5"
DEFAULT_ANALYSIS_MODEL = "claude-sonnet-5-5"

# Ceiling only (billing is per generated token). Thinking tokens count against it,
# so it must leave room for reasoning before the JSON answer.
MAX_TOKENS = 16_000

# Models that reject output_config.effort
_NO_EFFORT_PREFIXES = ("claude-3", "claude-haiku-4", "claude-sonnet-4-5", "claude-opus-4-5", "claude-opus-4-1")

# Models that accept the server-side refusal fallback (fallbacks: "default")
_FALLBACK_MODELS = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}


def request_options(model: str, effort: str) -> dict[str, Any]:
    """Extra kwargs for messages.create(): effort, plus refusal fallback where the model supports it."""
    options: dict[str, Any] = {}
    if not model.startswith(_NO_EFFORT_PREFIXES):
        options["output_config"] = {"effort": effort}
    if model in _FALLBACK_MODELS:
        # Beta param not typed on the non-beta messages.create(), so it goes through extra_body
        options["extra_body"] = {"fallbacks": "default"}
        options["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
    return options


def response_text(response: Any) -> str:
    """Concatenate text blocks. Newer models prepend thinking blocks, so content[0] isn't the answer."""
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError(f"Claude refused the request: {getattr(response, 'stop_details', None)}")
    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()

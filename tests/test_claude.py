"""Tests for shared Claude API helpers."""

from types import SimpleNamespace

import pytest

from bot.analyzer.claude import request_options, response_text


def test_request_options_sends_effort_and_fallback_for_sonnet() -> None:
    assert request_options("claude-sonnet-5-5", "medium") == {
        "output_config": {"effort": "medium"},
        "extra_body": {"fallbacks": "default"},
        "extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
    }


def test_request_options_haiku_has_no_fallback() -> None:
    assert request_options("claude-haiku-5-5", "low") == {"output_config": {"effort": "low"}}


def test_request_options_legacy_model_omits_effort() -> None:
    assert request_options("claude-haiku-4-5-20251001", "low") == {}


def test_response_text_skips_thinking_blocks() -> None:
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=' {"a": 1} ')],
    )
    assert response_text(response) == '{"a": 1}'


def test_response_text_raises_on_refusal() -> None:
    response = SimpleNamespace(stop_reason="refusal", stop_details=None, content=[])
    with pytest.raises(RuntimeError):
        response_text(response)

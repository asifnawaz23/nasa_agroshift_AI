"""ai.client tests with a fake Anthropic client (no network, no key, no cost)."""
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from ai import client as ai_client
from ai.client import ANSWER_SCHEMA, ask_llm

ANSWER = {"summary": "July is dry.", "points": [], "actions": [], "needs_expert": [],
          "confidence": "medium"}
MESSAGES = [{"role": "user", "content": "Why is July risky?"}]


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_client(response=None, error=None):
    messages = FakeMessages(response, error)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def response(text=json.dumps(ANSWER), stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category="cyber") if stop_reason == "refusal" else None,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        model="claude-opus-5-5",
    )


def test_no_key_means_template_fallback(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert ask_llm("system", MESSAGES, ANSWER_SCHEMA) is None


def test_returns_parsed_json_and_sends_schema():
    client, messages = fake_client(response())
    assert ask_llm("system", MESSAGES, ANSWER_SCHEMA, client=client, use_cache=False) == ANSWER

    sent = messages.calls[0]
    assert sent["output_config"]["format"] == {"type": "json_schema", "schema": ANSWER_SCHEMA}
    assert sent["fallbacks"] == "default"
    assert sent["system"] == "system"
    assert sent["messages"] == MESSAGES


@pytest.mark.parametrize("bad", [
    response(stop_reason="refusal"),
    response(stop_reason="max_tokens"),
    response(text="not json"),
    response(text="[1, 2]"),
])
def test_unusable_answers_return_none(bad):
    client, _ = fake_client(bad)
    assert ask_llm("system", MESSAGES, ANSWER_SCHEMA, client=client, use_cache=False) is None


def test_api_errors_return_none():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    for error in (anthropic.APITimeoutError(request=request),
                  anthropic.APIConnectionError(request=request)):
        client, _ = fake_client(error=error)
        assert ask_llm("system", MESSAGES, ANSWER_SCHEMA, client=client, use_cache=False) is None


def test_cache_hit_skips_the_api(monkeypatch):
    store = {}
    monkeypatch.setattr(ai_client, "_cache_get", lambda key: store.get(key))
    monkeypatch.setattr(ai_client, "_cache_set", lambda key, payload, model: store.update({key: payload}))

    client, messages = fake_client(response())
    assert ask_llm("system", MESSAGES, ANSWER_SCHEMA, client=client) == ANSWER
    assert ask_llm("system", MESSAGES, ANSWER_SCHEMA, client=client) == ANSWER
    assert len(messages.calls) == 1

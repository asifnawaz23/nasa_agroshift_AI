"""LLM client wrapper for the AI explanation and chat endpoints. Owner: Aman.

One function (plan section 10 / 15.3):

    ask_llm(system, messages, json_schema, timeout=15) -> dict | None

- Server-side only. The key comes from the LLM_API_KEY environment variable and never reaches
  the browser. LLM_MODEL picks the model (default claude-opus-5-5).
- The answer is forced into `json_schema` with structured outputs, so callers get a dict
  (summary, points, actions, needs_expert, confidence) instead of free text to parse.
- Returns None on ANY problem: no key configured, timeout, network or API error, refusal,
  truncated or invalid output. The caller then shows the template text from engine/explain.py,
  so the demo never depends on the LLM.
- Answers are cached in LocationCache(kind="ai") by a hash of the full request, so asking the
  same question about the same analysis twice costs nothing. The cache is skipped silently
  when Django or the table is not available (plain pytest, notebooks).
- Refusals: the request opts into server-side fallbacks ("default" routing), so a request a
  safety classifier declines is retried on Anthropic's recommended fallback model in the same
  call. If the whole chain still refuses, the result is None (template fallback).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_TIMEOUT_S = 15
# Explanations are short; this leaves room for adaptive thinking plus the JSON answer.
MAX_TOKENS = 4000
# Short grounded explanations do not need deep reasoning; low effort keeps answers fast
# enough for the 15 s budget.
EFFORT = "low"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
CACHE_KIND = "ai"


def _setting(name, default=""):
    """Django setting if configured, else the environment variable."""
    try:
        from django.conf import settings

        if settings.configured and hasattr(settings, name):
            return getattr(settings, name) or default
    except ImportError:
        pass
    return os.environ.get(name, default)


def cache_key(system, messages, json_schema, model) -> str:
    raw = json.dumps([system, messages, json_schema, model], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cache_get(key):
    try:
        from locations.models import LocationCache

        row = LocationCache.objects.filter(kind=CACHE_KIND, grid_key=key).first()
        return row.payload if row else None
    except Exception:  # Django not set up, table missing, DB down: no cache
        return None


def _cache_set(key, payload, model):
    try:
        from locations.models import LocationCache

        LocationCache.objects.update_or_create(
            kind=CACHE_KIND, grid_key=key, defaults={"payload": payload, "source_url": model}
        )
    except Exception:
        pass


def _client(api_key, timeout):
    import anthropic

    # max_retries=0: one attempt only, so the farmer is not kept waiting past the timeout;
    # a failed call falls back to the template text instead.
    return anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0)


def provider() -> str:
    """Which LLM to call: "anthropic" or "gemini".

    LLM_PROVIDER wins when set. Otherwise a GEMINI_API_KEY with no LLM_API_KEY means Gemini
    (free tier from Google AI Studio), so adding one env var on Render is enough.
    """
    chosen = (_setting("LLM_PROVIDER") or "").strip().lower()
    if chosen in ("anthropic", "gemini"):
        return chosen
    if _setting("GEMINI_API_KEY") and not _setting("LLM_API_KEY"):
        return "gemini"
    return "anthropic"


def ask_llm(system: str, messages: list, json_schema: dict, timeout: float = DEFAULT_TIMEOUT_S,
            *, client=None, use_cache: bool = True, session=None) -> dict | None:
    """Ask the LLM for a JSON answer that matches `json_schema`. None means: use the template.

    messages: [{"role": "user" | "assistant", "content": "..."}], oldest first (the frontend
    keeps the chat history and sends it every time).
    """
    if client is None and provider() == "gemini":
        return ask_gemini(system, messages, json_schema, timeout,
                          session=session, use_cache=use_cache)

    api_key = _setting("LLM_API_KEY")
    if client is None and not api_key:
        return None

    model = _setting("LLM_MODEL", DEFAULT_MODEL)
    key = cache_key(system, messages, json_schema, model)
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return cached

    import anthropic

    started = time.monotonic()
    try:
        client = client or _client(api_key, timeout)
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={
                "effort": EFFORT,
                "format": {"type": "json_schema", "schema": json_schema},
            },
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APITimeoutError:
        logger.warning("LLM timed out after %.1fs", time.monotonic() - started)
        return None
    except anthropic.RateLimitError:
        logger.warning("LLM rate limited")
        return None
    except anthropic.APIStatusError as exc:
        logger.warning("LLM API error %s: %s", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError:
        logger.warning("LLM connection error")
        return None
    except anthropic.AnthropicError as exc:
        logger.warning("LLM client error: %s", exc)
        return None

    elapsed = time.monotonic() - started
    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None) if response.stop_details else None
        logger.warning("LLM refused (category=%s) after %.1fs", category, elapsed)
        return None
    if response.stop_reason == "max_tokens":
        logger.warning("LLM answer cut off at max_tokens after %.1fs", elapsed)
        return None

    text = next((block.text for block in response.content if block.type == "text"), None)
    try:
        answer = json.loads(text) if text else None
    except json.JSONDecodeError:
        answer = None
    if not isinstance(answer, dict):
        logger.warning("LLM returned no usable JSON")
        return None

    logger.info("LLM answered in %.1fs (model=%s)", elapsed, response.model)
    if use_cache:
        _cache_set(key, answer, response.model)
    return answer


# --- Google Gemini (free tier) ---------------------------------------------------------------
# Plain REST with `requests`, so no extra package. The key goes in a header, never in the URL.
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# "gemini-flash-latest" follows Google's newest Flash model; the pinned name is a backup in case
# the alias is not available on a key. Override with GEMINI_MODEL.
GEMINI_DEFAULT_MODELS = ("gemini-flash-latest", "gemini-2.5-flash")


def _gemini_contents(messages):
    return [{"role": "model" if m.get("role") == "assistant" else "user",
             "parts": [{"text": str(m.get("content", ""))}]} for m in messages]


def _valid_answer(answer, json_schema):
    if not isinstance(answer, dict):
        return False
    return all(key in answer for key in (json_schema or {}).get("required", []))


def ask_gemini(system: str, messages: list, json_schema: dict, timeout: float = DEFAULT_TIMEOUT_S,
               *, session=None, use_cache: bool = True) -> dict | None:
    """Same contract as ask_llm, using the Gemini API. None on any problem (template fallback)."""
    api_key = _setting("GEMINI_API_KEY") or _setting("LLM_API_KEY")
    if not api_key:
        return None
    models = [_setting("GEMINI_MODEL")] if _setting("GEMINI_MODEL") else list(GEMINI_DEFAULT_MODELS)

    key = cache_key(system, messages, json_schema, "gemini:" + models[0])
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return cached

    import requests

    http = session or requests
    started = time.monotonic()
    for model in models:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": _gemini_contents(messages),
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": json_schema,
                "temperature": 0.3,
                "maxOutputTokens": MAX_TOKENS,
            },
        }
        for attempt in ("schema", "plain"):
            if attempt == "plain":
                # Some models reject responseJsonSchema: ask for JSON only, then validate below.
                body["generationConfig"].pop("responseJsonSchema", None)
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 1:
                logger.warning("Gemini out of time budget")
                return None
            try:
                resp = http.post(GEMINI_URL.format(model=model), json=body, timeout=remaining,
                                 headers={"x-goog-api-key": api_key,
                                          "Content-Type": "application/json"})
            except Exception as exc:  # timeout, connection error
                logger.warning("Gemini request failed: %s", type(exc).__name__)
                return None
            if resp.status_code == 404:
                logger.warning("Gemini model %s not found", model)
                break  # try the next model name
            if resp.status_code == 400 and attempt == "schema":
                continue  # retry without the schema field
            if resp.status_code != 200:
                logger.warning("Gemini API error %s", resp.status_code)
                return None
            try:
                data = resp.json()
                candidate = (data.get("candidates") or [{}])[0]
                if candidate.get("finishReason") not in (None, "STOP"):
                    logger.warning("Gemini stopped: %s", candidate.get("finishReason"))
                    return None
                text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
                answer = json.loads(text) if text else None
            except (ValueError, AttributeError, IndexError, TypeError):
                answer = None
            if not _valid_answer(answer, json_schema):
                logger.warning("Gemini returned no usable JSON")
                return None
            logger.info("Gemini answered in %.1fs (model=%s)", time.monotonic() - started, model)
            if use_cache:
                _cache_set(key, answer, "gemini:" + model)
            return answer
    return None


# The answer shape asked from the LLM (plan section 10). Shayan's ai/prompts.py can pass this
# as json_schema for /api/explain/ and /api/chat/.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    # "general" = general farming knowledge (chat), not from this farm's data
                    "type": {"type": "string",
                             "enum": ["observed", "estimated_cause", "prediction", "general"]},
                    "text": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["type", "text", "source"],
                "additionalProperties": False,
            },
        },
        "actions": {"type": "array", "items": {"type": "string"}},
        "needs_expert": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["summary", "points", "actions", "needs_expert", "confidence"],
    "additionalProperties": False,
}

"""Thin OpenAI wrapper. The API key lives only on the server (env var) and is never sent to the browser."""
from __future__ import annotations

import json
import logging

from ..config import get_settings

log = logging.getLogger("novatech.llm")
settings = get_settings()
_client = None


def enabled() -> bool:
    return settings.openai_enabled


def client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds, max_retries=2,
                         base_url=settings.openai_base_url or None)
    return _client


def chat(messages: list[dict], tools: list[dict] | None = None, json_mode: bool = False,
         temperature: float = 0.1, max_tokens: int = 900):
    kwargs: dict = dict(model=settings.openai_model, messages=messages, temperature=temperature,
                        max_tokens=max_tokens)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        kwargs["parallel_tool_calls"] = False
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return client().chat.completions.create(**kwargs)


def chat_json(system: str, user: str, max_tokens: int = 400) -> dict:
    resp = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                json_mode=True, max_tokens=max_tokens, temperature=0)
    return json.loads(resp.choices[0].message.content or "{}")


def friendly_error(exc: Exception) -> str:
    name = type(exc).__name__
    if "RateLimit" in name:
        return "The AI provider is rate-limiting requests. Falling back to the offline engine."
    if "Timeout" in name:
        return "The AI provider timed out. Falling back to the offline engine."
    if "Authentication" in name:
        return "The configured OpenAI API key was rejected. Falling back to the offline engine."
    return "The AI provider is unavailable. Falling back to the offline engine."

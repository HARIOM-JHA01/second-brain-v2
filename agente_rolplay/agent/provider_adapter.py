"""
Thin adapter layer for multi-provider AI message generation.

Supports Anthropic, OpenAI, and Google Gemini with a single unified interface.
Clients are lazy-initialized so there is no startup cost or circular-import risk.
"""

from __future__ import annotations

_anthropic_client = None
_openai_client = None
_google_genai = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        from agente_rolplay.config import ANTHROPIC_API_KEY
        _anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        from agente_rolplay.config import OPENAI_API_KEY
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_google():
    global _google_genai
    if _google_genai is None:
        from google import genai
        from agente_rolplay.config import GOOGLE_API_KEY
        _google_genai = genai.Client(api_key=GOOGLE_API_KEY)
    return _google_genai


def create_message(
    *,
    provider: str,
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int = 4096,
) -> str:
    """
    Generate a text response using the specified provider and model.

    Args:
        provider: "anthropic" | "openai" | "google"
        model: Model identifier (e.g. "claude-sonnet-4-6", "gpt-4o", "gemini-2.0-flash")
        system: System prompt string
        messages: List of {"role": "user"|"assistant", "content": str} dicts
        max_tokens: Maximum tokens in the response

    Returns:
        Plain text response string

    Raises:
        ValueError: If provider is not recognized
        Exception: Propagates SDK errors so callers can handle/log them
    """
    if provider == "anthropic":
        return _create_anthropic(model=model, system=system, messages=messages, max_tokens=max_tokens)
    elif provider == "openai":
        return _create_openai(model=model, system=system, messages=messages, max_tokens=max_tokens)
    elif provider == "google":
        return _create_google(model=model, system=system, messages=messages, max_tokens=max_tokens)
    else:
        raise ValueError(f"Unknown AI provider: {provider!r}. Must be 'anthropic', 'openai', or 'google'.")


def _create_anthropic(*, model: str, system: str, messages: list[dict], max_tokens: int) -> str:
    client = _get_anthropic()
    resp = client.messages.create(
        model=model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
    )
    return resp.content[0].text.strip()


def _create_openai(*, model: str, system: str, messages: list[dict], max_tokens: int) -> str:
    client = _get_openai()
    oai_messages = []
    if system:
        oai_messages.append({"role": "system", "content": system})
    oai_messages.extend(messages)
    resp = client.chat.completions.create(
        model=model,
        messages=oai_messages,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def _create_google(*, model: str, system: str, messages: list[dict], max_tokens: int) -> str:
    from google.genai import types as genai_types

    client = _get_google()

    # Build contents list from messages
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part(text=m["content"])],
        ))

    config = genai_types.GenerateContentConfig(
        system_instruction=system if system else None,
        max_output_tokens=max_tokens,
    )

    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return resp.text.strip()

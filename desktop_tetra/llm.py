from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class LLMProvider:
    def generate_json(self, system: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAICompatProvider(LLMProvider):
    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("openai package is required for OpenAI-compatible providers") from e
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_json(self, system: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Merge system into first position
        full_messages = [{"role": "system", "content": system}] + messages
        resp = self._client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.model,
            messages=full_messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content  # type: ignore[index]
        if not content:
            raise RuntimeError("Empty response from model")
        return json.loads(content)


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        try:
            import anthropic  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("anthropic package is required for Claude provider") from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def generate_json(self, system: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Anthropic expects system separately and content array
        conv: List[Dict[str, Any]] = []
        for m in messages:
            conv.append({"role": m["role"], "content": m["content"]})
        # Prefer JSON response if available; fall back to text + parse
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system,
            "messages": conv,
        }
        # Try structured output if SDK supports it
        try:
            # anthropic>=0.32 provides response_format
            kwargs["response_format"] = {"type": "json_object"}
        except Exception:
            pass
        resp = self._client.messages.create(**kwargs)  # type: ignore[arg-type]
        # Extract text
        parts = getattr(resp, "content", None)
        text = None
        if isinstance(parts, list) and parts:
            # parts[0] usually dict with {type: 'text', text: '...'}
            first = parts[0]
            text = getattr(first, "text", None) if not isinstance(first, dict) else first.get("text")
        if not text:
            # Some SDK versions expose .content[0].text directly
            try:
                text = resp.content[0].text  # type: ignore[attr-defined]
            except Exception:
                pass
        if not text:
            raise RuntimeError("Empty response from Claude")
        return json.loads(text)


def build_provider(provider: str, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> LLMProvider:
    p = provider.lower()
    if p in ("openai", "openai_compat"):
        return OpenAICompatProvider(model=model, api_key=api_key, base_url=base_url)
    if p in ("xai", "x-ai"):
        # xAI Grok is OpenAI-compatible
        base = base_url or os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        key = api_key or os.getenv("XAI_API_KEY")
        return OpenAICompatProvider(model=model, api_key=key, base_url=base)
    if p in ("lmstudio", "lm-studio", "lm_studio"):
        # LM Studio local server speaks OpenAI API by default
        base = base_url or os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        key = api_key or os.getenv("LMSTUDIO_API_KEY")
        return OpenAICompatProvider(model=model, api_key=key, base_url=base)
    if p in ("anthropic", "claude"):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        return AnthropicProvider(model=model, api_key=key)
    if p in ("local", "local-openai", "local_openai"):
        # Generic local OpenAI-compatible endpoint
        base = base_url or os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
        key = api_key or os.getenv("OPENAI_API_KEY")
        return OpenAICompatProvider(model=model, api_key=key, base_url=base)
    raise ValueError(f"Unknown provider: {provider}")

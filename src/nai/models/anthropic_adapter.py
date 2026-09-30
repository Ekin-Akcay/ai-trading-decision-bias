"""Anthropic Messages API adapter.

API note: Claude 5-family models (sonnet-5, opus-5, fable-5) reject sampling
params (`temperature` returns 400); Haiku 4.5 and older still accept them.
Determinism therefore isn't guaranteed on 5-family models — the prompt hash and
model version logged with each decision are what make runs auditable instead.
"""
from __future__ import annotations

from ..prompts import SYSTEM_PROMPT, parse_decision
from .base import ModelAdapter

# model-id prefixes that still accept temperature
_SAMPLING_OK_PREFIXES = ("claude-haiku-4-5", "claude-sonnet-4-5", "claude-3")


class AnthropicAdapter(ModelAdapter):
    is_llm = True

    def __init__(self, name: str, model_id: str, max_tokens: int = 200):
        import anthropic  # deferred so the package is optional until enabled

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # env key / ant auth profile
        self.name = name
        self.model_id = model_id
        self.model_version = model_id
        self.max_tokens = max_tokens

    def _content(self, ctx: dict):
        """Text, with the chart image prepended when the sim provides one and
        this model is vision-flagged (configs/models.yaml `vision: true`)."""
        img = ctx.get("image_path")
        if not (img and getattr(self, "vision", False)):
            return ctx["prompt"]
        import base64
        from pathlib import Path
        data = base64.standard_b64encode(Path(img).read_bytes()).decode()
        return [
            {"type": "image",
             "source": {"type": "base64", "media_type": "image/png", "data": data}},
            {"type": "text", "text": ctx["prompt"]},
        ]

    def decide(self, ctx: dict) -> dict:
        kwargs = {}
        if self.model_id.startswith(_SAMPLING_OK_PREFIXES):
            kwargs["temperature"] = 0.0
        try:
            resp = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": self._content(ctx)}],
                **kwargs,
            )
            if resp.stop_reason == "refusal":
                return {"action": "error", "confidence": 0.0, "reason": "refusal"}
            text = "".join(b.text for b in resp.content if b.type == "text")
            return parse_decision(text)
        except self._anthropic.APIStatusError as e:
            return {"action": "error", "confidence": 0.0, "reason": f"api {e.status_code}"}
        except self._anthropic.APIConnectionError:
            return {"action": "error", "confidence": 0.0, "reason": "connection error"}

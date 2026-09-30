"""OpenAI-protocol adapter — covers OpenAI itself plus any OpenAI-compatible
endpoint (Gemini via Google's compatibility base_url, OpenRouter, etc.).

Newer OpenAI models reject `temperature`/`max_tokens`; on such a 400 the call
is retried once with `max_completion_tokens` and no temperature.
"""
from __future__ import annotations

import os

from ..prompts import SYSTEM_PROMPT, parse_decision
from .base import ModelAdapter


class OpenAICompatAdapter(ModelAdapter):
    is_llm = True

    def __init__(self, name: str, model_id: str, base_url: str | None = None,
                 api_key_env: str = "OPENAI_API_KEY", max_tokens: int = 200):
        import openai

        self._openai = openai
        key = os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(f"{api_key_env} not set")
        self.client = openai.OpenAI(api_key=key, base_url=base_url)
        self.name = name
        self.model_id = model_id
        self.model_version = model_id
        self.max_tokens = max_tokens

    def _content(self, ctx: dict):
        """Text, with the chart image attached when provided and vision-flagged."""
        img = ctx.get("image_path")
        if not (img and getattr(self, "vision", False)):
            return ctx["prompt"]
        import base64
        from pathlib import Path
        data = base64.standard_b64encode(Path(img).read_bytes()).decode()
        return [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{data}"}},
            {"type": "text", "text": ctx["prompt"]},
        ]

    def _call(self, content, legacy_params: bool):
        kwargs = (
            {"temperature": 0.0, "max_tokens": self.max_tokens}
            if legacy_params else {"max_completion_tokens": self.max_tokens}
        )
        return self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            **kwargs,
        )

    def decide(self, ctx: dict) -> dict:
        content = self._content(ctx)
        try:
            try:
                resp = self._call(content, legacy_params=True)
            except self._openai.BadRequestError:
                resp = self._call(content, legacy_params=False)
            return parse_decision(resp.choices[0].message.content or "")
        except self._openai.APIStatusError as e:
            return {"action": "error", "confidence": 0.0, "reason": f"api {e.status_code}"}
        except self._openai.APIConnectionError:
            return {"action": "error", "confidence": 0.0, "reason": "connection error"}

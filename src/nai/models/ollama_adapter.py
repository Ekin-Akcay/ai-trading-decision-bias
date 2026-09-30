"""Local models via Ollama's REST API (http://localhost:11434). Free bulk
historical runs; pinned local weights give exact reproducibility."""
from __future__ import annotations

import requests

from ..prompts import SYSTEM_PROMPT, parse_decision
from .base import ModelAdapter


class OllamaAdapter(ModelAdapter):
    is_llm = True

    def __init__(self, name: str, model_id: str,
                 host: str = "http://localhost:11434", timeout: int = 120):
        self.name = name
        self.model_id = model_id
        self.model_version = f"ollama:{model_id}"
        self.host = host
        self.timeout = timeout

    def decide(self, ctx: dict) -> dict:
        user_msg = {"role": "user", "content": ctx["prompt"]}
        img = ctx.get("image_path")
        if img and getattr(self, "vision", False):
            import base64
            from pathlib import Path
            user_msg["images"] = [base64.standard_b64encode(
                Path(img).read_bytes()).decode()]
        try:
            r = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model_id,
                    "stream": False,
                    "options": {"temperature": 0.0, "seed": 7},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        user_msg,
                    ],
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            return parse_decision(r.json().get("message", {}).get("content", ""))
        except requests.RequestException as e:
            return {"action": "error", "confidence": 0.0, "reason": f"ollama: {e.__class__.__name__}"}

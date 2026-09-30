"""Adapter interface. Every model — LLM or baseline — answers the same question
from the same context and returns the same shape.

ctx keys: arm, asset, horizon, date (context end date), returns (np.array of the
context window's daily returns), prompt (prebuilt text for LLM adapters).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ModelAdapter(ABC):
    name: str = "base"
    model_version: str = ""
    is_llm: bool = False

    @abstractmethod
    def decide(self, ctx: dict) -> dict:
        """Return {"action": long|short|flat|error, "confidence": float, "reason": str}."""
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.name}>"

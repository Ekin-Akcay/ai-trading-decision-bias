"""Control models. Any LLM finding must be distinguishable from all of these.

All directional baselines place the same 'textbook' bracket — stop = 2×σ20,
target = 4×σ20 (2:1 reward:risk), where σ20 is the std of the last 20 context
returns — so among baselines only DIRECTION varies and geometry is controlled.
LLM geometry is then compared against this fixed reference (and H12–H14 test
whether LLM geometry itself is biased).

Random is deterministic per (asset, date) so reruns reproduce exactly.
Momentum/Reversal are the 'shadow strategies' an LLM might be imitating —
if LLM decisions correlate highly with Momentum-20, the LLM adds nothing (H8).
"""
from __future__ import annotations

import hashlib

import numpy as np

from .base import ModelAdapter

STOP_SIGMA = 2.0
TP_SIGMA = 4.0


def _stable_rng(asset: str, date: str, salt: str) -> np.random.Generator:
    seed = int(hashlib.sha256(f"{salt}|{asset}|{date}".encode()).hexdigest()[:12], 16)
    return np.random.default_rng(seed)


def _bracket(ctx: dict) -> tuple[float, float]:
    sigma = float(np.std(ctx["returns"][-20:]))
    sigma = max(sigma, 1e-4)
    return STOP_SIGMA * sigma, TP_SIGMA * sigma


class RandomModel(ModelAdapter):
    name = "random"

    def decide(self, ctx: dict) -> dict:
        rng = _stable_rng(ctx["asset"], str(ctx["date"]), self.name)
        action = rng.choice(["long", "short"])
        stop, tp = _bracket(ctx)
        return {"action": str(action), "stop_pct": stop, "tp_pct": tp,
                "confidence": float(rng.uniform(0.3, 0.9)), "reason": "coin flip"}


class AlwaysLong(ModelAdapter):
    name = "always-long"

    def decide(self, ctx: dict) -> dict:
        stop, tp = _bracket(ctx)
        return {"action": "long", "stop_pct": stop, "tp_pct": tp,
                "confidence": 0.5, "reason": "structural long"}


class Momentum(ModelAdapter):
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.name = f"momentum-{lookback}"

    def decide(self, ctx: dict) -> dict:
        r = ctx["returns"][-self.lookback:]
        up = float(np.prod(1 + r) - 1) > 0
        stop, tp = _bracket(ctx)
        return {"action": "long" if up else "short", "stop_pct": stop, "tp_pct": tp,
                "confidence": 0.5, "reason": f"{self.lookback}d trend follow"}


class Reversal(ModelAdapter):
    def __init__(self, lookback: int = 5):
        self.lookback = lookback
        self.name = f"reversal-{lookback}"

    def decide(self, ctx: dict) -> dict:
        r = ctx["returns"][-self.lookback:]
        up = float(np.prod(1 + r) - 1) > 0
        stop, tp = _bracket(ctx)
        return {"action": "short" if up else "long", "stop_pct": stop, "tp_pct": tp,
                "confidence": 0.5, "reason": f"{self.lookback}d mean reversion"}


BASELINES = {
    "random": RandomModel,
    "always-long": AlwaysLong,
    "momentum-20": lambda: Momentum(20),
    "reversal-5": lambda: Reversal(5),
}

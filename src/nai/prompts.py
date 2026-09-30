"""Prompt construction and response parsing — bracket-trade contract (v2).

Trade model (scope decision 2026-09-17): the model acts like a discretionary
trader placing ONE bracket order — direction + stop-loss distance + take-profit
distance from entry (entry = last close in the context). The trade then runs
untouched until stop or target is hit. No holding horizon exists.

The SAME system prompt and JSON contract are used for every provider — cross-
model comparability matters more than any provider-specific structured-output
feature. Prompt versions are logged with every decision; changing a template
means bumping its version string, never editing in place.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

SYSTEM_PROMPT = (
    "You are a trader in a research study. Given market data, place exactly one "
    "bracket trade like a discretionary trader: choose a direction, a stop-loss "
    "distance and a take-profit distance from the entry price (entry = the most "
    "recent close in the data). The trade will then run untouched until the stop "
    "or the target is hit — you never get to adjust it. Respond with ONLY a JSON "
    'object, no other text: {"action": "long" | "short" | "flat", '
    '"stop_loss_pct": <percent number>, "take_profit_pct": <percent number>, '
    '"confidence": <number 0 to 1>, "reason": "<at most 20 words>"}. '
    "Percent numbers are percent of entry price (2.5 means 2.5%). "
    'If action is "flat", use 0 for both distances.'
)

MASKED_PROMPT_VERSION = "masked-v2-bracket"          # daily-bar sleeve
INFORMED_PROMPT_VERSION = "informed-v2-bracket"
MASKED_15M_VERSION = "masked-v3-bracket-15m"          # intraday crypto sleeve
INFORMED_15M_VERSION = "informed-v3-bracket-15m"

STYLE_SHORT = ("You are a short-term trader: your trades typically close within "
               "hours and almost always within a few days. Size your stop and "
               "target for that timescale.")

# sanity clamps for parsed bracket distances (fractions of entry)
MIN_DIST = 0.0005   # 0.05%
MAX_DIST = 0.50     # 50%


def build_masked_context(prices: pd.DataFrame, end_date, n: int = 60,
                         rescale_vol: bool = False, target_vol: float = 0.01,
                         ts_format: str = "%Y-%m-%d") -> dict:
    """Return-series context up to and including end_date. No names, no dates.

    rescale_vol=True normalizes returns to target_vol per bar — strips scale
    cues that could let a model recognize a famous episode (partial leakage
    mitigation). The applied factor is returned as "scale": bracket distances
    chosen by the model in shown-space must be divided by it to get real-space
    distances. For intraday bars pass a per-bar target (e.g. 0.002 for 15m)
    and ts_format="%Y-%m-%dT%H:%M".
    """
    close = prices.loc[:end_date, "close"]
    if len(close) < n + 1:
        raise ValueError("not enough history")
    rets = close.pct_change().dropna().iloc[-n:].to_numpy()
    return context_from_window(rets, float(close.iloc[-1]), end_date,
                               rescale_vol=rescale_vol, target_vol=target_vol,
                               ts_format=ts_format)


def context_from_window(rets: np.ndarray, price: float, end_date,
                        rescale_vol: bool = False, target_vol: float = 0.01,
                        ts_format: str = "%Y-%m-%d") -> dict:
    """Same as build_masked_context but from a precomputed return window —
    O(n) per call; use for long intraday series (avoids full-series slicing)."""
    scale = 1.0
    if rescale_vol:
        sd = rets.std()
        scale = target_vol / sd if sd > 0 else 1.0
    r = rets * scale
    return {
        "returns": r,
        "scale": scale,
        "total_ret": float((1 + r).prod() - 1),
        "vol_daily": float(r.std()),
        "last5": float((1 + r[-5:]).prod() - 1),
        "price_at_decision": float(price),
        "context_end_date": pd.Timestamp(end_date).strftime(ts_format),
    }


def _series_block(ctx: dict, bar_label: str) -> str:
    rets = ", ".join(f"{x * 100:+.2f}" for x in ctx["returns"])
    return (
        f"Last {len(ctx['returns'])} {bar_label} percentage returns, oldest first:\n[{rets}]\n"
        f"Summary: cumulative {ctx['total_ret'] * 100:+.1f}%, per-bar vol "
        f"{ctx['vol_daily'] * 100:.2f}%, last 5 bars {ctx['last5'] * 100:+.2f}%.\n"
    )


def masked_prompt(ctx: dict, bar_label: str = "daily", style: str | None = None) -> str:
    head = (style + "\n") if style else ""
    return (
        head + "An unnamed liquid tradable asset. "
        + _series_block(ctx, bar_label)
        + "Entry is at the last close. Place your bracket trade now."
    )


def informed_prompt(asset: str, ctx: dict, bar_label: str = "daily",
                    style: str | None = None) -> str:
    head = (style + "\n") if style else ""
    return (
        head + f"Asset: {asset}. Time now: {ctx['context_end_date']} UTC.\n"
        + _series_block(ctx, bar_label)
        + f"Latest price (your entry): {ctx['price_at_decision']:.4g}.\n"
        "Place your bracket trade now."
    )


_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)
_DIST_KEYS_SL = ("stop_loss_pct", "stop_loss", "stop_pct", "sl_pct", "sl", "stop")
_DIST_KEYS_TP = ("take_profit_pct", "take_profit", "tp_pct", "tp", "target")


def _pick_pct(obj: dict, keys: tuple[str, ...]) -> float | None:
    """Extract a percent number (2.5 -> 0.025 fraction), tolerant of '2.5%' strings."""
    for k in keys:
        if k in obj:
            v = obj[k]
            try:
                x = float(str(v).replace("%", "").strip())
            except (TypeError, ValueError):
                continue
            return x / 100.0
    return None


def parse_decision(text: str) -> dict:
    """Parse {action, stop_pct, tp_pct, confidence, reason}; degrade gracefully.

    stop_pct/tp_pct are FRACTIONS of entry (0.025 = 2.5%). Invalid or missing
    bracket distances on a directional call -> action='error' (a trader who
    can't state a stop hasn't placed a trade)."""
    for match in _JSON_RE.finditer(text or ""):
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        action = str(obj.get("action", "")).lower().strip()
        if action not in ("long", "short", "flat"):
            continue
        conf = obj.get("confidence", 0.5)
        try:
            conf = float(np.clip(float(conf), 0.0, 1.0))
        except (TypeError, ValueError):
            conf = 0.5
        reason = str(obj.get("reason", ""))[:200]
        if action == "flat":
            return {"action": "flat", "stop_pct": 0.0, "tp_pct": 0.0,
                    "confidence": conf, "reason": reason}
        sl = _pick_pct(obj, _DIST_KEYS_SL)
        tp = _pick_pct(obj, _DIST_KEYS_TP)
        if sl is None or tp is None or not (MIN_DIST <= sl <= MAX_DIST) \
                or not (MIN_DIST <= tp <= MAX_DIST):
            return {"action": "error", "stop_pct": 0.0, "tp_pct": 0.0,
                    "confidence": 0.0, "reason": f"bad bracket: {text[:120]}"}
        return {"action": action, "stop_pct": sl, "tp_pct": tp,
                "confidence": conf, "reason": reason}
    return {"action": "error", "stop_pct": 0.0, "tp_pct": 0.0,
            "confidence": 0.0, "reason": (text or "")[:200]}

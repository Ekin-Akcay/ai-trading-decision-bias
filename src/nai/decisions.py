"""Decision records: the core dataset of the project. Append-only JSONL.

Schema documented in docs/04-data-and-leakage.md §5. Trade model is a bracket
order: direction + stop_pct + tp_pct (fractions of entry price, real-space).
There is no holding horizon — the exit is first passage of stop or target.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ACTIONS = ("long", "short", "flat", "error")


@dataclass
class DecisionRecord:
    model: str
    arm: str                 # masked | informed
    asset: str
    action: str              # long | short | flat | error
    stop_pct: float          # stop-loss distance, fraction of entry (0.025 = 2.5%)
    tp_pct: float            # take-profit distance, fraction of entry
    confidence: float
    reason: str
    context_end_date: str    # YYYY-MM-DD: last bar the model saw; entry at this close
    price_at_decision: float
    prompt_version: str = ""
    prompt_hash: str = ""
    model_version: str = ""
    timeframe: str = "1d"    # decision-bar size: "1d" | "15m" — routes evaluation
    run_id: str = "live"
    ts_decision: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def __post_init__(self):
        if self.action not in ACTIONS:
            self.action = "error"


def prompt_hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode()).hexdigest()[:16]


def append_records(records: list[DecisionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + "\n")


def read_records(paths: list[Path] | Path) -> pd.DataFrame:
    if isinstance(paths, Path):
        paths = [paths]
    rows = []
    for p in paths:
        if not p.exists():
            continue
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    if not df.empty:
        df["context_end_date"] = pd.to_datetime(df["context_end_date"])
    return df

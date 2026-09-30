"""Config loading: asset universe, model roster, costs, .env."""
from __future__ import annotations

import functools
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_DECISIONS = ROOT / "data" / "decisions"
DATA_RESULTS = ROOT / "data" / "results"
DATA_SIM = ROOT / "data" / "sim"


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader (KEY=VALUE lines). Never overrides existing env."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


@functools.lru_cache(maxsize=1)
def load_assets() -> dict:
    return yaml.safe_load((ROOT / "configs" / "assets.yaml").read_text())


@functools.lru_cache(maxsize=1)
def load_models() -> dict:
    return yaml.safe_load((ROOT / "configs" / "models.yaml").read_text())


def asset_universe() -> list[str]:
    cfg = load_assets()
    return [a for group in cfg["universe"].values() for a in group]


@functools.lru_cache(maxsize=None)
def asset_group(asset: str) -> str:
    cfg = load_assets()
    for group, assets in cfg["universe"].items():
        if asset in assets:
            return group
    return "default"


@functools.lru_cache(maxsize=None)
def cost_bps_per_side(asset: str) -> float:
    cfg = load_assets()
    costs = cfg["costs_bps_per_side"]
    return float(costs.get(asset_group(asset), costs["default"]))


@functools.lru_cache(maxsize=None)
def periods_per_year(asset: str) -> int:
    return 365 if asset_group(asset) == "crypto" else 252

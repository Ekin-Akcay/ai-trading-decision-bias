"""Build adapters from configs/models.yaml."""
from __future__ import annotations

from ..config import load_dotenv, load_models
from .base import ModelAdapter
from .baselines import BASELINES


def build_adapters(only: list[str] | None = None,
                   include_disabled: bool = False) -> tuple[list[ModelAdapter], list[str]]:
    """Returns (adapters, warnings). Unavailable providers are skipped with a
    warning, never a crash — the harness must run with whatever is available."""
    load_dotenv()
    cfg = load_models()
    adapters: list[ModelAdapter] = []
    warnings: list[str] = []
    for spec in cfg["models"]:
        name = spec["name"]
        if only is not None and name not in only:
            continue
        if not spec.get("enabled", False) and not include_disabled and only is None:
            continue
        provider = spec["provider"]
        try:
            if provider == "baseline":
                adapter = BASELINES[name]()
            elif provider == "anthropic":
                from .anthropic_adapter import AnthropicAdapter
                adapter = AnthropicAdapter(name, spec["model_id"])
            elif provider in ("openai", "openai_compat"):
                from .openai_adapter import OpenAICompatAdapter
                adapter = OpenAICompatAdapter(
                    name, spec["model_id"],
                    base_url=spec.get("base_url"),
                    api_key_env=spec.get("api_key_env", "OPENAI_API_KEY"),
                )
            elif provider == "ollama":
                from .ollama_adapter import OllamaAdapter
                adapter = OllamaAdapter(name, spec["model_id"])
            else:
                warnings.append(f"{name}: unknown provider '{provider}'")
                continue
            if spec.get("asset_whitelist"):
                adapter.asset_whitelist = spec["asset_whitelist"]
            adapter.vision = bool(spec.get("vision", False))
            adapters.append(adapter)
        except Exception as e:
            warnings.append(f"{name}: unavailable ({e})")
    return adapters, warnings


def model_spec(name: str) -> dict | None:
    for spec in load_models()["models"]:
        if spec["name"] == name:
            return spec
    return None

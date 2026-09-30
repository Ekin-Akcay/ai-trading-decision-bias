# NAI Trading — Negative-AI Trading Research

Research harness for one question: **are LLM trade decisions systematically wrong in
detectable conditions — and if so, can those conditions be traded (faded)?**

Not "invert the AI" (inverting noise is a guaranteed loser after costs — see the smoke
test) but: find the conditional cells where model error rates depart from 50%, use the
model ensemble as a narrative-crowding sensor, and build the one dataset nobody has —
a forward, leakage-proof log of many models' daily decisions.

## Read first
| Doc | What |
|---|---|
| [docs/00-thesis.md](docs/00-thesis.md) | The idea, sharpened: mechanisms M1–M6, tradeable formulations F1–F3, the two traps, falsification criteria |
| [docs/01-research-review.md](docs/01-research-review.md) | Literature: what's known, incl. evidence against the premise |
| [docs/02-experiments.md](docs/02-experiments.md) | Experiments E0–E8 with kill criteria |
| [docs/03-workflows.md](docs/03-workflows.md) | Phases, daily harvest loop, promotion gates, model roster |
| [docs/04-data-and-leakage.md](docs/04-data-and-leakage.md) | Lookahead rules, cutoff table, cost model, decision schema |
| [docs/05-simulation.md](docs/05-simulation.md) | The anonymized random-window simulation (primary Phase-1 vehicle) |
| [docs/hypotheses.md](docs/hypotheses.md) | Pre-registration registry (H1–H14) — write here BEFORE testing |

## Quickstart
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/pull_data.py      # daily OHLCV: 4 crypto, 7 equities, 3 commodity ETFs
.venv/bin/python -m pytest -q              # engine sanity tests
.venv/bin/python scripts/smoke_test.py     # E0: noise floor + inversion-trap demo
```

### Enabling LLM models
1. Create `.env` in the project root: `ANTHROPIC_API_KEY=…`, `OPENAI_API_KEY=…`, `GEMINI_API_KEY=…` (any subset).
2. For free local models: `brew install ollama && ollama pull llama3.1:8b`.
3. Flip `enabled: true` for the matching entries in [configs/models.yaml](configs/models.yaml).
4. Smoke it: `.venv/bin/python scripts/daily_harvest.py --dry-run`

### The two commands that matter
```bash
# Forward harvest (E7) — run daily; this dataset is the project's moat
.venv/bin/python scripts/daily_harvest.py

# Historical masked backtest for any model (E1/E2)
.venv/bin/python scripts/run_masked_backtest.py --model claude-haiku --respect-cutoff --every 3
```

## Layout
```
configs/    asset universe + costs, model roster + cutoffs
docs/       thesis, research review, experiments, workflows, leakage rules, hypothesis registry
src/nai/    data, features, prompts, decisions (JSONL store), backtest, metrics, models/ adapters
scripts/    pull_data, smoke_test, run_masked_backtest, daily_harvest, report
data/       raw/ (prices, regenerable), decisions/ (append-only logs — the asset), results/
tests/      engine sanity tests
```

Research tooling, not investment advice; nothing here places trades.

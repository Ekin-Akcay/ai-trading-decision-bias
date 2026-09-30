# Workflows & Execution Plan

## Phase map

```
Phase 0  (this session)   Scaffold, data pulls, backtest engine, baselines, docs.        ✅
Phase 1  (week 1–2)       E1–E6 on historical data: local models free + cheap API spot
                          checks on post-cutoff windows. Output: is there ANY conditional
                          structure, either sign?
Phase 2  (start now,      E7 daily decision harvest across the roster. Runs in parallel
          runs forever)   with everything; value compounds with calendar time.
Phase 3  (month 2–3)      Meta-model (F2) on harvested logs; walk-forward eval;
                          promotion gate → paper trading.
Phase 4  (month 4+)       Paper trade the surviving rule(s); monthly re-evaluation;
                          re-run whole battery on each new model generation.
```

## Daily harvest workflow (Phase 2, the core loop)

**Timing convention (pre-registered, boring on purpose):**
- Crypto: decide at 00:10 UTC using the just-closed UTC daily bar; evaluate close→close.
- US equities/ETFs/commodity ETFs: decide 21:15 UTC (after NYSE close) using that close; evaluate close→close.
- One decision per (asset × model × arm × horizon) per day, temp 0, fixed prompt version.

**Steps (all in `scripts/daily_harvest.py`):**
1. Refresh price data (yfinance, incremental).
2. Build contexts: masked arm (returns only) + informed arm (name/date/prices; headlines once news feed wired).
3. Query every enabled model in `configs/models.yaml`; parse to `{action, confidence, reason}`.
4. Append to `data/decisions/live/YYYY-MM.jsonl` with: timestamp, model id + version string, arm, asset, horizon, action, confidence, reason, prompt_hash, context_end_date, price_at_decision. **Append-only, never edited.** Failures are logged as `action=error` rows (a model refusing to answer is itself data).
5. Weekly: `scripts/report.py` joins matured decisions to forward returns, regenerates the metric battery per model/arm/cell.

**Scheduling:** macOS `launchd`/cron, or a Claude Code scheduled task can run it and summarize anomalies. Manual for the first days to shake out failures.

**Cost worksheet (per day, informed+masked, h=1):**
14 assets × 2 arms × ~6 models = ~170 calls/day, ≤1k tokens each →
- Haiku/GPT-mini/Flash tiers: ≈ $0.05–0.15/day total. Trivial.
- Add one frontier-top model on 4 assets only: +$0.10–0.30/day.
- Local Ollama models: $0. → **Run the roster wide; cost is not a constraint at daily frequency.**

## Weekly evaluation cadence
1. `report.py` → metrics per model × arm × asset-class × regime cell (only pre-registered cells; the rest render greyed-out as "exploratory").
2. Update `hypotheses.md` statuses (pending → supported/rejected/needs-data) with dates.
3. 15 minutes of human judgment: anything worth a new pre-registered hypothesis? Register it *before* looking at its cell.

## Promotion gates (signal → money path)
| Gate | Requirement |
|---|---|
| G1: Candidate | Pre-registered cell significant at FDR 10% on Phase-1 data, > cost hurdle, sign-stable in 2/3 sub-periods, absent in controls |
| G2: Replicated | Same cell significant on ≥60 days of *forward* (E7) decisions it never touched |
| G3: Paper | 8+ weeks live paper trading, realized net Sharpe > 0.8, drawdown < modeled 95% band |
| G4: Real money | Small size; only after G3 and a written capacity/cost re-check |

Skipping a gate requires writing down why, in this file, with a date. (Future-you will thank present-you.)

## Model roster (initial pick, `configs/models.yaml`)
| Model | Role | Access | Historical backtest? |
|---|---|---|---|
| claude-haiku-4-5 | frontier-cheap workhorse | API key | post-cutoff only |
| gpt-5-mini / gpt-4.1-mini | frontier-cheap, 2nd vendor | API key | post-cutoff only |
| gemini-2.5-flash | frontier-cheap, 3rd vendor | API key | post-cutoff only |
| claude-sonnet-5 (4 assets) | capability gradient probe | API key | post-cutoff only |
| llama3.1:8b (Ollama) | free bulk historical + "genuinely average AI" | `brew install ollama` | yes (masked, with caveats) |
| qwen2.5:7b (Ollama) | 2nd local family | Ollama | yes (masked, with caveats) |
| random / always-long / momentum-20 / reversal-5 | controls | built-in | yes |

Vendor diversity matters: consensus/disagreement signals (E4, E8) are meaningless across models that share training lineage.

## Setup runbook
```bash
cd "[local-home]/Documents/Claude Code/Quant/NAI Trading"
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/pull_data.py            # refresh/extend price data
.venv/bin/python scripts/smoke_test.py           # E0: engine + noise floor
.venv/bin/python -m pytest -q                    # engine unit tests
# after adding keys to .env (see README):
.venv/bin/python scripts/daily_harvest.py --dry-run
.venv/bin/python scripts/run_masked_backtest.py --model momentum-20   # any adapter name
```

## Scope decisions (2026-09-17)
1. **Price-only program; news pipeline CANCELLED.** The model is a price-action decision-maker, not a macro/news model. Rationale: cleaner cross-model comparability, no news-data engineering, historical masked runs become far more usable, and the extrapolation/optimism bias this project hunts is documented to exist on price-only inputs (Chen, Green, Gulen & Zhou, arXiv:2409.11540 — see 01-research-review §C). If the price-only program finds nothing, narrative inputs are the *next* experiment, not a prerequisite.
2. **Masked arm is primary.** The "informed" arm is kept in the FORWARD harvest only and consists of asset name + date + the same price series — no headlines, ever. Its sole purpose is the controlled A/B against masked (does knowing the identity change behavior? Glasserman–Lin "distraction effect"), at zero extra engineering cost. It is never backtested historically.
3. **Trade model is a BRACKET ORDER, not a fixed horizon** (user decision 2026-09-17, replacing the earlier h=1/h=5 design). The model decides direction + stop-loss + take-profit like a discretionary trader and never touches the trade again; exit is first passage of either level, holding time is an outcome (≈10 days at the 2σ/4σ reference geometry). One decision per asset × arm × model per day; overlapping open trades are independent tickets. Fixed-horizon direction tables remain available as a *post-hoc diagnostic only* (computed from the same logged decisions, no extra prompting) to decompose direction skill from bracket-geometry skill. Evaluation rules: docs/04 §6.
4. **Every masked historical run of an LLM uses `--rescale-vol` and, for pre-cutoff periods, `--decoys ≥1` (E9)** so each result ships with its own leakage estimate. (E9 decoys currently implemented for the daily sleeve; intraday LLM runs should prefer post-cutoff windows.)
5. **Timeframe: 15-minute chart for the crypto sleeve** (user decision 2026-09-18). Primary test universe: BTC, ETH, SOL, DOGE on Binance USDT-M perps. Context = 288×15m bars (3 days) with `STYLE_SHORT` trader framing; evaluation = first passage on 1m bars; **time-stop 72h** (market exit, scored) enforcing "max 2–3 days"; rescale target 0.2%/bar for masked contexts. Tooling: `scripts/intraday_backtest.py`, `scripts/intraday_harvest.py` (run once daily after the CDN's daily files land, ~02:00 UTC or later; it back-fills all 4h marks of the completed day, idempotently). The daily-bar sleeve (equities/commodities controls + E9 leakage gauging) stays on `run_masked_backtest.py`/`daily_harvest.py`.

# Experiment Designs (E0–E8)

Each experiment states: protocol, cost, success signal, kill signal. Run order ≈ numbered order. **Register any new hypothesis in `hypotheses.md` before running its test.** All directional tests are evaluated with the metric battery in `src/nai/metrics.py` (hit rate + Wilson CI, mean bps/trade vs cost hurdle, calibration, regime splits, inversion PnL after costs).

---

## E0 — Noise floor & engine validation (baselines) ✅ runs today, $0
**Protocol:** Run Random, Always-Long, Momentum(20d), Reversal(5d) over the full universe (daily bracket decisions, 2019→present, uniform 2σ-stop/4σ-target geometry so only direction differs).
**Purpose:** (a) verify the first-passage backtester on known cases; (b) produce the *noise-floor table* — what TP-hit rates and expectancies luck, drift and dumb rules produce here. Key calibrations from the first run: random ≈ tpBase (33%) and ≈ 0 net; **always-long hits 42% TP with +160 bps/trade from drift alone — that, not zero, is the bar an LLM must beat.** Every later LLM result is read against this table.
**Kill criterion for the whole project:** none — this is calibration.
```bash
.venv/bin/python scripts/smoke_test.py
```

## E1 — Masked bracket trades, historical, local models — $0, needs Ollama
**Protocol:** For each asset × every 2nd trading day 2019→present: masked context (last 60 daily returns, no names/dates, summary stats), ask llama3.x-8B & qwen2.5-7B for one bracket trade {action, stop_loss_pct, take_profit_pct, confidence}, temp 0. ~14×850 ≈ 12k calls per model — free locally, a couple hours wall-clock. Run with `--rescale-vol --decoys 1` (E9 embedded).
**Success:** any pre-registered cell with tpHit% outside the Wilson band around that cell's tpBase% AND net expectancy (either sign) > 0, replicating across both models — or a robust geometry pathology (H12–H14).
**Kill:** everything at tpBase with sane geometry → masked pure-pattern arm is dead; whatever bias exists needs identity/narrative context (→ E7 informed A/B matters more).
**Leakage note:** masked ≠ leakage-proof (models can recognize famous crash shapes); pre-cutoff results are suggestive only and must clear the E9 gauge.

## E2 — Masked direction, API-cheap models, post-cutoff only — ~$5–15
**Protocol:** Same as E1 but Claude Haiku + GPT-mini + Gemini Flash, restricted to each model's post-cutoff window (see `04-data-and-leakage.md`), sampling every 3rd day to control cost.
**Purpose:** do frontier-cheap models show the same conditional structure as local models? (Mechanism check M1/M3.)

## E3 — Calibration & confidence-conditional accuracy — free (reuses E1/E2 logs)
**Protocol:** Bucket decisions by stated confidence (≤0.5, 0.5–0.7, >0.7); accuracy per bucket; slope of calibration curve.
**Success (for fading):** inverted calibration — high-confidence calls *less* accurate (M4). Then test "fade only confidence>0.7 calls" as a pre-registered cell.

## E4 — Ensemble consensus extremes (the crowding test) — free (reuses logs)
**Protocol:** Per asset-day, consensus score = mean signed action across models (weighted by confidence). Sort into quintiles; forward returns per quintile; focus on |consensus| extremes.
**Success:** top-consensus quintile forward return < bottom quintile (fade works), or monotone *positive* (follow works — also fine!). 
**This is the highest-prior experiment in the project (M2).**

## E5 — Horizon-decomposition diagnostic — free (post-hoc on the same logs, no extra prompting)
**Protocol:** The DIRECTION of each logged bracket decision evaluated at fixed h ∈ {1, 5, 20} via `nai.backtest.evaluate` (diagnostic only — the trade model stays bracket).
**Success (M1):** direction accuracy rising in h (wrong at reversal horizon, right at momentum horizon) → the model's bracket losses should concentrate in fast stop-outs; distinct signature, hard to get by luck. Also decomposes "bad direction" from "bad geometry": a model can pick direction at 50% yet still lose via noise-band stops (H12).

## E6 — Post-big-move conditioning (capitulation detector) — free (reuses logs)
**Protocol:** Split decisions by trailing 20d return decile of the asset. Test accuracy in extreme deciles vs middle.
**Success (M3):** accuracy collapse (<45%) after extreme trailing moves, especially crashes, especially in crypto/meme names, not in SPY/GLD controls.

## E7 — Informed arm, live forward harvest — the gold dataset — ~$0.5–2/day
**Protocol:** Daily cron (see `03-workflows.md`): for each asset, build *informed* context (asset name, date, recent prices, recent headlines once the news feed is wired), query the full roster, log to append-only JSONL with prompt hash + model version. Never evaluated until ≥60 days accumulate. 100% leakage-proof by construction.
**This should start as soon as API keys are added, even while E1–E6 are running — its value only compounds with time.**

## E9 — Synthetic-decoy leakage gauge (makes masked historical runs trustworthy) — $0 with local models
**Protocol:** Re-run any masked historical experiment with `--decoys N` (N=1–2): each real asset is interleaved with N moving-block-bootstrap clones of its own returns (block=10, preserves vol clustering; models cannot have memorized a bootstrap path). Compare accuracy on real vs synthetic series, pre-cutoff and post-cutoff separately.
**Reading:** `hit(real) − hit(synthetic)` pre-cutoff ≈ memorization leakage (H11); post-cutoff the gap should be ≈ 0. Baselines must show ≈ 0 everywhere (sanity). Any masked pre-cutoff finding is only promotable if it ALSO appears on the synthetic decoys or survives on post-cutoff data — a pattern that exists only on real, pre-cutoff series is memory, not behavior.
**Bonus:** synthetic decoys also answer "is the model reading patterns or recognizing episodes" — genuine pattern-reading skill transfers to bootstrap paths; episode recall does not.

## E8 — Disagreement → volatility (consolation prize, M6) — free (reuses logs)
**Protocol:** Dispersion(asset, day) = variance of signed actions across roster. Regress next-day |return| (and realized vol) on dispersion, controlling for trailing 20d vol (the lazy benchmark). 
**Success:** dispersion adds significant explanatory power → use for sizing even if all directional tests fail.

---

## Reading results: the decision tree

```
E0 noise floor
└─ E1/E2 any conditional signal (either sign)?
   ├─ NO → E4/E8 (ensemble-level signals may exist even if per-model is noise)
   │        └─ still no → thesis dead per falsification criteria (00-thesis §5);
   │                      keep E7 running one more model generation before burying it.
   └─ YES → does it survive: (a) FDR across cells? (b) replication on untouched
            later slice? (c) cost hurdle? (d) absent in control assets?
            └─ YES → F1 rule-based paper trading + start F2 meta-model
                     once E7 logs > ~3k decisions.
```

## Statistical hygiene (applies to all)
- Hit-rate significance: Wilson intervals; cross-cell: Benjamini–Hochberg FDR at 10%.
- Overlapping horizons (h>1 sampled daily): use non-overlapping subsamples or Newey–West on mean returns; the runner samples every h days by default for h>1.
- Sub-period stability: every "significant" cell must hold sign in ≥2 of 3 equal sub-periods.
- Never tune on the evaluation slice; the last 20% of any sample is touched once, at the end.

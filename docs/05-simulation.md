# The Simulation (anonymized random-window experiment)

Implemented 2026-09-24 in `src/nai/sim.py` + `scripts/run_simulation.py`.
This is the primary Phase-1 experiment vehicle: it decouples decision
collection from calendar time (thousands of windows per day possible) while
keeping every model on identical stimuli.

## The loop

```
sample random window ──> anonymized snapshot ──> chart PNG + stats text
   (asset ∈ {BTC,ETH,SOL,DOGE},        (price rebased: now = 100;
    any time 2020→present,              volume ÷ recent avg; no dates,
    overlaps allowed, seeded RNG)       no names; MA20/50, σ, ATR)
        │
        ├──> same prompt (+ image where supported) to EVERY model:
        │      claude-haiku · gpt-mini · gemini-flash · deepseek (+ baselines)
        │      → one bracket trade: long/short/flat + stop% + tp% + confidence
        │
        └──> immediate resolution on historical 1m bars (first passage,
             72h time-stop): outcome (tp/sl/timeout/ambiguous/open),
             minutes held, exit ts/price, P/L gross & net %, MFE %, MAE %
        │
        └──> one JSONL row per (window × model): data/sim/decisions/<run>.jsonl
             chart PNGs: data/sim/charts/<run>/<window_id>.png
```

## Stimulus contract (`sim-v1-15m-window`)

- **Window**: 40 visible 15m bars (`--visible-bars`, default raised from 20 on
  2026-09-24 user feedback); indicators computed on a hidden 200-bar history,
  so every MA point is a true rolling average including pre-window bars —
  MA20/MA50 read exactly as they would on a live terminal at that moment.
- **Anonymization**: prices ×(100/current close); volume as multiple of the
  200-bar average; x-axis = bar offsets (−19…now); no dates, names, or years.
  Real asset/timestamp are stored in the row for evaluation but never shown.
- **Text block** (identical for all models): the 40 OHLC rows + vol ratios,
  MA20/MA50 (rebased) and price position vs both, σ of 15m returns over the
  visible window and over the last 2 days, ATR(14) as % of price, window
  return, 24h and last-5-bar volume ratios. Ask: one bracket trade, stop/tp
  as % of entry (entry = 100.00), JSON contract from `prompts.SYSTEM_PROMPT`.
- **Image**: candlestick + volume PNG in standard trading-chart idiom
  (green/red candles, MA overlays). Attached only for `vision: true` models
  (claude/gpt/gemini); DeepSeek's API is text-only and receives the identical
  numeric stimulus — noted as a comparability caveat in any cross-model claim
  about *chart reading* specifically. Each row records `stimulus`
  ("text+image" | "text").
- **Measuring the image's marginal effect (paired design):** the same
  `--seed` reproduces the same windows, so running once normally and once with
  `--no-charts` yields a paired text-vs-text+image comparison per model —
  answering "does the chart change decisions/performance at all" as its own
  pre-registrable question.

## Recorded per row

Decision: model, action, stop_pct, tp_pct, confidence, reason, prompt hash/
version, image path. Window: window_id, asset, real timestamp, real price,
σ/ATR/MA/volume stats (for conditional analysis). Result: outcome, entry/exit
price, exit timestamp, minutes held, P/L gross and net %, MFE/MAE % (max
favorable/adverse excursion through the exit bar). Everything needed for
E3/E4/E6/H12–H14 cells comes free with the rows.

## Leakage status

Windows are historical, so LLM decisions are subject to the training-cutoff
rules (docs/04): masked/anonymized ⇒ *suggestive*; per-model post-cutoff
window filtering and the forward harvest remain the confirmatory tiers. The
anonymization here (rebased prices, ratio volumes, no dates) is the strongest
masking we have — but famous shapes remain recognizable in principle.

## Running

```bash
# stub check, no AI (baselines only, already enabled):
.venv/bin/python scripts/run_simulation.py --windows 16

# live, once keys are in .env and the four are enabled in configs/models.yaml:
.venv/bin/python scripts/run_simulation.py --windows 200 \
    --models claude-haiku gpt-mini gemini-flash deepseek --seed 42
```

Keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`DEEPSEEK_API_KEY` in `.env`. Cost estimate: ~1.2k input tokens text + ~1.1k
tokens image per vision call ⇒ ≈ $0.20–0.50 per 100 windows across all four
models at mini/flash/haiku tiers. Determinism: seeded windows; temp 0 where
the API supports it; prompt hash logged per row.

## Reading results (`nai.sim.summarize_sim`)

Skill = `tpHit%` vs `tpBase%` (= stop/(stop+tp), the random-walk base rate for
the model's own chosen geometry) — never vs 50%. `pnl_net%/tr` carries the
cost verdict; `stopW/tpW` + σ columns feed H12–H14 (geometry pathologies);
MFE/MAE separate "wrong direction" from "right direction, bad bracket" —
a trade stopped out with large MFE first is a geometry failure, not a
direction failure.

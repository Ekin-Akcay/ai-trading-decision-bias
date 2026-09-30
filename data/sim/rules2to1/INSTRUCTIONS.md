# Rules-2to1 experiment — forced-geometry variant (v2)

Shared protocol for re-running the SAME 100 SOL-USD moments with two rule changes.
Any operator (Codex/GPT side, Claude side, or future API runs) must follow this file
exactly so results stay comparable. Written 2026-09-26.

## The two rule changes (vs the free-geometry v1 runs)

1. **No flat.** Every case must end in a position: `action` is `"long"` or `"short"`. Flat/no-trade is not an allowed output.
2. **Fixed 2:1 reward-to-risk.** The model chooses ONLY the stop-loss distance. The take-profit is set by the harness at EXACTLY `2 × stop_loss_pct`. Models must not be asked for a take-profit, and any take-profit field they emit anyway is ignored (log it, don't use it).

Everything else is IDENTICAL to v1: same stimuli, same masking, same engine, same
bracket-and-never-touch trade model, gross P/L headline (no fees), 20 bps round-trip
kept as the secondary after-fees column.

## The 100 moments

- Canonical list: `data/sim/rules2to1/window_list.json` — 100 entries with `case`
  (1–100), `window_id`, stimulus paths, `window_end_ts`, `price_real`, and the window
  stats needed for decision rows.
- Case numbering matches the ordering already used by the OpenAI v1 runs
  (case 1 = `f2d094003c` … case 100 = `eb5f9f2e41`). Verified 2026-09-26.
- Stimuli are the ORIGINAL, unchanged files under `data/sim/agent-demo2/`:
  `prompt_<window_id>.txt` (text stats) + `<window_id>.png` (chart). Do not edit them;
  hash them into your rows (sha256) as the v1 OpenAI runs did.

## Per-case procedure

- One FRESH model subagent/thread per case. No inherited conversation, no cross-case
  or cross-model feedback, no outcome feedback ever.
- Deliver to the model: the full text of the case's `prompt_file` + the `chart_file`
  image, and the wrapper below. Nothing else about the case.
- The stimulus text file ends with the v1 response-format instructions (it asks for a
  `take_profit_pct` and allows `flat`). The wrapper OVERRIDES that. Use this wrapper
  (adapt only the file-delivery mechanics to your harness):

```text
Short-term trader simulation. Read the two attached inputs (text stats, then chart).
RULES FOR THIS RUN — they override any response format described inside the files:
- You MUST take a position: "long" or "short". Flat / no-trade is NOT allowed.
- You choose ONLY the stop-loss distance. Your take-profit is fixed by the exchange
  at EXACTLY 2x your stop-loss distance (2:1 reward-to-risk). Do not output a
  take-profit field.
Entry = current price = 100.00; the trade then runs untouched until your stop-loss
or the fixed 2x take-profit is hit.
Reply with EXACTLY this JSON object (one line, no markdown fences):
{"action":"long"|"short","stop_loss_pct":<percent number>,"confidence":<number 0 to 1>,"reason":"<max 20 words>"}
stop_loss_pct is percent of entry (2.5 means 2.5%).
```

## Validity / exclusions

- Valid decision: `action` in {long, short}; `stop_loss_pct` a number with
  0.05 ≤ stop ≤ 50 (percent). Then `tp_pct := 2 × stop_pct` by rule.
- Invalid (excluded BEFORE scoring, preserved in your run folder, fresh re-run of the
  case): flat/refusal, missing/unparseable stop, stop outside bounds, tool-access
  violation, incomplete stimulus delivery. Max 3 attempts per case; if still
  non-compliant, record an `action:"error"` row (excluded from scoring) and move on.
- Never exclude or re-run based on the trade's outcome. Log every exclusion with a
  reason, as in the v1 OpenAI runs.

## Resolution (identical engine to v1)

Resolve immediately on historical 1m bars with the existing engine — from repo root:

```python
import sys; sys.path.insert(0, "src")
import pandas as pd
from nai.sim import SimResolver
resolver = SimResolver(["SOL-USD"], time_stop_hours=72)
res = resolver.resolve("SOL-USD", pd.Timestamp(window_end_ts), action, stop_pct, tp_pct)
# stop_pct / tp_pct as FRACTIONS (0.025 = 2.5%); tp_pct = 2 * stop_pct
```

Entry = window-close price; first passage on 1m bars; gap-through exits at open;
both-levels-in-one-bar = ambiguous (excluded); 72h time-stop = "timeout" (scored);
MFE/MAE recorded. `res` supplies outcome/entry/exit/exit_ts/minutes_held/
pnl_gross_pct/pnl_net_pct/mfe_pct/mae_pct.

## Recording

- One JSONL row per case × model in `data/sim/decisions/<run_id>.jsonl`, using the
  SAME row schema as v1 (see any v1 file for the field list), with:
  - `prompt_version`: `"sim-v2-15m-window-2to1-noflat"`
  - `prompt_hash`: sha256 of the stimulus TEXT file (same convention as v1)
  - `stop_pct` = chosen stop as fraction; `tp_pct` = exactly `2 × stop_pct`
  - provenance extras (raw_response, hashes, thread ids) welcome, as in v1
- Run naming: OpenAI side uses run_id/folder starting `rules2to1-openai-` (your own
  timestamp convention); Claude side writes `rules2to1-claude-agents`
  (file: `data/sim/decisions/rules2to1-claude-agents.jsonl`).
- Do NOT append to any v1 file, do not modify anything under `data/sim/agent-demo2/`,
  `data/sim/decisions/` (existing files), `src/`, or `scripts/`. Additive only, own
  run folder for audits/raw attempts, HANDOFF.md summarizing what was done.

## Analysis conventions

- Headline P/L is GROSS %/trade. tpBase under forced 2:1 is 33.33% for every trade
  (stop/(stop+tp) = 1/3), so tpHit% is directly comparable across all models here.
- Primary comparison: each model's forced-2:1 run vs its OWN free-geometry v1 run on
  the same 100 windows (within-model, within-window: the geometry rule is the only
  treatment).
- The Claude-side report for this experiment: `data/sim/reports/rules2to1.html`.

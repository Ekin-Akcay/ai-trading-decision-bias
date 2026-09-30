# V3: price and volume only — shared protocol

User-authorized 2026-09-29. Prepare the SAME canonical 100 cases as v2, in identical order. Current OpenAI batch runs only cases 1–20 on Luna, Terra and Astra (60 decisions); cases 21–100 stay pending. Other operators can use this exact window_list.json and stimuli in their own run folders without touching OpenAI artifacts.

## Input treatment

Only 40 anonymized 15-minute OHLC bars, per-bar relative volume, and a candle/volume chart. Text OHLCV rows are byte-identical to v2; raw chart OHLCV and entry rebasing/volume normalization are identical. Remove all MA lines/labels/values, the volatility/sigma/ATR section, and the derived move/aggregate-volume summary. No asset identity or historical date is delivered. The volume reference remains the original trailing-200-bar average. The price chart can autoscale differently once MA lines are removed. This treatment is broader than MA-only removal and cannot isolate the causal contribution of MAs alone.

The controller retains real dates, prices, and original indicator values privately for scoring. Agents receive only `input.txt` and `chart.png`. Never send window_list.json, this protocol's analytic context, previous decisions, hypotheses, outcomes, or other cases to an agent.

## Decision contract unchanged from v2

Fresh isolated single turn per case/model; same exact v2 wrapper, reasoning effort medium; tool access disabled. Long or short required; no flat. Agent chooses stop_loss_pct in percent of entry (0.05–50 inclusive); TP derived only by controller at exactly 2×SL. Confidence 0–1; nonempty reason ≤20 words. No outcome feedback. Preserve every raw attempt. Accept the first valid audited attempt, maximum three attempts for input/access/format failures only. Never rerun based on outcomes. Unsupported models are errors, not substituted models.

The legacy trailing response-format sentence in the source stimulus remains unchanged and is overridden by the same wrapper as v2, preserving that aspect of delivery.

## Evaluation and storage

Use unchanged nai.sim.SimResolver with historical one-minute bars, 72-hour timeout, gap fills at open, ambiguous both-level minute excluded and counted. Gross and net (existing 20 bps round trip) both reported. Each model chooses brackets before outcomes are resolved. Match v3 vs historical v2 on exact model/window pairs. Also compare fixed elapsed-time signed movement at 15,30,105 minutes independently of original exit. N=20 unique windows in this batch; 60 decisions are not 60 independent market observations. Historical v2 controls are not fresh repeated controls, and collection harness differs for some original decisions; do not call this a clean causal or fresh-market test.

Save a new `sim-v3-15m-window-pricevolume-2to1-noflat` ledger and a separate HTML report, raw attempts, hashes, input audit, isolation audit, summary and HANDOFF. Existing Claude/OpenAI results and code remain untouched. Do not feed exit-policy study findings to the agents.

## Concurrent retrospective study (controller only)

Separately evaluate existing v1/v2 decisions: pure time exits 15,30,105 minutes primary; 5,60,240 secondary. Scale BOTH original SL and TP by 1,.75,.5,.25 with unchanged72h timeout. Secondary combinations cap brackets at15,30,105m. Keep all cells, paired original comparisons, ambiguous exclusions/bounds, cost assumptions, window-cluster uncertainty, multiplicity correction and chronological sensitivity. This is already-inspected data; no selected rule counts as validated.

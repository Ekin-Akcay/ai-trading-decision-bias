# Frozen test:50 new random eligible windows, Terra, two reversal hypotheses

Frozen2026-09-29 before sampling model responses or evaluating forward prices. User requests a folder of ideas and50new trials using one model for the two reversal hypotheses. Interpretation disclosed:50total new setups/trades, not50qualifying trades for each direction. Every eligible setup triggers exactly one of the two rules. Do not extend sampling to balance outcomes or signal counts.

## Model and input

Use gpt-5.6-terra with medium reasoning, same original v2 full MA-present chart/stats and forced2:1/no-flat wrapper. Terra is chosen for continuity with the earlier pilot and its exploratory weak long-call accuracy; it is not proven to be the most exploitable model. Model selection is part of prior discovery, not a result of this new batch. Preserve model ID, no substitutions.

Fresh single-turn CLI agent per window; directly attached exact text+chart; empty cwd; user config, tools, external data, plugins, memories and rules disabled as in v3. Audit actual transcripts for exact model, effort, complete text/image hashes and zero tool calls. Agent receives no asset identity, historical date, other decisions, outcomes, research hypotheses or planned reversal/time exits. It thinks it places the unchanged original bracket trade. Keep chosen stop/confidence/reason for analysis; do not use them to optimize the reversal rules.

## Sample

Asset SOL-USD, same raw source as discovery. Random seed2026092901. Draw50windows from15-minute bars where the last close is at or above its trailing20/50bar averages. All conditioning uses information available at original entry. Require200contiguous history bars and complete72h future1m data solely for coverage/evaluator validity, not future outcome. Shuffle eligible timestamps once and accept the first50passing coverage and temporal-separation requirements. Case numbering is sampling order; never reorder by performance.

Exclude all SOL windows already present in any existing canonical simulation decision ledger. Further require at least122hours between new entry timestamps and any prior entry, and between new entries. This prevents overlap between the full50-hour indicator history and72-hour original bracket evaluation spans. It does not make all market regimes statistically independent.

Draw from the existing historical archive; new to these experiments, not a future live period. Reused archive, exploratory prior model/threshold selection and small subgroups limit generalization. Do not describe this as live proof or a chronological holdout. Prior datasets/source hashes and sampled-input hashes are recorded before model calls.

## Primary reversal policies

- H-SHORT: Terra LONG => strategy SHORT, fixed exit105minutes after entry.
- H-LONG: Terra SHORT => strategy LONG, fixed exit30minutes after entry.

Current above-both-MA condition holds in all sampled windows. Simulated entry at the last visible bar's close, consistent with prior experiments; exits use native1m closes at exactly30/105elapsed minutes. No SL/TP, trailing stop, additional confirmation or forecast update in these two strategies. This ignores inference latency and market impact; show next1m-open entry as a prespecified timing sensitivity, not an optimized alternate. Gross is primary; net subtracts fixed20bps roundtrip. Flat forbidden by unchanged agent contract. Report both gross-positive and net-positive trade rates, mean/median, count, dispersion, uncertainty; no leveraged or compounded portfolio claim.

Also record the original agent bracket outcome separately using the unchanged72h resolver; do not confuse it with the reversal trade.

## Controls and inference

Evaluate always-long and always-short at BOTH30 and105minutes on all50eligible windows, and keep the original same-direction return on each selected rule's identical window/horizon. For AI selection, compare the selected side/horizon mean with the same side/horizon on the entire eligible sample; use a permutation of Terra's long/short labels across the50windows that preserves label counts. Two primary selection tests (one per hypothesis), two-sided, BH correction. Report selected-return confidence intervals separately from incremental-selection inference. A selected return equal to its price-rule baseline is no AI contribution.

Bootstrap complete window rows10,000times, seed2026092902; fixed sample50, no optional stopping. Report gross-mean95%intervals and, where possible, chronological-half sensitivities within each triggered hypothesis. Broad-historical sample and asymmetrical subset sizes require cautious interpretation. Success requires more than a positive gross point estimate: disclose costs, uncertainty and incremental-baseline results. Do not test more exit horizons, find best confidence thresholds, or select a winner after viewing this batch.

All attempts retained, up to3validity retries; never retry on outcomes. Unsupported model/access failure is not a trade. Complete requested50or explicitly report missing slots. Existing data, decisions, reports and source code remain unchanged. New outputs in this run only.

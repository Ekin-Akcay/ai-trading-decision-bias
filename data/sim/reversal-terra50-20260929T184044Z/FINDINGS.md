# Fifty-window reversal test: neither rule establishes a profitable edge

Completed all 50 new historical SOL windows with gpt-5.6-terra, medium reasoning.50 independent sessions, full text/image audit, zero tools, no retries. Old files preserved. This is50 total setups, split42 SHORT trades and8 LONG trades by Terra's direction; not50 per strategy.

| Frozen rule | Trades | Gross-positive | Mean gross/trade | Mean net/trade |
|---|---:|---:|---:|---:|
| Terra LONG → SHORT,105 minutes |42|24/42 (57.1%)|−0.205%|−0.405%|
| Terra SHORT → LONG,30 minutes |8|5/8 (62.5%)|+0.049%|−0.151%|
| Combined |50|29/50 (58.0%)|−0.165%|−0.365%|

Net assumes20 bps roundtrip, not funding/borrow/market impact. These are arithmetic means per trade, not portfolio returns. Both rules had50% net-positive trades.

The short idea failed to reproduce its earlier positive gross estimate. Its average winner was+0.764%, while its average loser was-1.498%. A57% gross win rate therefore still lost money. The long idea had only 8 signals: its 4.9 bps gross mean did not cover20 bps assumed costs.

Against the same side/time baseline across all 50eligible windows, AI selection changed mean returns by −0.048percentage points for shorts and+0.022points for longs. Label-permutation p-values were 0.586 and 0.935; both BH-adjusted q-values 0.935. Neither result demonstrates incremental value from the AI opinion. Gross-mean 95% intervals: SHORT[−0.653%,+0.220%]; LONG[−0.533%,+0.602%]. Broad intervals do not prove zero effect; they fail to establish an edge.

Terra still chose LONG 42/50 (84%) in this above-both-MA sample. That is a directional preference conditional on the selected regime, not proof of systematically bad forecasts. Following its LONG calls for the same 105 minutes produced+0.205% gross and+0.005% net on those42 cases; that estimate also has an interval crossing zero and is not a new validated strategy.

Prespecified next-bar-open sensitivity (at the same entry timestamp) changes the combined mean only to−0.160% gross/−0.360% net. Both chronological halves lose after costs for H-SHORT; H-LONG changes from+0.068% net in the earlier4 cases to−0.370% in the later4. No extra horizons or thresholds were searched.

The original AI 2:1 bracket trades are recorded separately:18 TP,32 SL, mean+0.068% gross/−0.132% net. Those outcomes are not the reversal strategy. Each trade's original explanation, chart, bracket outcome, reversal price/time, minute-path excursions and returns are in the report and ledgers.

These are previously unused, separated windows from the existing historical archive, not live or chronological held-out data. Bootstrap/permutation inference assumes exchangeability; residual regime dependence and prior exploratory model/rule selection limit conclusions. MAs are intraday, not a daily macro filter. Source timestamps are treated as UTC. Primary entry at the visible close ignores inference latency; next-open sensitivity is not a latency simulation.

I would not call either reversal rule successful from this batch. The long hypothesis is still weakly measured because it fired8 times, but this run does not justify changing its horizon or optimizing a filter on these outcomes. Preserve this result as a failed/uncertain validation.

- [Complete HTML report](index.html)
- [All 50 strategy trades](strategy_trades.csv)
- [Summary with uncertainty and controls](summary.json)
- [Original AI decisions and bracket outcomes](../decisions/reversal-terra50-20260929T184044Z.jsonl)
- [Frozen protocol](../../research/reversal-ideas-20260929/PROTOCOL.md)
- [Idea archive](../../research/reversal-ideas-20260929/IDEAS.md)

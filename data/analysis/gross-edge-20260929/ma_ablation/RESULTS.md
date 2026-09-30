# SOL long replication and explicit-MA intervention

MA_A failed its frozen gross-profit replication criteria. The test did not establish that removing explicit MAs changes decisions more than ordinary model variation.

90 fresh SOL macro-bear windows;270 accepted isolated decisions;270 physical calls in this follow-up. Current-phase total: **771/800** new physical calls. Prior500-window failures are preserved. All trading returns below are unlevered and zero-cost.

| Arm | Role | Trades | Mean gross/trade | Win rate | Mean per opportunity |99% trade-mean interval |
|---|---|---:|---:|---:|---:|---:|
|MA_A|primary_profit_replication|71|-0.130%|46.5%|-0.102%|[-0.825%, +0.601%]|
|MA_B|repeat_diagnostic|67|-0.061%|44.8%|-0.045%|[-0.744%, +0.661%]|
|NO_MA|MA_input_intervention|72|-0.117%|47.2%|-0.093%|[-0.838%, +0.613%]|

Only MA_A is the prespecified profit replication. MA_B measures ordinary stochastic variation. NO_MA changes only the explicit MA20/MA50 chart lines, labels and text; all candles, volume, scale and non-MA statistics are held fixed. Each call is isolated and arm execution order was randomized.

The unchanged rule buys when the agent chooses SHORT, using the next minute open and a240-minute exit; otherwise it skips. Every selected market window already satisfies the original completed-day SOL≤50DMA and BTC≤200DMA gate.

## MA dependence

- Removing MAs changed 19/90 actions; repeating identical inputs changed 10/90.
- Excess change rate: 10.0%. Exact one-sided paired p=0.0317841, against the locked0.01 threshold.
- Discordant windows: treatment-only 14; repeat-only 5.
- SHORT frequency changed by +1.1% when explicit MAs were removed.

Dependence on an input is not a profitable signal. The model can still infer trends or approximate averages from visible prices. This intervention isolates explicit MA information, not every source of trend information.

## Long-rule replication

- Profit verified: **False**. Incremental AI selection verified: **False**.
- Quarter95% profit interval: [-0.491%, +0.217%].
- Same-entry price-only mean: -0.175%; macro plus below-MA20 price-only mean: -0.213%.
- AI increment after era/MA-stratum standardization: -0.036%;99% window interval [-0.226%, +0.105%].
- Chronological halves: -0.211%, -0.042%.
- Entry delayed1/5minutes: -0.122%, -0.123%.
- Remove largest3winners: -0.406%.
- Failed primary criteria: window99_lower_positive, quarter95_lower_positive, both_halves_positive, both_delays_positive, remove_best3_positive.

Secondary arm comparisons count a skip as zero and compare all90 opportunities, rather than comparing differently selected trade averages. They cannot rescue a failed MA_A primary:
- MA_B_minus_MA_A: +0.057% per opportunity;95% paired interval [-0.082%, +0.241%].
- NO_MA_minus_MA_A: +0.009% per opportunity;95% paired interval [-0.160%, +0.190%].

## Scope

These90 target paths were excluded from all earlier exposed feature/outcome periods. Each has a50-hour history and six-hour checked future; new windows are at least56hours apart. There are90 market observations, not270.42 of90 are in2022, so the locked quarter sensitivity matters. The sample is historical, not live; leverage, funding, spreads and liquidation are not modeled.

[Full interactive report](./data/sim/ma-ablation-sol90-20260929T210853Z/index.html) · [All positions](./data/sim/ma-ablation-sol90-20260929T210853Z/strategy_trades.csv) · [Summary](./data/sim/ma-ablation-sol90-20260929T210853Z/summary.json) · [Locked protocol](./data/analysis/gross-edge-20260929/ma_ablation/PROTOCOL.md)

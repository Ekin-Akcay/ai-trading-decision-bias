# Long recovery hypothesis — frozen before computing this rule

Question: can a bearish AI view of a short-term setup identify a subsequent long recovery during a broader uptrend? This is a new exploratory backtest on previously inspected windows, not confirmation.

Primary exact rule:
1. At the original decision time, the previous completed daily SOL close is above its50-day simple average and the previous completed daily BTC close is above its200-day simple average. Use daily rows strictly before the UTC entry date; no partial same-day data. This is a trend proxy, not a full macro model.
2. At least2of3 original OpenAI v2 models (Luna,Terra,Astra) choose short. One majority signal per canonical window; no pooled duplication. Original v2 inputs/rules unchanged.
3. Observe the next15-minute close; if strictly above the original decision price, qualify. Otherwise observe the30-minute close and qualify if strictly above. If neither qualifies, do not trade. This requires a close above the reference; no additional intrabar-dip condition is imposed.
4. Buy at the next available one-minute OPEN after that confirming close. Hold105minutes from actual entry and exit at the last1-minute close of that holding interval. No SL/TP in this diagnostic. Costs20bps roundtrip secondary; gross is primary.

Controls fixed before evaluation: exact same recovery+daily-trend rule without AI filtering; AI-short recovery without daily filter as a diagnostic, not an alternative winner. Report all three, event counts, per-trade returns, whole-window bootstrap95% intervals and chronological sensitivities where feasible. No threshold sweep, no selection of best holding time, no new AI calls.

Use existing 100 canonical windows. Export every eligible/triggered/skipped window with reasons, source hashes and validation. If too few macro-filtered events exist, report the result as underpowered; do not relax filters after observing outcomes.

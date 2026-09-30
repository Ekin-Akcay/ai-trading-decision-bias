# Direction and path study — exploratory plan, 2026-09-29

Question: What systematic directional behavior do AI decisions exhibit, and does that behavior relate to subsequent paths independently of brackets?

This is exploration of previously inspected historical data, not an untouched validation set. A pattern is not required to exist. Model reasons are brief reported explanations, not access to hidden reasoning. No decision or historical source data will be modified.

Scope: inventory every canonical simulation ledger. Main paired sample: the same 100 SOL windows, Luna/Terra/Astra/Haiku/Sonnet, v1 free geometry and v2 forced 2:1/no flat. Opus's 20 windows and early non-SOL/pilot windows are descriptive supplements. Controls are benchmarks, not additional AI observations. Do not duplicate copied matched-result files or count multiple models at one window as independent market events.

Entry convention: source window_end_ts is the OPEN of the last visible 15m bar. Entry is its close, at ts+15 minutes; first future 1m bar opens then. Verify against saved entry prices. Reconstruct fixed elapsed-time paths regardless of original bracket exit. Primary horizons: 15, 90 and 105 minutes (1, 6, 7 visible candle durations); additional exploratory horizons: 1, 5, 30, 45, 60, 75, 120, 180, 240, 360, 720 and 1440 minutes. Missing bars/horizons are explicitly excluded, never silently shifted. Report interval overlap.

Metrics: raw underlying returns; direction-signed fixed-horizon returns; return/entry ATR; directional accuracy; fraction of minute closes favorable; first excursion to +/-0.5 and +/-1 entry ATR; first-minute and first-seven-bar trajectory; MFE/MAE over fixed horizons; initial correct then reverses / initial adverse then recovers. MFE/MAE are full chosen horizons, not censored at exits. Intraminute both-barrier touches are ambiguous.

Behavior: long/short/flat rates, agreement with visible trend and MA20/MA50, behavior when indicators disagree, cross-model consensus, repeat stability v1 vs v2, normalized stop choices, confidence distributions, and fixed dictionary reason tags. Describe reasons on eventual losses only as post-hoc context, not executable conditioning.

Prediction tests: case-level bootstrap confidence intervals (10,000 resamples, fixed seed), sign/return statistics stratified by direction and visible trend, permutation comparisons preserving directional base rates, horizon-wide max-stat adjustment and Benjamini-Hochberg q-values within declared test families. Compare AI with always-long/short, simple price-vs-MA20 and visible momentum, including case-paired differences. Preserve direction proportions in shuffle baselines. For overlapping event days report sensitivity aggregated by UTC day. Five-fold grouped cross-validation is exploratory only: all rows at a window remain in one fold. Fit simple price-feature vs price-plus-AI predictors with fixed regularization; no threshold search or feature selection using forward returns.

Discovery: fixed candidate context cells (above/below both MAs, mixed MAs, visible trend, unanimous vs nonunanimous, confidence above/below each model's median, largest quartile absolute visible move/ATR). Include all cells and adjust within family; do not present best cell alone. Require useful sample counts and report chronological-half and leave-one-out sensitivity. Lexical associations may merely restate price features.

Output: reproducible script, source hashes, per-window minute paths, per-decision horizon/path metrics and reasons, inference tables, readable findings, and an HTML explorer covering each setup and every decision. Explicitly separate behavioral regularity, retrospective price association, and independently validated trading signal (none supplied by this study).

Implementation refinement after checking timestamps: three window pairs overlap within 24h (one within 105m). Cross-validation therefore also keeps events less than 72h apart in the same fold, rather than relying on window identity alone. No model/threshold selection is based on CV outcomes.

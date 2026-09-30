# Long candidates: measured results, 29 September 2026

## Candidate from the existing regime/horizon analysis

Hypothesis: buy against an AI countertrend short while price is above both intraday MA20 and MA50; exit after30minutes from the original entry. This is retrospectively selected from existing results, not a pre-registered confirmation.

Across the original five models and both v1/v2,50short decisions qualify on19unique windows. Each window is weighted once below, even if multiple models shorted it. Operationally this union means at least one of the ten recorded model/protocol opinions was short. A particular model, protocol or voting rule must be frozen before a future test; a different signal definition is not the same backtest.

| Long holding period | Gross mean per trade | Positive windows | Net mean at20bps cost |
|---|---:|---:|---:|
|15minutes|+0.1075%|10/19|−0.0925%|
|30minutes|+0.1283%|13/19|−0.0717%|
|105minutes|−0.0931%|7/19|−0.2931%|

The30minute gross median is+0.1059%. This fits a short-lived continuation story: AI shorts may be early in anticipating a reversal. It is a possible explanation, not a demonstrated mechanism. The favorable average does not cover our assumed20bps roundtrip costs. No statistical reliability or independent validation is established. The intraday moving-average condition is not a macro regime.

Full cases: countertrend_short_windows.csv. Exact summary/limitations: countertrend_short_candidate.json. Original upstream cells are preserved in ../exit-policies-20260929/posthoc_regime_direction.csv.

## The separately proposed daily-regime confirmed-recovery rule

I also tested the precise rule frozen in PLAN.md: previous-completed-day SOL>50DMA and BTC>200DMA; at least two of three OpenAI v2 models short; first15/30minute close above the original decision price; buy at the next1minute open and hold105minutes. The raw1minute entry/exit checks passed.

| Rule | Trades | Gross mean | Net mean at20bps |
|---|---:|---:|---:|
|Bullish daily regime + bearish AI + recovery|9|−0.0697%|−0.2697%|
|Same regime/recovery without AI filter|17|−0.3045%|−0.5045%|
|Bearish AI/recovery without daily filter|35|−0.0125%|−0.2125%|

The primary nine-trade gross-mean bootstrap interval is approximately[−0.657%,+0.755%]. Its negative estimate and tiny sample do not support promoting it as a profitable long hypothesis. The controls have different event subsets; differences are not a causal estimate of AI value. None of the three variants produces positive observed gross mean.

All calculations reuse the original100windows; no new model calls were made. Native verification: validation.json. Per-window eligibility, triggers and timing: windows.csv. Reproducible primary/control script: run.py. No thresholds were changed after inspecting the confirmed-recovery outcome.

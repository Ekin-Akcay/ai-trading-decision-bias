# AI reversal research ideas — 29 September 2026

This folder preserves the ideas, their discovery evidence, the frozen test rules and the completed results. Historical discovery estimates are hypotheses, not proof of reliable future returns. Returns below are arithmetic percentages per trade, not portfolio returns.

**The new 50-window test is complete. Neither selected rule established a profitable edge.** Read [results](RESULTS.md), [the full trade report](../../sim/reversal-terra50-20260929T184044Z/index.html), or the [frozen protocol](PROTOCOL.md).

## H-SHORT: short against AI longs above both intraday averages

Condition: price at or above MA20 and MA50 on the original 15-minute chart; model chooses long. Enter short at the decision-time close and exit 105 minutes later.

Discovery pooled 243 long opinions on 29 distinct windows across five models and two protocols: inverse mean +0.386% gross, or +0.186% after 20 bps assumed cost. That was retrospective selection. The new test fixes Terra alone, which differs from discovery's union of models.

New test: 42 trades, 24 gross winners, mean **−0.205% gross / −0.405% net**. No incremental AI-selection evidence (adjusted q=0.935). The positive discovery mean did not reproduce.

## H-LONG: buy against countertrend AI shorts for two candles

Condition: price at or above both intraday averages; model chooses short. Enter long at the decision-time close and exit 30 minutes later.

Discovery pooled 50 short opinions on 19 distinct windows: mean +0.128% gross, 13/19 positive, −0.072% net at 20 bps. The 15-minute mean was +0.107%; the 105-minute mean was −0.093%. Timeframe and filtering were selected retrospectively. The new test fixes Terra and 30 minutes before new decisions or outcomes.

New test: 8 trades, 5 gross winners, mean **+0.049% gross / −0.151% net**. No incremental AI-selection evidence (adjusted q=0.935). Eight observations provide weak precision; this does not establish profitability.

## H-RECOVERY: wait for a bearish call to fail in a broad uptrend

Previous completed daily SOL close above its 50-day average and BTC above its 200-day average; OpenAI v2 majority short; first 15/30-minute close above the original decision price; buy the following minute's open and hold 105 minutes from actual entry.

Earlier existing-data test: 9 trades, mean −0.070% gross / −0.270% net. Daily-trend/recovery-only control: 17 trades, −0.305% gross. No positive observed mean; small sample. No filter adjustments made after seeing the results. This idea was not included in the new 50-window test.

## Other ideas retained for research

- Buy against an AI short during a bullish daily regime: test whether the model overreacts to a pullback. Not independently validated.
- Follow AI longs during a bullish daily regime: compare with buying every eligible same-regime setup without AI. Not independently validated.
- Below-both-MA early continuation and later fading: 34/50 v2 majority shorts were favorable after 15 minutes (68%; one unchanged), versus 24/50 after 105 minutes. A few large winners support the later mean; the three best moves account for 82.8% of total signed movement. This may be a price-regime effect, not incremental AI information.
- Smaller brackets and time exits: 46 policies tested on 1,000 prior decisions. No primary modification established improvement. Half-width v2 target rate was 37.6% versus 37.4% originally; gross R was roughly unchanged while fee burden in R doubled. No geometry optimization in the new test.
- Price/volume-only input: v3 first 20 cases across three models completed. Direction changed in 12/60 calls; agreement with hidden MA20 remained 75%. Terra's 30-minute accuracy of 14/20 is a pilot lead, paired-return adjusted q≈0.289, not confirmed. V3 removes all supplied indicators and summaries, not only MAs.
- UTC entry sessions: small-group descriptive differences exist; no selected time-of-day filter has been validated.

## Evidence and reproducibility

- [Direction and path study](../../analysis/direction-paths-20260929/FINDINGS.md)
- [Exit-policy study](../../analysis/exit-policies-20260929/FINDINGS.md)
- [Daily-regime recovery study](../../analysis/long-recovery-20260929/FINDINGS.md)
- [V3 first-20 study](../../sim/pricevolume-v3-openai-20260929T173255Z/FINDINGS.md)
- [New-test results](RESULTS.md)
- [New-test protocol, frozen before sampling and model calls](PROTOCOL.md)

The selected run is recorded in `run.json`. It contains 50 total random, previously unused historical SOL windows, split across the two reversal rules by Terra's choices. Existing source data and reports are preserved. There was no outcome-based tuning in this batch.

## Deep follow-up: 280 additional isolated snapshots

[Full deep-research folder](../../analysis/reversal-deep-20260929/RESEARCH_PLAN.md) and [primary report](../../sim/reversal-validation280-20260929T194012Z/index.html).

Two rules selected from the first 150 Terra windows were frozen and tested on 280 new windows. Confirmed longs averaged +0.015% net across 85 trades; capped short reversals averaged +0.008% net across 91. Both failed the prespecified verification criteria despite slightly positive averages. The report retains exact strategy rules, uncertainty, timing/cost stresses, price-only controls and every model explanation. Broader follow-up grids are explicitly exploratory and do not replace these results.

Deep investigation completed: [master results](../../analysis/reversal-deep-20260929/RESULTS.md). The expanded 11,295-definition family included BTC hedging and stop-out timing. None survived the complete search correction. Stronger-looking long leads are retained as unverified hypotheses; neither old results nor failed primary tests were removed. No further model calls were spent simply to fill the 300-call limit.

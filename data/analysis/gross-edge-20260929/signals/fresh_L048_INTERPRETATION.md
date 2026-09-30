# Fresh L048 audit and interpretation

Independent native-data audit passed for `gross-edge-500-20260929T204545Z`, after root explicitly released the seal. All500 valid decisions and their unique isolated sessions were checked. The scorer independently rebuilt prior-day asset50DMA/BTC200DMA gates, original intradayMAs, native minute entry/240-minute exit prices,1/5-minute entry delays, MAE/MFE and scheduled15/30/60/105/240-minute moves. All500 L048 ledger rows matched root across27fields(13,500 field comparisons), with control, complement, delay and per-asset summaries also matching. No new model calls were made by this audit.

## Result: positive observed return, failed verification

L048 executed101 trades in38 of125 calendar blocks, out of500 asset-window opportunities. It returned **+0.3607% mean gross**,53/101winners(52.5%), median+0.0067% and gross profit factor1.773. One- and five-minute delayed entries still averaged+0.3549%/+0.3186%. Both chronological halves were positive.

These point estimates did **not** verify the rule. The simultaneous97.5% calendar-block interval is **−0.3809% to+1.1944%**; the ordinary95% quarter interval is **−0.2117% to+1.0227%**. Both contain losses. The latest chronological third averaged−0.1706%, despite the positive two-half summary. Preserve the frozen failed criteria rather than redefining success around another slice.

## Cross-asset transport remains uncertain

| Asset | Trades | Mean gross |
|---|---:|---:|
| SOL |24|+0.8895%|
| BTC |26|−0.0077%|
| ETH |24|+0.1489%|
| DOGE |27|+0.4335%|

The average is positive in three assets, and all leave-one-asset-out means are positive. That is compatible with some transport, but the pooled primary interval failed and each asset has only24–27trades. SOL's strongest mean is not a separately verified SOL strategy. Its largest trade(+14.9952%) supplies70.2% of its summed signed return, and removing its three best trades turns its mean negative.

## Most observed profit is explained by the declared price conditions

The identical daily-gate long control without AI selection averaged+0.2972% across149trades. After standardizing this price-only baseline to the selected asset×era×intraday-MA strata, it averaged **+0.3400%**. L048 added only **+0.0206percentagepoints**; its simultaneous block interval is **−0.0680to+0.1035points**, and quarter95% interval is−0.0577to+0.0871. Incremental AI value was not verified.

80of101selected observations lie in strata where every eligible observation was AI-selected. In those strata the selected and price-control means are identical by construction. Only21selected observations in11mixed strata provide the direct selection contrast. This is consistent with AI decisions largely reproducing coarse price conditions; it does not establish that arbitrary AI errors can be converted into an independent edge.

The additional prespecified price-only control(daily gate plus original price below intradayMA20) has a higher point estimate:+0.7245% over68trades. It remains a diagnostic control, not a replacement winner declared after the primary test failed. Its mean alone cannot demonstrate superiority or validated profitability.

## Calendar concentration

An additional descriptive audit of the native-verified L rows found that the2024-08-07 22:30UTC block contributed25.2060 summed trade-percentagepoints across four assets,69.2% of the total signed L return. Excluding that block leaves+0.1157% per remaining trade; excluding the three best blocks produces−0.1270%. These exclusions are sensitivity diagnostics, not revised trading rules. The event clustering explains why101 trades do not supply101 independent market episodes and why the preregistered block intervals are wide.

The source calculations and primary criteria remain unchanged. The historical test shows a positive gross realization but does not verify profitable cross-asset transport or additional AI selection value. No fee assumption is added to this phase: all figures above use the user's requested zero fees.

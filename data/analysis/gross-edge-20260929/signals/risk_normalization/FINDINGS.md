# L048 risk-normalization diagnostic

**The fresh pooled result becomes less compelling after accounting for pre-entry volatility. AI selection adds no demonstrated value under either normalization.** A narrowly defined SOL replication would be scientifically legitimate, but a paired MA-present/no-MA experiment is the more informative next use of model calls if the question is specifically whether AI mistakes create the edge.

Only three fixed representations were used, with the exact original L048 gate, selected trades, entry and240-minute exit unchanged: grosspercentage, grosspercentage/ATR14percentage, and grosspercentage/sigma2dpercentage. ATR and sigma values are pre-entry features. The normalized figures are movement per unit of pre-entry volatility, **not leveraged portfolio returns**. This diagnostic makes no new primary claim and preserves the failed500-window primary test.

## Same selected trades across all representations

| Cohort | Selected trades | Mean gross | Mean ATR units | Mean sigma2d units |
|---|---:|---:|---:|---:|
| Original150SOL windows |22|+0.2116%|+0.2900|+0.3780|
| Later280SOL windows |65|+0.5351%|+0.4761|+0.7080|
| Fresh500four-asset windows |101|+0.3607%|+0.1072|+0.3476|

For the fresh500, the ordinary block95% interval is−0.7886to+0.9649ATR units and−1.0155to+1.7279sigma units. Both include substantial negative values. The quarter intervals also include zero. The earlier65-trade cohort's normalized ordinary intervals cross zero too, despite its positive unnormalized interval. Normalization therefore does not reveal a stable hidden signal that the raw-percentage analysis missed.

## AI versus the same price conditions, fresh500

| Representation | L048 AI-selected mean | Same macro gate, no AI | Macro gate + belowMA20, no AI |
|---|---:|---:|---:|
| Grosspercentage |+0.3607%|+0.2972%|+0.7245%|
| ATR units |+0.1072|+0.1120|+0.6105|
| Sigma2d units |+0.3476|+0.3494|+1.1628|

The asset×era×intraday-MA-standardized AI increment is+0.0206percentagepoints for rawgross, **−0.0485ATR units**, and **−0.0660sigma units**. Their simultaneous block97.5% intervals are respectively[−0.0680,+0.1035],[−0.1818,+0.0625], and[−0.2790,+0.1082]. No representation demonstrates positive additional AI selection value. The intraday-MA20 control's stronger point estimates remain diagnostics; their block95% intervals also cross zero and they cannot replace the failed primary.

The lack of identification is unchanged by rescaling:80of101 selected observations belong to strata in which all eligible observations were selected. Only21selected observations in11mixed strata provide a within-stratum AI/control contrast.

## Temporal concentration persists

The2024-08-07 22:30UTC block is the largest contributor under all three measures. It represents69.2% of summed signed raw return,226.2% of summed signed ATR-unit return, and121.9% of summed signed sigma-unit return. Values above100% mean the remaining blocks collectively offset part of that one block's gain; they do not describe portfolio returns.

Removing the best three temporal blocks leaves−0.1270% gross,−0.3985ATR units and−0.4938sigma units. The macro-only control also becomes negative after removing its best three blocks. The macro+belowMA20 control leaves+0.0544% gross,−0.0855ATR units and approximately+0.0003sigma units. Neither volatility scaling nor the obvious price-control comparison resolves event concentration.

Original150 and later280 are single-asset datasets, so each timestamp block contains one SOL observation; their block concentration coincides with trade concentration. Original22 selected trades turn negative after the best three are removed in every measure. Later65selected trades remain positive after the best three are removed in every measure. These different outcomes support uncertainty, not a universal rule that every positive result depends on one winner.

## Is a SOL-only replication worth additional calls?

The SOL point estimates remain positive across all three cohorts after normalization. Fresh SOL contributes24trades with+0.8895% raw,+0.3906ATR units and+1.1437sigma units. Its standardized AI increments are positive(+0.1445percentagepoints,+0.0973ATR units,+0.1827sigma units), but only8of24selected observations are in mixed strata. Removing its top three trades gives−0.2392% raw,−0.2651ATR units and−0.3406sigma units. These are not enough observations to establish stable SOL-specific AI value.

A fresh, fully locked SOL-only replication of the exact rule could answer the narrower question of whether its SOL gross mean persists, especially if sampling is restricted prospectively to the already-declared daily macro gate without looking at future returns. It must remain a new replication, not a reclassification of the failed cross-asset test. It should retain the no-AI daily control, belowMA20 control, calendar-block uncertainty and AI-increment test. Merely increasing the number of model calls in strata where AI always predicts the same action will add little evidence that AI itself is needed.

**Priority recommendation:** use a separate, fixed paired input-ablation study on identical fresh windows. One isolated decision receives the unchanged MA-present input; the paired decision receives the same price/volume history with MA fields and overlays removed. Compare direction changes and the fixed strategy's paired gross outcomes against the same prespecified price-only controls. Pair by window, preserve the calendar blocks, and freeze the sample and endpoints before collection. This directly tests the suspected input-induced trading bias; it does not guarantee a profitable strategy. Do not add new exit searches or use failed conditions as permission to change the primary after viewing outcomes.

All detailed results, asset means, standardized increments and per-block contributions are retained in this folder. The current500 diagnostics reuse the exact frozen block and quarter bootstrap weights and reproduce the original raw L048 primary and AI-increment intervals. Original150 uses block seed2026093061/quarter seed2026093062; later280 uses2026093062/2026093063. No model calls were made, and source files remain unchanged.

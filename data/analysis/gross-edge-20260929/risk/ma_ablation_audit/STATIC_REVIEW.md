# MA-ablation economic review before release

Reviewed the frozen three-arm protocol and `ma_ablation/evaluate.py` statically, without opening fresh forward prices or return artifacts.

The economic comparison is correctly defined on all 90 paired opportunities. Each arm's SHORT decision takes the same long payoff; its LONG decision skips with payoff zero. NO_MA−MA_A and MA_B−MA_A therefore compare paired opportunity returns, not incompatible conditional trade averages. Both quarter-resampled numerators and denominators account for variable numbers of windows in a quarter.

The sole profit replication is MA_A. Its code requires the frozen minimum 50 selected trades, positive 99% window interval lower bound, positive 95% quarter interval lower bound, positive chronological halves, positive 1/5-minute delayed entry means, and positive mean after removing the three best trades. Neither MA_B nor NO_MA is allowed to become `profit_verified` or `AI_increment_verified`, even if its diagnostics look attractive. The macro price-only and below-MA20 controls have no model-dependent gate. The comparison uses the same fixed 240-minute exit clock in all arms.

No economic logic defect was identified. Reporting must keep these distinctions explicit:

- `selected.win_rate` is the executed-trade win rate. `opportunity.win_rate` is the fraction of all sampled opportunities returning a positive payoff; it counts skipped windows as zero, not wins. Do not label the latter a trade win rate.
- Arithmetic sums of trade percentages are concentration diagnostics, not compounded portfolio return. Ninety opportunities and 270 independent model calls still yield only 90 market outcomes.
- Higher NO_MA conditional trade mean can result from changed trade count. Its paired per-opportunity difference is the prescribed economic intervention comparison, and remains secondary.
- A positive MA-information flip test establishes sensitivity to the explicit MA bundle, not an economic edge. Neither flip significance nor secondary-arm profit rescues failed MA_A criteria.
- Zero-cost returns remain gross, unlevered historical returns. Delayed entry is a sensitivity, not a separate primary.

The dormant `audit.py` requires a matching explicit `--release` argument, an existing `ALLOW_EVALUATION` marker, all 270 accepted unique sessions, and passing isolation records before reading any economic output. It will independently reconstruct payoff/skip economics from the final ledger, verify support/half/quarter/tail summaries and all profit criteria, compare serialized bootstrap quantiles and paired opportunity arithmetic, and report payoff concentration. It deliberately does not duplicate the other agent's native-minute or daily-gate audit.

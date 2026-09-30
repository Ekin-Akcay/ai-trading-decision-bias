# Same-moment pattern tests

This pass found one coherent **exploratory price/volume lead**: shorting a quiet rally. It is based entirely on moments where AI decisions already existed. No new trade-agent calls or new sampled dates were used. The remaining 29 snapshot credits are preserved.

The lead is a price-only comparison rule that emerged from the volume study. It does not establish that AI consistently makes the wrong directional call. All outcomes have already been studied, and every favorable result here remains exploratory.

## Exact rule

Wait 30 minutes after an existing AI snapshot. If price has risen at least half of the original ATR14 and those 30 minutes have at most 75% of the median 30-minute volume from the preceding 50 hours, short at the next minute open. Exit after 120 complete minutes. No AI-direction filter, stop or target.

ATR is the pre-entry value already supplied in the original snapshot. Both volume sums use native minute data; the reference is 100 consecutive 30-minute sums before the snapshot. The feature becomes known at elapsed 30 minutes; entry is minute 31 open and exit minute 150 close. One original window lacked complete volume history and was excluded from all volume policies, leaving 1019 eligible windows.

## Observed result

| Measure | Result |
|---|---:|
| Executed positions / original-entry clusters |56 /46|
| Wins |34 /56 (60.7%)|
| Mean gross per trade |+0.3921%|
| Median gross |+0.1209%|
| Average winner / loser |+0.9682% /−0.4982%|
| Gross profit factor |3.00|
| Worst / best position |−2.9184% /+9.1835%|
| Mean after removing best entry-time cluster |+0.2323%|
| Mean after removing best 3 entry-time clusters |+0.1038%|
| Chronological halves |+0.4976% /+0.2939%|
| Entry delayed 1 /5 minutes, still held 120 minutes |+0.4070% /+0.3468%|

All five chronological groups and all seven sampled calendar years have positive means. Four of five source cohorts are positive; the above-MA enriched next50 cohort contributes only two trades and averages −1.2479%. All four asset means are nonnegative, but BTC is effectively flat on six trades. Most observations are SOL (36 of 56). These splits support further investigation; they are not independent holdouts.

The original ordinary quarter-bootstrap 95% interval is+0.0798% to+0.6889%. The 14-definition volume-family interval includes zero. Across all 44 definitions in this pass, the conservative simultaneous interval is **-0.1738% to+0.9349%**. None of the 44 definitions has a positive whole-search lower bound. That correction still does not erase earlier adaptive research history. This is an observed gross result, not verified future profitability.

## What the comparisons say

The same upward half-ATR geometry without the volume filter averages −0.0202% across 248 shorts. Unconditional shorting at the same delayed clock averages+0.0123% across 1019 positions. These are post-score diagnostic comparisons, clearly separated from the original frozen family. The quiet-rally rule's conditional mean is higher, but its paired opportunity-return improvements remain uncertain: +0.02646 percentage points versus geometry alone and +0.00927 points versus unconditional shorts; both intervals include zero. They do not establish a causal volume effect.

The lead only trades 5.5% of eligible snapshots. Its mean per original eligible opportunity, counting skips as zero, is+0.02155%; the+0.3921% figure is per executed trade. Neither is an annualized, compounded or leverage-adjusted account return.

Splitting the same quiet-rally positions by original AI action gives 40 trades averaging+0.4614% when the AI had already said SHORT, and 16 averaging+0.2190% when it had said LONG. This split was inspected after the original result and is descriptive. The stronger subset **follows a bearish call after waiting for a counter-move**. It suggests an entry-timing hypothesis; it does not prove incremental AI value or justify retrospectively restricting the rule.

For long trades, the quiet-down/AI-LONG partition averages+0.1287% over 37 positions, but falls to−0.0297% after removing its three best market events. The declared long candidates lose. There is no comparably coherent long lead from this pass.

## Other ideas tested

- Protecting reversed positions with breakeven, trailing stops or partial profit-taking: means -0.0498%, -0.0699% and -0.0485% over 1020 positions. The unchanged 240-minute hold is+0.0550%. These management rules reduced returns.
- BTC recovering while an AI-bearish asset lags: the two long policies average−0.1173% and−0.1494%. Both mirrored short policies and all direct price-only gates also lose.
- High-volume recovery/rejection and quiet directional extensions with an AI-reversal filter: the long policies lose; the positive short cells become negative after removing their best 3 market events.

There were 11 initial candidate definitions and 26 declared controls/comparators, followed by seven explicitly post-score diagnostics. All 44 vectors (43 unique) are retained. No parameter grid, new model opinion or extra market moment was added.

## Files

- [HTML trade inspector](index.html): all 56 quiet-rally positions, original AI reasons, prices and interactive paths.
- [All 56 trades](quiet_rally_trades.csv): entries, exits, returns, volume/price features and top-event flags.
- [Volume study](volume_reaction/RESULTS.md), [BTC reaction study](market_reaction/RESULTS.md), [managed exits](managed_exits/RESULTS.md).
- [All current results](joint_results.csv), [joint uncertainty calculation](joint_audit.json), and independent audit artifacts in audit/.
- [Post-score diagnostics](volume_reaction/POST_SCORE_DIAGNOSTICS.md) records exactly what was added after seeing results.

Earlier decisions, reports and the 771-attempt budget ledger remain unchanged. Numerical audits verify the simulated executions and statistics; they do not convert exploratory findings into a demonstrated market edge.

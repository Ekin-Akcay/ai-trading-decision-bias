# Review of the two AI timing hypotheses

These are **follow-the-AI after a quiet countermove** hypotheses. They give the actual AI direction an explicit selection role, but they do not support the original claim that AI direction is generally wrong. Both partitions were noticed after earlier outcomes were inspected; all numbers here are discovery evidence. This review uses only old files, with no new calls or fresh outcomes.

| Old-data measure | Quiet rally / AI SHORT → SHORT | Quiet decline / AI LONG → LONG |
| --- | ---: | ---: |
| Trades / original-time blocks |40 /37|37 /32|
| Mean gross/trade |+0.46135%|+0.12874%|
| Quarter95% mean interval |[+0.10684%, +0.79586%]|[-0.10039%, +0.39414%]|
| Same price/volume gate without AI |56 trades, +0.39212%|69 trades, +0.00751%|
| Opposite-AI partition, same executed side |16 trades, +0.21904%|32 trades, -0.13267%|
| Conditional increment versus all gate trades |+0.06923 points|+0.12123 points|
| Quarter95% interval for that increment |[-0.04294, +0.18632]|[-0.03122, +0.27549]|
| Gross after removing three best market events |+0.05251%|-0.02965%|
| Opportunity increment versus trading every gate |−0.06258 points/gate|+0.06153 points/gate|

The short has the stronger gross-return lead; its AI-specific value is weak because omitted positions also made money. The long has a more interesting directional selection contrast but a weaker, tail-sensitive profit result. Neither is established. An additional old-data cohort×asset×year adjustment gives +0.04100 points for the short (95%[-0.03035,+0.11133]) and +0.08855 for the long ([+0.01257,+0.16495]); only14 and21 selected observations, respectively, have a selected/nonselected contrast in those strata. The nominal positive long interval is post-selection and cannot establish causality or independent confirmation. The new fixed-effect test uses its separately frozen asset×MA20 strata, not these retrospectively reviewed groups.

## Exactly two proposed hypotheses and controls

Preserve the existing Terra/medium, MA-present, 40-visible-bar snapshot at t0. Hide all subsequent observations, sampling gates, dates/assets and strategy details from the agent. Observe30 complete minutes, with O/C as first open/last close, original ATR14 price distance O×ATR, and volume ratio relative to the median of100 prior30-minute volume sums.

1. If the agent said SHORT, C−O >=0.5×O×ATR, and volume ratio<=0.75, short at t0+30-minute open and hold120 minutes.
2. If the agent said LONG, O−C >=0.5×O×ATR, and volume ratio<=0.75, buy at the same clock and hold120 minutes.

For each, the exact price-only control executes **every** matching price/volume gate in the same side and at the same entry/exit. Keep the AI-opposed subset as the complementary comparison, and retain the frozen MA20-only selector. Report both per-executed-trade and per-price-gate returns with skipped trades zero. A good gross price pattern with no AI increment must be labelled as such; it does not justify further inference spending.

The genuinely new question is whether the AI's *earlier* direction discriminates a successful later countermove fade, with matched fresh price gates. This is different from retuning old L048/S508 or modifying every original bracket. Do not add confidence, alternate models, new thresholds, volume bins or hold lengths within this experiment.

## Budget and decision recommendation

The frozen protocol's **60 screen opinions (30 per direction), up to120 confirmation opinions, and20 operational-retry attempts** is a sensible allocation of the new200-attempt cap. Keep the old29 untouched. Price-pattern enrichment is essential: uniform random calls previously produced only56 quiet-up and69 quiet-down gates per1,019 opportunities. Screen only using values available by t0+30, then deliver the agent the frozen t0 snapshot; never select using the subsequent120-minute payoff. Keep all sampled AI-opposed calls, because they identify AI value. Balance assets/years independently of outcomes and avoid synchronized duplicate events.

Use the registered noninferential screen exactly: at least5 aligned and5 opposed, positive aligned mean, and positive raw aligned-minus-opposed spread. Neither passes → stop and preserve the remainder. One passes →120 confirmation cases for it; both pass →60 each. Choose no replacement cases or alternative rule after seeing screen results. Confirmation outcomes stay sealed until all its calls and isolation audits finish; do not pool the screen into confirmation.

The frozen confirmation standard appropriately requires both family-adjusted positive lower bounds—gross return and asset×MA20 fixed-effect AI spread—plus mixed-stratum counts, positive halves, and a positive best-three-removed result. These test a useful conditional historical selector, not retail psychology or live profitability. A positive point mean with an interval crossing zero is **not verified**; an upper interval below zero is stronger evidence against a positive edge. Lack of significance alone does not prove no effect, and it does not justify extra calls beyond the cap.

Power is limited. At the old observed mean and standard deviation, a simple independent-observation calculation suggests about121 selected short trades (roughly169 price-gated calls) or273 selected long trades (roughly510 calls) for80% power using an ordinary two-sided95% test. This ignores clustering, multiple testing, selection bias and weaker future effects, so it is optimistic. Splitting confirmation60/60 is particularly unlikely to establish a small long edge. The phase is a controlled attempt to reject or strengthen two ideas, not a promise that200 calls can force a verified strategy.

Supporting calculations and immutable old-source hashes: `old_signal_statistics.json`, reproducible with `review_old.py`. No old files were modified.

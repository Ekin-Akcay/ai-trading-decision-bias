# Frozen test: AI direction after a quiet countermove

This phase tests whether an original AI direction becomes useful after a low-volume move against it. The two hypotheses came from retrospective analyses of the existing 1,020 Terra decisions. They are exploratory leads, not established strategies. This document is frozen before any new trade-agent call or new post-entry payoff is examined.

## Two hypotheses and exact trading clock

At time t0, give one isolated gpt-5.6-terra process (medium reasoning) the original forced-2:1, no-flat contract, anonymized text and chart: 200 historical 15-minute bars for indicators and 40 visible bars, with price rebased to 100. The last visible candle opens at t0−15 minutes and closes at t0. Preserve the MA-present stimulus to test the existing lead without changing the treatment. The model does not know sampling conditions, calendar/asset identity, later observations or the evaluation rule. Its requested bracket describes the original hypothetical decision; only its direction selects our separately evaluated delayed trade.

Observe the next 30 complete one-minute candles. Let O be their first open, C their last close, and ATR be original ATR14 as a fraction of original price. Let V be their volume sum divided by the median of 100 non-overlapping 30-minute volume sums immediately before t0 (50 hours).

- Short hypothesis: C−O >= 0.5×O×ATR, V <= 0.75, and original AI action SHORT. Enter SHORT at t0+30 minutes.
- Long hypothesis: O−C >= 0.5×O×ATR, V <= 0.75, and original AI action LONG. Enter LONG at t0+30 minutes.

Enter at the native open of the next minute after observation completes. Exit at the close of the last of 120 complete held minutes, at t0+150 minutes. No stop, target, leverage, fee or funding adjustment is fitted. Gross percent return = side×100×(exit/entry−1), with side +1 for long and −1 for short. This is historical unlevered notional return, not account equity or net profit. Invalid/missing data are excluded only by coverage/validity criteria, never by realized profit. Baseline case numbering and model opinions are immutable.

## Fresh conditional sample

Use the sampler and its frozen design artifacts. Candidate t0 values lie on UTC half-hour boundaries in the available SOL, BTC, ETH and DOGE archives. Both 50-hour input/volume history and forward timestamp coverage must be complete. The sampler may inspect only pre-execution values through t0+30 minutes; it must not derive post-entry prices or returns. Selection enriches on the two price/volume gates. Thus this is a conditional study of eligible signals, not a uniform market sample or a test of natural signal frequency.

Exclude any new trade interval [t0+30m,t0+150m) overlapping globally with the 681 earlier exposure intervals in the last fresh-block inventory or the 783 scored four-hour proxy-replication targets. Exact previously queried window IDs and original query times are excluded. Require one selected event per UTC day globally and no overlap between selected trade intervals. Input history may reuse previously observed prices; freshness refers to unscored post-entry target intervals, not unknown-to-the-model market history or inaccessible raw files.

Freeze an ordered 60-case screen (30 up, 30 down) and up to 120 potential confirmation windows per direction before collecting opinions. Assets and available years are balanced by the sampler, with a fixed seed and documented coverage constraints. Potential windows not called do not count as model decisions or scored targets. Never replace a case because of its answer or payoff.

## Budget and continuation

This phase has its own 200-physical-attempt cap. Every attempt, including timeout/invalid-output retries, is durably reserved before launch. Up to 180 valid opinions are planned and 20 attempts are reserved for operational failures. Maximum three attempts per case; accept the first valid isolated answer, never choose between answers. No replacement windows. The old allowance has 29 unused attempts, left untouched.

Collect and audit all 60 screen opinions before opening screen outcomes. A direction passes this inexpensive screen only if it has at least five AI-aligned and five AI-opposed cases, aligned mean gross return >0, and aligned-minus-opposed mean return >0. This screen is noninferential and cannot verify the hypothesis.

- Both directions pass: collect the first 60 confirmation cases per direction.
- Exactly one passes: collect its full 120-case confirmation reserve.
- Neither passes: stop this experiment after screening and preserve unused credits.

Confirmation sample sizes are fixed by these rules, without interim scoring. Complete collection and isolation audit before opening any confirmation outcome. Screen and confirmation results are always reported separately; pooling cannot support confirmation claims. No extension because a p-value is close. Another research hypothesis, if developed later, requires a new declared experiment and new target periods, and remains within the phase's unspent allowance.

## Controls, statistics and claim standard

For each direction, the price-only control trades every sampled gate in the same direction with identical entry/exit. The AI-opposed subset is the complementary gate. A MA20-only control takes a short when original price is below MA20, or a long when above/equal MA20. Report its conditional and per-gate return. Also report skips as zero for all policy opportunity averages, so higher conditional profit cannot disguise lost total opportunity profit.

Two primary statistics per direction are (1) AI-aligned mean gross return and (2) the aligned-minus-opposed return spread adjusted for asset × original MA20 side. For (2), regress gate-direction return on binary AI alignment and eight possible asset/MA20-side fixed-effect strata: beta = sum((A−mean(A within stratum))×R) / sum((A−mean(A within stratum))²). Only mixed strata identify the slope. Report raw spread, mixed-stratum counts and each stratum's composition. This tests incremental selection relative to these explicit coarse price controls; it does not prove added information beyond all possible price features, causation or retail-trader behavior.

Confirmation uses 40,000 bootstrap samples of complete calendar-quarter clusters, seed 2026093051. Recompute means and fixed effects within each bootstrap draw. For each of the four planned primary statistics, report an ordinary 95% interval and a conservative one-sided 98.75% lower bound (Bonferroni family of four), retaining the family size even if only one hypothesis reaches confirmation. Undefined bootstrap statistics count as minus infinity for lower-bound decisions, and the undefined fraction is reported. Use an empirical order-statistic quantile (no interpolation at infinite values) and retain all confirmation quarters in the resampling universe.

A hypothesis is confirmed in this historical conditional sample only if both simultaneous lower bounds exceed zero, it has >=10 aligned trades and >=10 opposed trades within mixed price strata, its aligned mean is positive in both chronological halves, and its aligned mean remains positive after removing its three largest winning events. Otherwise distinguish observed positive gross returns from insufficient evidence or a failed hypothesis. This protocol cannot establish live profitability.

Report per-direction number of signals, win rate, mean/median, profit factor, average win/loss, best/worst, MFE/MAE, halves, assets, years/quarters, leave-best-1/3-out, and AI action/confidence/reason beside each historical trade. These are diagnostics, not an additional parameter search. All results, exclusions and failures remain in the research record.

## Isolation, preservation and reproducibility

Each physical call starts a fresh noninteractive Codex process and fresh empty working directory. Disable model tool access, browser, memories, plugins, dynamic skill discovery and inherited project instructions. The standard runtime system instructions and generic built-in skill catalog may still be present; freeze their hashes and reject inherited task/project context. The task input is the frozen text and image; copy the image to neutral chart.png. Hash requests and delivered image bytes; audit exact user-message allowlist, single context, model/effort, absence of tool calls, unique transcript/session and exact final answer. Audit before scoring. Record original file hashes and verify the old budget is unchanged.

The runner follows the documented noninteractive CLI pattern (https://learn.chatgpt.com/docs/non-interactive-mode), with local feature/configuration checks and transcript validation as the evidence of actual delivery. Local scripts, manifests, sampled windows, opinions, all attempts, scores, decisions to continue/stop and independent audits are durable. No real orders are placed.

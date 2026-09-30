# Independent design and isolation review

Reviewed before new model calls or new post-entry outcomes. This review is confined to the new `ai-timing-200-20260930` experiment; the previous 29 unused credits and old files remain separate. No model or API calls were made for this review.

## Design conclusion

The two fixed hypotheses are suitable for a bounded historical confirmation attempt. They test whether the original AI direction selects profitable entries after a quiet countermove. They do not test unconditional reversal of AI decisions. The entry condition uses information available at execution: the model sees only its original t0 history, the sampler observes the subsequent 30 minutes, and the trade begins at t0+30. Conditioning on that observed gate is legitimate, provided no t0+30-to-t0+150 return influences eligibility or allocation and the condition is not disclosed to the model.

Freshness is relative to the enumerated prior target exposures. Historical inputs may overlap earlier work; the model may have encountered historical markets during training. A new sample from an old archive is not a prospective live-market test. Results describe the quiet-move population, not natural signal frequency or general market profitability.

## Frozen allocation and continuation

Freeze 60 screening windows (30 per direction) plus ordered reserves of 120 confirmation windows per direction before collecting opinions. At most 180 valid opinions are collected: both screens pass → 60 confirmation each; one passes → 120 for that direction; neither passes → stop after the screen. The 200-attempt allowance includes 20 operational retries, with no transfer from the old allowance. Uncalled reserve windows must not be scored. Retries use the same case; do not replace or select an answer because of action or payoff.

For screening, require at least five aligned and five opposed calls, positive aligned mean gross return, and positive raw aligned-minus-opposed spread. This is a noninferential continuation rule. A ten-per-action screen threshold would discard many plausible short samples simply because the previous aligned rate was about 71%, leaving fewer than ten rejected calls on average in a 30-case screen.

Confirmation must remain sealed until all authorized confirmation opinions pass isolation audit. Screen outcomes must not contribute to confirmation confidence bounds. Do not alter thresholds, horizons, strata, allocation rules or model after the screen. If collection is incomplete because the retry cap is exhausted, report incompleteness and missingness; do not substitute windows.

## Primary statistics and claim separation

The frozen protocol's two statistics per direction are appropriate:

1. Mean gross return among AI-aligned trades.
2. The within-asset/MA20-side aligned-minus-opposed spread, computed as the fixed-effects slope of gate-direction return on AI alignment after centering alignment within each of eight possible asset × original MA20-side strata.

Only strata containing both actions identify statistic 2. At least ten aligned and ten opposed cases must lie in those mixed strata for an AI-increment claim. Report their count, distribution, and contribution explicitly. If AI always reproduces MA direction within a stratum, it contributes no identifying variation, regardless of how profitable the price regime is.

Reestimate stratum proportions in every resampled calendar-quarter draw; never freeze the full-sample control mean while resampling selected outcomes. Include all confirmation quarters in the resampling universe, including quarters without selected trades. A zero slope denominator is undefined, not zero effect. The fixed family of four one-sided 98.75% lower bounds is a conservative transparent standard even when only one hypothesis proceeds. All four should be reported where defined. The two bounds for a hypothesis must both be positive, with the protocol's mixed-support, chronological-half and concentration requirements, before a confirmation claim.

Use a direct empirical order-statistic lower quantile if undefined bootstrap values are assigned minus infinity. Linear interpolation involving infinity can produce NaN; report the undefined fraction and never discard undefined draws only because doing so improves the bound. Forty thousand quarter resamples estimate conditional sampling uncertainty; they do not create more independent calendar regimes. Publish the number of eligible/selected quarters and the distribution of counts.

Maintain separate interpretations: positive gross policy expectancy, selection value over the specific asset/MA20 control, and an overall compound confirmation claim. A profitable price-only gate remains economically interesting if AI adds nothing; it is not evidence for AI being wrong. Positive incremental selection with negative absolute return is not a profitable strategy. An increment over these coarse fixed controls does not prove information beyond every possible price feature or a causal effect of AI. Direction permutations conditioned only on MA20 may leave asset/time confounding and should not replace the prespecified cluster analysis.

## Realistic resolution

With 60 confirmation gates and roughly 40 aligned/20 opposed opinions, even independent observations have spread standard error about 0.274 times the return standard deviation. A one-sided 1.25% test with approximately 80% power needs a spread about 0.84 times that standard deviation. For a 1%–1.5% return standard deviation, that is roughly 0.84–1.26 percentage points, before dependence and stratum losses. The aligned-mean detectable scale is about 0.49–0.73 percentage points. Reallocating 120 cases to one surviving direction improves these illustrative scales to approximately 0.61–0.92 points for the spread and 0.34–0.50 for the aligned mean, assuming 70% alignment.

These are illustrative normal-approximation scales, not a power estimate using any new outcome. The budget can detect a large effect and falsify simple stories; it cannot promise precise proof of a small edge. A confidence interval crossing zero is insufficient evidence, not proof that the effect is exactly zero.

## Sampler precollection requirements

The planned exclusion union must include all 681 earlier global feature/outcome exposures plus all 783 scored proxy four-hour targets. Check each proposed delayed target interval against the union across all assets. Exact previously queried t0 values and IDs are excluded. Preserve the half-open interval convention and explicit boundary counts in the audit.

Require complete 200-bar historical OHLCV inputs and complete 3,000-minute volume history, finite positive native prices, valid nonnegative volume, and a positive historical volume median. Compute the first-30-minute gate independently from native values. Sampling may check future timestamp/validity coverage, but must not save or inspect future returns/excursions. One asset per UTC day is useful but does not itself prevent target overlap across midnight; check intervals explicitly. Balance assets/years using only timestamps and gate features, never outcomes. Stage and reserve assignment must be deterministic and reproducible from the frozen seed and candidate pool.

## Runner review and implemented safeguards

The old harness already used a fresh `codex exec`, empty temporary working directory, disabled tools/search, ignored user/project configuration, durable per-attempt budget reservations, and audited actual delivered text/image. Two omissions warranted hardening: its model-visible absolute attachment path contained the experiment/run/case name, and its audit accepted the intended prompt appearing among potentially additional user text.

The new runner now uses neutral `chart.png` inside the temporary directory and writes its final output there before copying it out. The new `runner_templates/cli_audit.py` is fail-closed: exactly one session metadata record, one model/effort context, two allowed user messages, an exact runtime environment wrapper, one exact four-block image-plus-request message, exact frozen image bytes/text hashes, one final answer, no additional assistant turns, and no tool/unknown response items. It checks fresh exec origin/cwd and rejects reused session identifiers. Source prompt and image hashes are verified before launch by the runner and again by the auditor.

The audit uses an explicit runtime instruction lock from a genuine earlier CLI transcript. The prior CLI still injected its standard base instructions, generic built-in skill inventory and generic runtime developer messages despite discovery/tool flags. These cannot honestly be described as absent. They contain no inherited research conversation in the inspected reference; their hashes are frozen, and extra user/project/task content is forbidden. The runtime environment discloses the actual current date/timezone and neutral working directory, not the historical market date or asset. This is an isolated trading opinion under common CLI instructions, not a raw language model receiving literally only two inputs.

`design/cli_audit_offline_test.json` records a passing offline test of a genuine transcript with only its attachment wrapper neutralized, followed by twelve rejected mutations: old informative image path, additional user turn/text, built-in web search, ordinary tool call, second context, wrong cwd, inherited session metadata, wrong image/model, duplicate final, and injected runtime text. No model calls were needed.

Before the parallel batch, audit one already planned screening case. A changed runtime bundle, wrong delivery/model, inherited context, or tool access must pause collection for harness review instead of triggering blind retries. Operational timeout or invalid JSON can follow the frozen retry rule. Budget reservations remain conservative even for uncertain attempts. All case/stage authorizations and frozen protocol/input hashes must be checked before every launch.

## Status

Statistical protocol: suitable to freeze, with the implementation details above. Runner audit: implemented and offline-tested, subject to checking the actual first new transcript and frozen manifest. Sampler: awaiting completed frozen artifacts and independent precollection audit. No fresh post-entry outcome has been examined by this reviewer.

## Completed precollection and pilot audit

`precollection_selection_audit.json` now records PASS for all 300 potential cases: native gates and ATR/volume inputs, full historical and future-validity coverage, all 439,200 exclusion comparisons, deterministic selection/order, and stage/asset quotas. No post-entry return was calculated by the reviewer. There are 230 allowed half-open endpoint adjacencies. Some intervals occupy gaps between previously scored proxy targets, so they must be described as unscored specific target intervals, not wholly unseen endpoint prices. This was disclosed before interpretation; the frozen sample was retained and no rule was changed after calls began.

`pilot_isolation_audit.json` independently verifies actual pilot case 1: unique fresh Terra/medium session, neutral attachment and final-output paths, exact request/image, no extra user/assistant history, no tools, effective read-only sandbox and restricted network, unchanged pre-call runtime instruction bundle, and matching durable stage authorization/budget reservation. The old budget hash is unchanged. Subsequent collection remains subject to the same per-case audit. No live runner code was modified during collection.

## Completed stage reviews

Screen and confirmation were explicitly released separately. `screen_statistics_audit.json` reproduces all 40,000 screen bootstrap draws and the frozen continuation to 120 quiet-rally cases only. The long screen failed; no long confirmation-reserve outcomes were examined.

`confirmation_statistics_audit.json` reproduces all 40,000 confirmation draws and fixed-effects distributions by independent row-level weighted residualization. The 91 AI-aligned shorts average +0.0519374% gross, with adjusted aligned-minus-opposed spread +0.1071749 percentage points. Both primary lower bounds are negative; the later chronological half loses and removing the three largest winners makes the mean negative. The frozen confirmation claim fails. This is insufficient evidence for the proposed edge, not a proof that every possible effect is zero.

`final_isolation_budget_audit.json` checks all 180 exact delivered inputs/images, unique sessions and working directories, runtime bundles, effective permissions, stage authorizations and prelaunch reservations. All pass with zero failures/retries. The new 200-attempt allowance retains 20; the old ledger remains 771 used with 29 unused. All frozen old-source and archived screen-evidence hashes are preserved. None of the unused DOWN reserve outcomes was read.

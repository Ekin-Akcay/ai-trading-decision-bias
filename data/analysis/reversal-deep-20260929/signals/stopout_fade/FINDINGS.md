# Stop-out fade mechanism: no robust candidate

The finite16-policy study tested whether the AI might choose the right eventual direction but enter too early or place an exploitable stop. After the original hypothetical trade stopped out before its target, the strategy entered in the **same direction as the original AI**, at the following1-minute open. This follows a hypothetical forced closing order in the opposite direction; it is distinct from immediately reversing the AI prediction. No actual retail order flow was observed.

**None of the16 candidates passed the declared screen. Every candidate lost after20bps in the original150-window sample.** Only two candidates had positive mean net returns in the reused280 windows. All48 candidate/control nominal95% net-mean intervals include zero, before search correction. This is exploratory reuse after inspecting earlier results, not new independent validation.

| Candidate | Original trades / mean net | New trades / mean net | New net after30bps | New net excluding best3 |
|---|---:|---:|---:|---:|
| AI LONG stopped first within105m; buy next open, hold240m |35 /−0.3374%|48 /+0.4839%|+0.3839%|−0.0429%|
| AI LONG stopped first within240m; buy next open, hold240m |43 /−0.5784%|61 /+0.3034%|+0.2034%|−0.1146%|

The first candidate's new chronological thirds are+1.1599%,+0.2342%,+0.0577%, but its negative original result, winner concentration and95% interval starting at−0.3541% prevent a robust-profit interpretation. Its all-window AI-width control averages+0.3400% net over130 triggers; the price-only ATR-width control averages+0.1073% over157. The AI-selected difference is therefore exploratory, not evidence of a causal or reproducible retail-stop effect.

The other14 selected policies have negative new net means. ATR stops and targets on the new position did not rescue this mechanism within the registered family. There is no sufficiently supported candidate here to justify spending the remaining model-call budget on a purported confirmation.

## Exact execution and audit

The original bracket must hit SL before its2×SL target; target-first cases do not trigger later entries. Entry follows the entire stop-trigger minute. New stops/targets are centered on the actual new-entry open. Stop gaps use adverse actual opens, target gaps cap at target, and a new-position bar touching both levels counts as stop. Only the new strategy trade is charged20bps; the hypothetical original AI loss is not charged to a position the strategy never held. Maximum elapsed path is480minutes.

The reviewers noted that assigning a simultaneous original SL/TP bar to SL can create additional fade entries and is not necessarily conservative for the new trade. We preserved the registered primary, flagged this condition and saved an exclude-ambiguous-trigger sensitivity. **There were zero ambiguous original triggers in either dataset or either control**, so this distinction has no numerical effect here.

Independent replay passed13,760 original first-exit checks and7,468 new-trade entry/exit/payoff checks. All430 native price paths were finite and positive. Six synthetic tests covered gap stops, capped target gaps and same-bar ambiguity. All48 family vectors match their summaries.

Files: `results.csv`/JSON retain all16 candidates and32 controls; `all_window_paths.csv.gz` retains13,760 window/policy/width rows, including target-first and timeout nontriggers; `ambiguity_sensitivity.csv` records the fixed diagnostic; `independent_validation.json` records replay checks. `family_vectors.npz` provides48×280 `net_pct`, `gross_pct`, `selected` and ambiguity matrices, plus policy labels, cases, window IDs and timestamps. Nontrigger returns are NaN with selected=False, so use the mask explicitly when integrating into familywise tests.

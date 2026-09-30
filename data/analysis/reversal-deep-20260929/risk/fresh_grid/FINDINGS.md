# Exploratory grid transfer after the primary test

**No stable replacement strategy emerged.** This was an explicitly exploratory follow-up after inspecting the failed locked validation. It does not overwrite the two primary outcomes or constitute another untouched test.

We applied 721 of the original 824 exit policies to all 280 new Terra windows. The 103 policies requiring 72 hours were excluded because the new sample guaranteed 24 hours only. No model calls, new thresholds or new directions/gates were added. All 403,760 elementary path outcomes and 10,815 group summaries are saved.

Of 5,047 reversal-policy cells with at least 20 old and 40 fresh executed trades:

- 62 had positive average net return in both old and fresh samples.
- **Zero** had positive net averages in all four chronological halves: old earlier, old later, fresh earlier, fresh later.
- Therefore zero satisfy the stronger old source batch and fresh chronological thirds consistency screen.

These counts describe a large search and are not significance claims. Root is conducting multiplicity checks from the retained window-level arrays.

## Why the apparent winners do not qualify

| Example | Old trades | Fresh trades | Old net/trade | Fresh net/trade | Failure |
|---|---:|---:|---:|---:|---|
| Reverse Terra long into short; fixed SL 1.5%, target 3×SL, timeout 720 min |72|91|−0.1512%|+0.2936%|Old later half −0.5368%; fresh final third −0.0134%|
| Reverse Terra long into short; SL 2×AI stop, target 3×SL, timeout 720 min |72|91|−0.1801%|+0.2633%|Both old chronological halves negative|
| Reverse all directions below both MAs; exit 1440 min |50|111|−0.1589%|+0.3547%|Old later half −0.9618%; fresh final third −0.3257%|
| Reverse Terra long into short; SL 1.5×AI stop, target 1×SL, timeout 240 min |72|91|+0.1404%|+0.0066%|Fresh later half −0.0172%; 30 bp costs negative|

The final row comes closest to preserving all four halves but is effectively at the fee break-even point. Requiring above-both MAs for that same rule yields +0.0287% fresh versus +0.1054% old; its old later half was −0.0371%, and it also fails 30 bp costs. Adding this gate after viewing the outcomes cannot repair the failed primary claim.

The apparent best below-both 24 hour reversal includes only three Terra-LONG→SHORT trades, averaging +4.1097% net. Those three unusual decisions materially lift the overall 111-trade average; this is not a broad replicated long-only advantage. Simple long-only below-both positions average +0.1217% fresh, versus +0.2503% for 108 selected AI short→long trades. The old 50 selected long trades still lost −0.1589% net on average.

## Original finalists remain unchanged

The locked S policy is still +0.00816% net over 91 fresh trades, with fresh earlier/later halves +0.1172%/−0.0985%. The earlier ATR 2/RR 1 alternative is +0.00777% net, with halves +0.1747%/−0.1555%. Neither becomes reliable through this grid search.

## Controls and files

Every original gate and policy also has always-long/always-short controls in `all_trials.csv`. Agent-stop controls use the AI's supplied sizing and are not pure no-AI controls; fixed/ATR controls are price-only. Examples: the fresh fixed SL 1.5%/RR 3/720 min short control is −0.0778% across all 280 and +0.1090% above both, compared with +0.2936% for 91 AI selected shorts. That selection difference is worth describing, but its old-sample reversal must not be hidden.

- `all_trade_results.npz`: array axes 721 policies × 280 windows × 2 directions (long, short); includes gross_pct, held_minutes, ambiguous, gap, and original_policy_ids.
- `policies.json`: maps array position to original risk policy_id.
- `windows.csv`: fresh receiver order in case order.
- `all_trials.csv`: every fresh group summary.
- `old_fresh_comparison.csv`: complete matched comparisons.
- `ranked_candidates.csv`: eligible cells with explicit robustness flags.
- `stable_candidates.csv`: empty because no candidate qualifies.
- `audit.json` and `validation.json`: coverage, preservation, and numerical checks.

No original discovery, primary finalist, or previous report was changed.

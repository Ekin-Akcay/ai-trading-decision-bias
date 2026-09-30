# Static review before fresh outcome release

Reviewed `data/sim/reversal-validation280-20260929T194012Z/evaluate.py`, the locked validation protocol, and `confirmation/run.py`. This review did not read or evaluate fresh outcomes.

## Fresh finalist evaluation

- Primary S entry is path index0 close, the minute ending at the original snapshot entry clock.
- S next minute index1 starts at original entry; timeout index240 closes at original+240minutes.
- S delay1/5 enter at index2/6 open, re-center the same original stop percentage on that actual fill and retain index240 timeout.
- Model stop fractions convert to percentage points before multiplying by1.5; target distance is twice strategy stop. The reversed side is short only when the original AI side is long.
- The donor matrix scales donor original-stop/ATR ratio by receiver ATR, then1.5; action and geometry travel together under within-era/MA-regime permutations.
- Follow-AI long control replays mirrored brackets, rather than negating the short bracket payoff. ATR2/RR2 controls and ATR2/RR1 diagnostic match their declarations.
- L index15 close is the first complete future15-minute close; index16 open is the following one-minute open at original+15minutes. Index255 close is exactly240minutes after that actual entry.
- Row bootstrap, quarter bootstrap, conditional permutation and two-test Holm implementation are structurally consistent with the locked specification.
- Primary, delayed and control scoring paths appear correct. No outcome-dependent alterations were requested.

## Discovery discrepancy

`confirmation/run.py` returns favorable gap improvement at the opening price rather than capping the payoff at the target in its optional bracket variants. Its adverse-gap and simultaneous-touch handling are correct. Root was notified to cap favorable gaps and rerun/archive the rejected discovery grid, or explicitly disclose the older convention. This does not affect the selected time-only L finalist or the new capped S engine.

## Independent checker prepared, not executed on fresh data

`independent_s_check.py` requires all three gates before any fresh outcome read:

1. Explicit root invocation with `--release reversal-validation280-20260929T194012Z`.
2. Existing `ALLOW_EVALUATION` marker in that run folder.
3. Exactly280 unique accepted case decisions.

After release it independently replays native time-indexed minute OHLC for S, both delays, mirrored long control and both ATR controls, and compares root per-window rows, trade clocks and aggregate control summaries. It writes `risk/independent_S_validation.json`. Only its `--help` path was exercised during preparation; no fresh scoring has occurred in this worker.

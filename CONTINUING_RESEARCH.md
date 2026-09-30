# Research continuation notes

The latest completed phase is `data/analysis/ai-timing-200-20260930/`, with model records under `data/sim/ai-timing-200-20260930T104240Z/`.

The frozen quiet-rally / AI-SHORT timing rule failed confirmation. Its 91 selected confirmation trades averaged +0.051937% gross, but the uncertainty interval crossed zero, the later half was negative, and removing the largest winner made the mean negative. The mirrored long rule failed screening. A retrospective identical-coverage AI-versus-MA20 comparison also did not establish AI value.

Before another experiment:

1. Read the latest `RESULTS.md`, `VALIDATION_PROTOCOL.md`, and both interpretation reports.
2. Treat all evaluated outcomes as already exposed. Add `exposed_target_intervals.json` to earlier exclusion inventories before selecting new targets.
3. Keep historical screening and confirmation results separate. Do not relabel a retrospective improvement as validation.
4. Declare a new hypothesis, price-only controls, sampling rule and stopping criteria before looking at new payoffs.
5. Preserve existing records; put any new run in a distinct directory. Use isolated model contexts and audit exactly what inputs were supplied.

The original local workspace retains private operational state needed to resume collection. This public snapshot includes scientific results and numerical reproduction but excludes local credentials, CLI transcripts and personal run-budget accounting. No study is currently collecting opinions, and no live orders have been placed.

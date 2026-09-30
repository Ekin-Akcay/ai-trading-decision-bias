# AI decision timing: fresh historical test

No strategy passed the frozen confirmation standard.

The short setup's screening mean did not persist: confirmation averaged +0.052% across 91 trades, versus +0.099% for the MA20-only control. Removing only the largest winner changes the AI mean to -0.007%. Its chronological halves are +0.301% and -0.202%. The positive point mean is too fragile to call a verified strategy.

Used **180 of 200 new trade snapshot attempts**, yielding 180 audited opinions. **20 new credits remain**. The previous 29 unused credits and all older findings are preserved. All reported returns are gross, without fees, funding or leverage.

The hypotheses follow an earlier AI decision after a 30-minute low-volume countermove. The actual entry is after that observation; positions close 120 minutes later. No exit threshold, holding period, confidence cutoff or model was optimized on these results.

| Stage | Rule | AI trades | Win rate | AI mean | Price-only mean | MA20-only mean | Adjusted AI spread |
|---|---|---:|---:|---:|---:|---:|---:|
| screen | Short quiet rally | 22 | 77.3% | +0.573% | +0.196% | -0.001% | +2.277 pp |
| screen | Long quiet decline | 14 | 35.7% | -0.293% | -0.241% | -0.051% | -0.966 pp |
| confirmation | Short quiet rally | 91 | 46.2% | +0.052% | -0.030% | +0.099% | +0.107 pp |

Price-only and MA20 figures use the same eligible gates and entry/exit clock but can execute different numbers of trades. The adjusted spread compares AI-aligned versus AI-opposed gate returns within asset × original MA20-side strata. It is a difference in percentage points, not an additional portfolio return. Full opportunity averages, with skipped trades zero, are in the stage summaries.

## Screening and confirmation

Screen decision: `continue_fixed_confirmation`. Passing directions: up (up means the short hypothesis; down means the long hypothesis). The screen is exploratory and never contributes to confirmation intervals.

### Screen: Short quiet rally

22 trades; mean +0.573%, median +0.219%, win rate 77.3%. Mean winner +0.895%; mean loser -0.523%; worst trade -0.737%.
Ordinary 95% gross-mean interval (finite draws): [+0.161%, +1.130%]. Family-adjusted one-sided lower bound: +0.120%.
Adjusted AI spread: +2.277 percentage points; family-adjusted lower bound -0.497. Undefined bootstrap fraction: gross 0.000%, adjusted spread 0.950%; undefined draws count as −∞ for the decision lower bound. Identifying mixed strata contain 11 aligned and 8 opposed calls.
Chronological halves: +0.711%, +0.373%. Mean after removing the three best winning events: +0.190%.
Status: **screen pass not confirmation**.

### Screen: Long quiet decline

14 trades; mean -0.293%, median -0.133%, win rate 35.7%. Mean winner +1.063%; mean loser -1.047%; worst trade -5.431%.
Ordinary 95% gross-mean interval (finite draws): [-1.500%, +0.721%]. Family-adjusted one-sided lower bound: -1.717%.
Adjusted AI spread: -0.966 percentage points; family-adjusted lower bound -3.885. Undefined bootstrap fraction: gross 0.000%, adjusted spread 0.163%; undefined draws count as −∞ for the decision lower bound. Identifying mixed strata contain 13 aligned and 10 opposed calls.
Chronological halves: -0.093%, -0.653%. Mean after removing the three best winning events: -0.839%.
Status: **screen stop not statistical falsification**.

### Confirmation: Short quiet rally

91 trades; mean +0.052%, median -0.030%, win rate 46.2%. Mean winner +0.909%; mean loser -0.682%; worst trade -4.339%.
Ordinary 95% gross-mean interval (finite draws): [-0.248%, +0.379%]. Family-adjusted one-sided lower bound: -0.289%.
Adjusted AI spread: +0.107 percentage points; family-adjusted lower bound -0.392. Undefined bootstrap fraction: gross 0.000%, adjusted spread 0.000%; undefined draws count as −∞ for the decision lower bound. Identifying mixed strata contain 70 aligned and 29 opposed calls.
Chronological halves: +0.301%, -0.202%. Mean after removing the three best winning events: -0.102%.
Status: **not confirmed**.

## What the test can establish

This is a conditionally sampled historical study, balanced across four assets and available years. It tests the selected quiet-move population; it does not estimate natural trade frequency or a compounded account return. These are fresh query windows and previously unscored target intervals, not a prospective live-market test or entirely unseen price data. Screen and confirmation periods share market quarters, so they are separate targets rather than independent market regimes.
The 300 potential targets avoid the enumerated earlier scored intervals. The half-open convention permits endpoint adjacency: 230 exclusion comparisons touch an old boundary. Input histories can overlap earlier observations. Neither sampling nor model inputs use the post-entry payoff. Quarter bootstrap intervals are approximate and retain a four-statistic correction even when one direction proceeds.
A reliably positive adjusted spread would support additional selection value beyond the specific asset/MA20 controls used here. It would not prove incremental value beyond all price features or that AI simulates losing retail traders.

## Reproduction and records

- Run: `data/sim/ai-timing-200-20260930T104240Z`.
- Frozen rules: [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).
- Durable state: [PROJECT_MEMORY.md](../../../PUBLICATION.md), [HANDOFF.md](../../../PUBLICATION.md), [RESEARCH_LOG.jsonl](../../../PUBLICATION.md).
- Budget: [snapshot_budget.json](../../../PUBLICATION.md).
- Complete interactive positions: [index.html](index.html).
- Sampler, isolation and economic replay checks are retained in `design/` and `audit/`.

## What the AI decisions showed

AI direction agreed with MA20 direction in 96/120 confirmation cases (80.0%). Mean original confidence was 0.5907 on winning selected trades and 0.5896 on losing selected trades. This is a descriptive comparison, not a calibration test: the AI confidence concerned its original bracket, while this research changed the entry and exit.

[AI wording, price paths and three mechanically selected examples](interpretation/AI_BEHAVIOR.md). The first 30-minute countermove is a sampling condition and cannot itself establish that the AI was wrong.

[Post-score comparison at identical trade coverage](interpretation/IDENTICAL_COVERAGE.md). This separate diagnostic does not change the frozen confirmation result.

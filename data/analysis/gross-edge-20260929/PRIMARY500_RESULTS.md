# AI reversal: fee-free fresh validation

Neither frozen rule passed the fresh gross-profit verification criteria.

500 isolated Terra snapshots across 125 calendar blocks and four assets. 501 physical calls used in this phase; 781 including the previous280. No historical findings were overwritten. All primary returns below are unlevered and exclude costs.

| Frozen rule | Trades / blocks | Gross per trade | Gross wins | Simultaneous block interval | Price-only mean |
|---|---:|---:|---:|---:|---:|
| L048 | 101 / 38 | +0.361% | 52.5% | [-0.381%, +1.194%] | +0.297% |
| S508 | 171 / 64 | -0.013% | 57.3% | [-0.264%, +0.228%] | -0.056% |

L048: when AI chooses SHORT and the completed prior-day asset close≤50DMA and BTC close≤200DMA, buy at the next minute open and exit after240minutes. S508: when AI chooses LONG above both intraday MAs, short with stop=target=2×ATR14 and a240-minute timeout.

## What survives the checks

**L048**: profit verified=False; incremental AI contribution verified=False.
- Quarter-bootstrap95% profit interval: [-0.212%, +1.023%].
- AI increment after asset/era/MA-stratum standardization: +0.021%; simultaneous block interval [-0.068%, +0.104%].
- Entry delayed1/5minutes: +0.355%, +0.319%.
- Chronological halves: +0.347%, +0.372%.
- Removing the largest1/3winners: +0.214%, +0.074%.
- Failed profit criteria: block_simultaneous_profit_lower_positive, quarter95_profit_lower_positive.

**S508**: profit verified=False; incremental AI contribution verified=False.
- Quarter-bootstrap95% profit interval: [-0.232%, +0.196%].
- AI increment after asset/era/MA-stratum standardization: +0.047%; simultaneous block interval [-0.030%, +0.142%].
- Entry delayed1/5minutes: +0.033%, +0.023%.
- Chronological halves: -0.177%, +0.173%.
- Removing the largest1/3winners: -0.030%, -0.054%.
- Failed profit criteria: block_simultaneous_profit_lower_positive, quarter95_profit_lower_positive, both_chrono_halves_positive.

## Interpretation

The500calls contain125distinct market times, so uncertainty resamples whole four-asset blocks and whole quarters. New future paths do not overlap previously examined chart/history/outcome intervals; feature histories may reuse known past data. This is newly held-out historical target data, not live trading or proof against model pretraining exposure.

The price-only controls execute the identical direction and geometry whenever the price gate holds. The standardized comparison asks whether AI selection adds information beyond declared asset, era and intraday-MA groups. It does not establish causality or superiority to every possible price-only model.

The secondary sampled basket returned +8.379% with -6.743% maximum drawdown. It holds one-quarter equity notional per eligible asset and cash for skips. This sparse experimental basket is not an annualized or continuously deployed strategy; it cannot rescue failed primary rules.

Leverage was not used in the test. The zero-cost assumption excludes spread, commissions, funding and liquidation mechanics. A positive gross result would still need executable pricing and position-sizing validation before any live profitability claim.

Secondary fixed-percentage short and15-minute-confirmed long results remain labeled secondary in summary.json. No post-outcome rule was promoted to a winner.

## Artifacts

- [Interactive trade report](./data/sim/gross-edge-500-20260929T204545Z/index.html)
- [Full strategy trade ledger](./data/sim/gross-edge-500-20260929T204545Z/strategy_trades.csv)
- [Model decisions](./data/sim/gross-edge-500-20260929T204545Z/accepted_decisions.jsonl)
- [Machine-readable summary](./data/sim/gross-edge-500-20260929T204545Z/summary.json)
- [Locked protocol](./data/analysis/gross-edge-20260929/VALIDATION_PROTOCOL.md)
- [Sampling audit](./data/analysis/gross-edge-20260929/design/sampling_design_audit.json)

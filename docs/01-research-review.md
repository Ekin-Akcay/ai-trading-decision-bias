# Research Review — What Is Known (compiled 2026-09-17)

Condensed from an academic-literature sweep and a practitioner-evidence sweep (URLs inline). Read `00-thesis.md` first; this file is the evidence base behind its priors.

## Verdict in one paragraph

The **strong form** of the fade hypothesis — LLM decisions are anti-predictive, invert everything — is **not supported and is contradicted for 2021–2023 news signals**, which were *right-way* predictive before decaying with adoption. The **weak/conditional form is alive**: honest out-of-sample benchmarks put LLM agents at-or-below dumb baselines with *patterned, regime-dependent* errors (too cautious in bulls, too aggressive in bears; over-extrapolation after run-ups; heavy overconfidence; stable per-model directional tilts). No one has published a profitable systematic fade — and no one has published an ensemble-LLM crowding index at all, which makes E4/E7 the most original part of this project. The best-supported null remains "LLM ≈ noise, blanket fade ≈ guaranteed loss after costs" — the project's job is to find the conditional cells where that null breaks.

## A. Can LLMs predict returns? (the inconvenient evidence first)

- **Lopez-Lira & Tang, "Can ChatGPT Forecast Stock Price Movements?"** ([SSRN 4412788](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4412788), [arXiv:2304.07619](https://arxiv.org/abs/2304.07619)). GPT-4 headline-sentiment long-short: ~34 bps/day pre-cost, Sharpe ~3, concentrated in **small caps** and **negative news**; sample starts post-cutoff (clean). **Critical for us: Sharpe decayed monotonically 6.54 (2021Q4) → 3.68 (2022) → 2.33 (2023) → 1.22 (Jan–May 2024)** — adoption arbitraged it toward zero; it never flipped negative. Lesson: the unconditional LLM signal in 2025+ is probably ≈ 0, and zero inverted is a costs-only loser.
- **Chen, Tang, Zhou & Zhu** ([SSRN 4660148](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4660148)): aggregate WSJ-news LLM scores predict S&P returns monthly via *underreaction to good news*. Right-way again.
- **Kim, Muhn & Nikolaev**: GPT-4 beats analysts on earnings direction (~60% vs ~53%) — treat with care (an arXiv posting was withdrawn by the authors).

## B. But LLM *agents* are mediocre with patterned failures (the fade-relevant evidence)

- **FINSABER (KDD 2026,** [arXiv:2505.07078](https://arxiv.org/abs/2505.07078)**)**: re-evaluated LLM trading agents over 20 years, 100+ symbols — reported advantages "deteriorate significantly"; simple baselines (B&H, ARIMA, XGBoost, trend) beat them. **Regime asymmetry: bull markets B&H Sharpe 0.61 vs FinAgent 0.12 / FinMem −0.19 (too conservative); bear markets FinMem −0.97 vs B&H −0.28 (too aggressive).** This is exactly the kind of conditional wrongness M1/M3 predict.
- **StockBench (contamination-free, Mar–Aug 2025,** [arXiv:2510.02209](https://arxiv.org/abs/2510.02209)**)**: 14 frontier models trading daily; most fail to beat buy-and-hold; the best margins are within noise; agents underperformed in the downturn window.
- **Alpha Arena S1 (live crypto perps, real money, Oct–Nov 2025,** [nof1.ai](https://nof1.ai/)**)**: 4 of 6 LLMs lost money (GPT-5 −63%); **stable model personalities: Claude long-biased, Gemini short-biased, Qwen overtrading (1,418 trades) vs Grok (158)**. n=1 and 17 days — weak alone, but the "per-model persistent tilt" structure is what H5 tests.
- **Self-reported agent papers (FinMem, TradingAgents)** claim big wins on cherry-picked tickers/windows; FINSABER exists precisely because those don't replicate.

## C. LLM behavioral biases (mechanism support)

- **Over-extrapolation + optimism** — Chen, Green, Gulen & Zhou ([arXiv:2409.11540](https://arxiv.org/abs/2409.11540)): asked to forecast from price histories, ChatGPT extrapolates recent performance (despite actual short-horizon reversal) and is optimistic vs realized returns. **Direct support for M1 (fade after run-ups at reversal horizons).** Nuance: its 80% intervals beat human survey respondents' — the model isn't uniformly dumb.
- **Overconfidence** — frontier LLMs overestimate their correctness by **20–60 percentage points** ([arXiv:2505.02151](https://arxiv.org/pdf/2505.02151)). Support for M4 (fade high-stated-confidence calls) — though measured on general tasks, not returns.
- **Herding across similar models** — TwinMarket ([arXiv:2502.01506](https://arxiv.org/abs/2502.01506)) and Lopez-Lira's simulation ([arXiv:2504.10789](https://arxiv.org/html/2504.10789v1)): similar prompts → correlated agent behavior → bubbles/instability. Mechanism support for M2 (consensus = crowding).
- **Forecasting vs humans**: GPT-4 significantly *worse* than the human crowd in a real forecasting tournament ([arXiv:2312.06941](https://arxiv.org/abs/2312.06941)).

## D. Lookahead bias (validates our Trap A rules)

- **Glasserman & Lin** ([SSRN 4586726](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4586726)): decompose contamination into *lookahead* (memorized outcomes) and *distraction* (background knowledge about named firms); **anonymized headlines outperform raw ones even in-sample** → anonymize for backtests AND live use. Direct justification for the masked arm.
- **Sarkar & Vafa** ([SSRN 4754678](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4754678)): LLMs "predict" events they memorized (election winners from bios) → evaluate strictly post-cutoff.
- **Gao, Jiang & Yan** ([arXiv:2512.23847](https://arxiv.org/abs/2512.23847)): Lookahead-Propensity score; in-sample "skill" concentrates exactly where the model can recall the outcome, **collapsing to zero post-cutoff**.
- **ChronoBERT/ChronoGPT** ([arXiv:2502.21206](https://arxiv.org/abs/2502.21206)): chronologically-trained models exist on Hugging Face — a future clean-historical-backtest option worth remembering.

## E. Practitioner graveyard (expectation calibration)

- **SJIM (Inverse Cramer ETF)**: −15% vs S&P +25% in <1 yr; ~$2M AUM at death (Feb 2024). Cramer studies: **alpha ≈ 0, not negative** (Hartley & Olson; Engelberg et al. — the only real effect was small-cap attention-spike reversal). **Inverting zero alpha = short beta − fees − borrow.** ([ETF.com](https://www.etf.com/sections/news/inverse-jim-cramer-etf-shuttered))
- **AIEQ** (IBM Watson ETF): alive but ~62 pts cumulative behind SPY since 2017, ~2,700% turnover. **QRFT liquidated 2026. Eurekahedge AI hedge-fund index 9.8%/yr vs S&P 13.7% (2009–2024).** AI funds = expensive closet benchmarks.
- **Social-sentiment funds**: Derwent Twitter fund dead in ~1 month (2012, and its academic basis failed replication); **BUZZ** live ~8.4%/yr vs SPY ~13–14% after a backtest that "beat the S&P by 115%" — the canonical backtest-to-live gap.
- **The one robust fade-the-crowd result: Barber, Huang, Odean & Schwarz (J. Finance 2022,** [SSRN 3715077](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077)**)**: Robinhood herding episodes → **−3%/−6% abnormal over 5 days, ~−5%/−9% over 20 days** after ordinary/extreme herding. Caveats: small volatile names, borrow 20–100%+ APR exactly when the signal fires, and the Robintrack feed is dead. **An LLM ensemble as a live herding detector is a plausible replacement for that dead feed — this is the strongest practitioner anchor for the project.**
- **WSB studies**: due-diligence posts predicted returns pre-2021, then the effect vanished; long-minus-short ≈ no alpha, longs slightly negative ([RFS 2024](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3806065)).

## F. Overlapping known factors (what any "signal" must be benchmarked against)

- **Short-term reversal**: classic weekly implementation ~16%/yr gross 1990–2009, **decayed to ~nothing in most regions now**; it's compensation for liquidity provision. If our fade ≈ reversal exposure, it's free elsewhere and mostly dead.
- **AAII contrarian**: works only at bearish extremes (+14%/6mo after >2σ bearish); bullish extremes ≈ nothing. Sparse-trigger contrarianism, consistent with "fade only at extremes."
- **Single-stock put/call**: option flow is *informed* — fading it loses (Pan & Poteshman). Not all positioning is fade-able.
- **Crypto perp funding**: crowding premium was real (carry Sharpe ~6.4 in 2020–2025 sample, ~4 from 2024, **negative in 2025** — decaying); funding extremes still mark reversals. **Funding is the incumbent crowding signal our LLM-consensus must beat or complement in crypto** — and it's free. ([arXiv:2510.14435](https://arxiv.org/pdf/2510.14435))
- **Machine Forecast Disagreement (Bali, Kelly, Moerke & Rahman,** [SSRN 4537501](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4537501)**)**: ML-model disagreement decile spread ~14%/yr — the published template for our E4/E8 ensemble-dispersion work, done with ML models rather than LLMs.

## G. Frictions (kills list)

| Venue | Round trip | Extra |
|---|---|---|
| US large caps/ETFs | ~5–10 bps | — |
| Meme/small caps | 20–50+ bps | borrow 20–100%+ APR when it matters; squeeze risk |
| Crypto majors (perps) | ~9–11 bps taker | funding often *pays* the anti-crowd side |

**Consequence:** the meme-equity edge (where herding reversal is largest) is mostly unharvestable at retail; **crypto perps are the only venue where fading the crowd is cheap and being anti-crowd earns carry** — confirming the thesis §7 venue ranking.

## H. What this changes in our design (deltas applied)

1. **Two-sided pre-registration**: because 2021–23 evidence was right-way, every cell tests deviation from 50% in *either* direction — "follow the LLM" is as acceptable an outcome as "fade it" (already in `hypotheses.md`).
2. **FINSABER regime asymmetry** becomes a named hypothesis: expect under-risk in up-trends, over-risk in down-trends (tested via E6/E5 conditional splits).
3. **Funding-rate benchmark**: in crypto, any consensus-extreme signal must add value beyond perp funding — add funding data in Phase 2.
4. **Masked arm justified twice over** (Glasserman–Lin distraction effect): anonymization may *improve* signal, not just reduce leakage.
5. **Expectation:** live products that inverted famous predictors all died; edges if any are conditional, sparse, small, and crypto-first. The project's originality is the **multi-model decision-log dataset and consensus/dispersion index** — treat the dataset as the moat, the strategy as one consumer.

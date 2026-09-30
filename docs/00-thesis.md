# Thesis: Trading Against the Machine (NAI = Negative-AI Trading)

**One-liner:** LLMs asked to make trade decisions are not merely *uninformative* — they may be *systematically biased* in directions that correlate with future returns with the wrong sign, in specific, detectable conditions. If those conditions can be identified, their decisions become a fade-able (invertible) signal — or more generally, a free, always-on sensor of the "narrative crowd."

---

## 1. Why the naive version fails (and you already sensed this)

The naive strategy — "AI is bad, so invert everything it says" — fails for three reasons, and they shape the entire research design:

1. **Bad ≈ uninformative, not anti-informative.** A predictor with a 50% hit rate inverted is still a 50% predictor. Inversion only creates alpha if the hit rate is *reliably below* 50% (minus costs). Randomness is symmetric; you cannot mine alpha from symmetry.
2. **Costs are paid in both directions.** Inverting a coin-flip signal is not a 0-EV trade — it is a guaranteed loser at the rate of ~2× per-side costs per trade. Every fade strategy must clear this hurdle. (The smoke-test report in this repo demonstrates this numerically with a random model.)
3. **Inverting a *biased* model can just mean inheriting a dumb static bet.** LLMs plausibly have a long bias (optimism, "stocks go up" is in the training data). Inverting a long-biased 50% model ≈ being structurally short equities ≈ negative expected return. Any fade must be computed **relative to the model's own base rates**, not raw.

**Conclusion:** the tradeable object is *not* "the inverse of the AI." It is **the conditional structure of the AI's errors.** The research question becomes: *in which states of the world, for which assets, at which horizons, for which models, is the error rate predictably above 50%?*

## 2. Where systematic (fade-able) bias could actually come from

Six candidate mechanisms, roughly ordered by how much I'd bet on them:

**M1 — Narrative extrapolation at reversal horizons.** LLMs are trained on text that overwhelmingly *explains past moves* ("stocks rallied because…"). Asked to predict, they tend to extrapolate the prevailing narrative: recent up-move + good news → "long." But short-horizon returns (1–5 days) in liquid assets exhibit *reversal*, not continuation. A narrative-extrapolator should therefore be slightly-but-reliably wrong at 1–5 day horizons and possibly right at momentum horizons (1–3 months). **Testable prediction:** hit rate < 50% at h=1–5d, ≥ 50% at h=20–60d, and the short-horizon wrongness concentrates after large recent moves.

**M2 — The LLM as crowding sensor.** An LLM is a compression of internet consensus. When *many different models independently agree with high confidence*, the trade is by definition the consensus trade — i.e., crowded, i.e., already priced, i.e., vulnerable to unwind. This reframes the whole project: **you are not trading against the AI, you are using the AI as a free, high-frequency proxy for the median narrative-following participant** — and fading the crowd at extremes is one of the oldest documented edges (sentiment contrarianism, positioning squeezes). Even if every individual model is exactly 50/50, *consensus extremes* can be anti-predictive. This is the most theoretically defensible version of the idea.

**M3 — Capitulation/euphoria mimicry.** If LLMs absorb retail psychology from text, they may reproduce it: turning bearish after crashes (capitulating at bottoms), bullish after melt-ups (buying tops). **Testable prediction:** conditional on a large trailing move (e.g., |20d return| in the top decile), the model's directional accuracy collapses below 50%. This is where the fade should be concentrated if M3 holds.

**M4 — Confidence miscalibration.** Stated confidence may correlate with narrative vividness, not with accuracy — the most confident calls could be the *most* wrong (a compelling story is a crowded story). **Testable prediction:** calibration curve is flat or inverted; fade only high-confidence calls.

**M5 — Asymmetric action biases.** Long-rate, flat-rate, and short-aversion differ per model and per regime (models may refuse to short after bad news = exactly when shorting pays). Any signal must be measured as *deviation from that model's own conditional base rates*.

**M6 — Disagreement as a volatility signal.** When models disagree, the situation is genuinely ambiguous → ambiguity resolves → realized volatility. Dispersion across the model ensemble may forecast vol even if nothing forecasts direction. This is a consolation-prize strategy (vol targeting / straddle timing), but it's the one most likely to simply work.

## 3. Three tradeable formulations (from dumbest to smartest)

- **F1 — Conditional fade (rule-based):** invert the ensemble only inside pre-registered cells where Phase-1 evidence shows hit rate significantly < 50%: e.g. *(high consensus) × (after large move) × (short horizon) × (retail-heavy asset)*. Everything else: no trade. Few parameters, easy to falsify, easy to overfit — hence pre-registration discipline (see §5).
- **F2 — Meta-labeled signal (learned):** treat the LLM decision as a *primary model* and train a simple secondary classifier (logistic regression / small GBM) on features *(model id, action, confidence, ensemble agreement, regime: trend/vol/recent-move, asset class)* to predict P(decision is correct). Trade **with** the model when P is high, **against** it when P is low, flat in the middle. This is López de Prado's *meta-labeling* with an LLM as the primary. It subsumes F1 and handles "some models suck harder than others" automatically — but needs on the order of thousands of logged decisions, which is why the harvesting pipeline (§4) is the real asset.
- **F3 — Disagreement → volatility:** map ensemble dispersion to a realized-vol forecast; use it for position sizing or vol instruments. Direction-agnostic; survives even if M1–M5 all fail.

## 4. The two traps that kill this project if ignored

**Trap A — Lookahead leakage (the big one).** An LLM backtested on dates *before its training cutoff* has effectively seen the future: it knows COVID crashed markets in March 2020 and that NVDA went up. This contaminates historical backtests in *unknowable directions* — the model may look artificially good (it remembers outcomes) or artificially bad-in-a-fake-way. Mitigations, in order of strength:
1. **Forward (live) harvesting** — collect decisions daily from today on. 100% leakage-proof, and after 3–6 months you own a dataset nobody else has. *This is why the daily harvest cron should start immediately, in parallel with everything else.*
2. **Post-cutoff windows** — each model may only be historically backtested on dates after its documented training cutoff. Maintained in `docs/04-data-and-leakage.md`.
3. **Masked contexts** — present anonymized, date-stripped, (optionally vol-rescaled) return series so the model can't recognize the asset/era. Enables cheap historical testing of *pure pattern-reading*, at the cost of removing the news/narrative channel where the bias probably lives. Both arms are run; they answer different questions.

**Trap B — Multiple-testing / garden of forking paths.** Models × assets × horizons × regimes × consensus buckets = hundreds of cells; some will show hit rate 44% by luck. Discipline: (a) every hypothesis is written in `docs/hypotheses.md` *before* the test runs; (b) FDR control (Benjamini–Hochberg) across cells; (c) any surviving cell must replicate on a later, untouched time slice before money ever touches it; (d) effect must also be *economically* large enough to clear ~2×costs.

## 5. Falsification criteria (write the obituary in advance)

The premise is **dead** if, after ≥ ~1,000 decisions per arm across the roster:
- no pre-registered conditional cell shows |hit − 50%| significant at FDR 10% **and** > cost hurdle, and
- ensemble-consensus extremes show no forward-return asymmetry, and
- dispersion does not forecast next-day realized vol better than trailing vol alone (the lazy benchmark).

Even in that world the pipeline yields: a clean negative result, a multi-model narrative-sentiment index (potentially valuable as a *feature* in other strategies), and infrastructure for testing any future model generation. The downside is bounded and useful; the upside is a genuinely novel signal. That asymmetry is why the idea is worth the effort despite modest priors.

## 6. Calibrated expectations (honest priors)

- Academic evidence (see `01-research-review.md`) suggests LLM news-sentiment had *positive* short-horizon predictive power in 2021–2023 samples — the opposite sign of this thesis — concentrated in small/attention stocks, and likely decayed with adoption. Both signs are fine for us: **any stable sign is tradeable; only zero is not.**
- Famous "obviously fade-able" predictors (TV personalities) turned out to be ~noise after costs. The base rate for "inverse X" strategies is poor.
- Therefore: expect edges, if any, of a few bps/trade living in *conditional cells*, mostly in retail-heavy venues (crypto, meme equities). The project is structured so that even the null result produces reusable assets (forward dataset, sentiment index, harness).

## 7. Asset-class choice (initial stance)

Fade-able narrative bias should be largest where narrative share of flow is highest and arbitrage capital thinnest:

| Venue | Narrative intensity | Frictions | Verdict |
|---|---|---|---|
| Crypto majors + memecoins (BTC, ETH, SOL, DOGE) | Extreme; LLM training data saturated with crypto talk | Low (perps, 24/7, ~5–10 bps taker) | **Primary hunting ground** |
| Retail/attention equities (TSLA, GME, NVDA) | High | Shorting can be expensive; overnight gaps | Secondary |
| Index/commodity ETFs (SPY, QQQ, GLD, USO) | Low (macro, institutional) | Lowest | **Controls** — if a "signal" appears here as strongly as in DOGE, suspect an artifact |

Start: decisions on all three groups (cheap), but expect and pre-register that the effect concentrates in the first group. FX and rates: later, if ever.

## 8. Model roster philosophy

- **Frontier-cheap tiers** (Claude Haiku, GPT-mini, Gemini Flash): the "average AI" the thesis targets; pennies per thousand decisions.
- **Local open models via Ollama** (llama3.x 8B, qwen2.5 7B): free unlimited historical runs, pinned weights = perfect reproducibility, and genuinely "dumber" — closest to the thesis premise.
- **One frontier-top model** sparingly: tests whether "dumbness" shrinks with capability (if the fade edge *shrinks* as models improve, the mechanism story strengthens).
- **Non-negotiable controls:** Random, Always-Long, Momentum(20d), Reversal(5d). Any LLM pattern must be distinguishable from all four — momentum/reversal baselines are exactly the "shadow strategies" an LLM might be unconsciously imitating, and if `LLM ≈ Momentum`, you don't need the LLM (or its fade — you need the reversal factor, which is free).

*Related docs: research base → `01-research-review.md` · experiments → `02-experiments.md` · workflows/phases → `03-workflows.md` · leakage & data rules → `04-data-and-leakage.md` · hypothesis registry → `hypotheses.md`.*

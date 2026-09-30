# Data, Leakage Rules & Cost Model

## 1. The lookahead problem (read before trusting ANY backtest here)

An LLM evaluated on dates before its training cutoff has plausibly memorized the outcome (it "predicts" the COVID crash because it read about it). For this project leakage is *doubly* toxic: it biases results in an unknown direction, so it can fake both "the AI is smart" and "the AI is fade-ably dumb."

**Hard rules:**
1. **R1 — Informed-arm historical backtests are only valid strictly after the model's training cutoff.** Enforced via the cutoff table below (`run_masked_backtest.py --respect-cutoff` reads it).
2. **R2 — Masked-arm historical backtests are allowed on any period but labeled "suggestive."** Masking (no names, no dates, returns only, optional vol-rescaling via `prompts.build_masked_context(..., rescale_vol=True)`) reduces but does not eliminate recognition of famous episodes. Any masked finding must replicate on post-cutoff or forward data before promotion.
3. **R3 — Forward-harvested decisions (E7) are the only gold-standard evidence.** Gates G2+ (see `03-workflows.md`) accept nothing else.
4. **R4 — Decision logs are append-only.** Never rewrite, never re-prompt a past date with a newer model version and store it in the same file. Model version string + prompt hash live in every row.

## 2. Training-cutoff table (VERIFY against provider model cards before relying on it)

| Model | Claimed knowledge cutoff | Honest OOS start (cutoff + 1 mo buffer) |
|---|---|---|
| claude-haiku-4-5 | ~Feb 2025 | 2025-04-01 |
| claude-sonnet-5 / opus-5 | ~mid 2025 | 2025-09-01 |
| gpt-4.1-mini | Jun 2024 | 2024-08-01 |
| gpt-5-mini | ~late 2024 | verify |
| gemini-2.5-flash | ~Jan 2025 | 2025-03-01 |
| llama3.1:8b | Dec 2023 | 2024-02-01 |
| qwen2.5:7b | ~late 2023 | 2024-01-01 |

Maintained by hand; re-verify each entry on the provider's model card when a model is first enabled (`configs/models.yaml` carries a `cutoff:` field per model that the code actually uses — this table is documentation).

## 3. Universe & data sources

Defined in `configs/assets.yaml`; pulled by `scripts/pull_data.py` into `data/raw/<name>.csv` (daily OHLCV, auto-adjusted closes).

| Group | Assets | Source | Fallback |
|---|---|---|---|
| Crypto | BTC-USD, ETH-USD, SOL-USD, DOGE-USD | yfinance | Binance public klines API (no key) |
| Equities (attention) | AAPL, NVDA, TSLA, GME | yfinance | Stooq CSV endpoint |
| Equities (index/controls) | SPY, QQQ, IWM | yfinance | Stooq |
| Commodities (ETF proxies) | GLD, USO, DBC | yfinance | Stooq |

ETF proxies for commodities avoid futures-roll modeling; revisit if commodities ever become primary.

### Intraday crypto (primary program data — scope decision 2026-09-18)

Short-term bracket trades (typical close <1 day, max 2–3 days) cannot be evaluated
on daily bars: at that geometry both levels usually sit inside one daily bar
(measured: 14–81% of trades unresolvable, vs ≤0.75% on 5m bars for stops ≥0.5%).
Pulled by `scripts/pull_intraday.py` from Binance USDT-M **perpetual futures**
(the venue the strategy would trade: native shorting, real wick structure, funding):

| Data | Use | Coverage | Store |
|---|---|---|---|
| **15m klines** | decision context — the model's chart (default 288 bars = 3 days) | BTC/ETH 2020-01→, SOL 2020-09→, DOGE 2020-07→ (~217–235k bars) | `data/raw/intraday/<ASSET>_15m.csv.gz` |
| **1m klines** | first-passage evaluation of stops/targets | same (~3.3–3.5M bars) | `data/raw/intraday/<ASSET>_1m.csv.gz` |
| 1h + 5m klines | robustness checks / coarser fallback | same | on disk, same pattern |
| funding rates (8h) | H10 crowding benchmark + carry realism | same, via CDN monthly zips (~2-week lag acceptable) | `data/raw/funding/<ASSET>.csv.gz` |

Source: data.binance.vision bulk zips (monthly + current-month daily). Both
live Binance APIs (fapi + spot) return **451 (geo-blocked) on this machine**,
so freshest data lags ~1 day; the harvest therefore runs once daily and places
decisions retroactively at every 4h mark of the completed day — leakage-clean,
because each context ends at its mark and the model has no channel to later
bars. Bar index = bar OPEN time, UTC; the still-open bar is dropped.

**Geometry calibration (2026-09-18, `scripts/calibrate_geometry.py`, RR=2, 1m eval):**
stops of **0.3–1.0%** give median resolution 8 min–7 h with p90 ≤ 34 h and 1m
ambiguity ≤ 0.5% on all four names — squarely "usually <1 day, max 2–3 days."
Stops ≤ 0.1% are unresolvable even on 1m bars for SOL/DOGE (amb 5.6%) — treat
any LLM stop < 0.2% as a flagged cell.

**Cost hurdle at 15m (measured, E0-intraday):** with 20 bps round trip and the
baselines' 2σ/4σ geometry (stops 0.5–1%), cost is ~10–25% of the bracket:
breakeven TP-hit = (stop + cost)/(stop + tp) ≈ **42% vs the 33% random-walk
base** — an ~8.7 pp skill requirement, far steeper than the daily sleeve.
Consequences: (a) an LLM choosing tight stops bleeds mechanically (H12 is
amplified at this timeframe); (b) wider brackets or sparse conditional triggers
are the only realistic paths to net-positive; (c) baseline noise floor at this
timeframe = −19 to −21 bps/trade (pure cost drag), median holding ~2.4 h.

Data hygiene: adjusted closes; crypto uses UTC daily bars; equities use exchange close. Forward returns computed off the same series the context was built from — context and evaluation can never come from different adjustment states.

## 4. Cost model (the hurdle every edge must clear)

Per-side, retail-scale, conservative defaults (configurable in `configs/assets.yaml → costs`):

| Venue | Per-side (bps) | Round trip (bps) | Notes |
|---|---|---|---|
| Large-cap US equities / ETFs | 5 | 10 | spread ~1–2 + slippage + zero commission |
| Meme/attention equities | 10 | 20 | wider spreads; borrow cost for shorts NOT included — check per name |
| Crypto majors (perps) | 10 | 20 | taker ~5–7 + slippage; funding excluded (tracked separately — funding is itself a crowding signal) |

**Rule of thumb (bracket trades):** expectancy per trade ≈ p·tp − (1−p)·stop − round-trip cost, where p is the TP-hit probability. The random-walk base rate for p is stop/(stop+tp) (e.g. 33% for a 2:1 bracket), at which gross expectancy is ~0 — so **the entire net edge must come from p exceeding the geometry-implied base rate (or from fading a p that falls below it), by more than cost/(stop+tp).** Wider brackets amortize the fixed cost over a bigger range (2σ/4σ brackets resolve in ~10 days on average and make 10–20 bps costs small relative to the 6–17% ranges in crypto), which is why bracket trading is inherently friendlier to the cost hurdle than fixed 1-day holds — and why stops placed inside the noise band (H12) are so destructive: they maximize cost frequency while randomizing outcomes.

## 5. Decision record schema (`data/decisions/**/*.jsonl`)

Trade model (scope decision 2026-09-17): **one bracket order per decision** —
direction + stop-loss + take-profit, then hands-off until a level is hit.
There is no holding horizon; holding time is an *outcome*, not a parameter.

```json
{
  "ts_decision": "2026-09-17T21:15:03Z",
  "model": "claude-haiku-4-5",
  "model_version": "claude-haiku-4-5-20251001",
  "arm": "masked",                  // masked | informed
  "asset": "BTC-USD",
  "action": "long",                 // long | short | flat | error
  "stop_pct": 0.036,                // stop distance, fraction of entry (real space)
  "tp_pct": 0.072,                  // target distance, fraction of entry
  "confidence": 0.65,
  "reason": "recent momentum with declining volatility",
  "prompt_version": "masked-v2-bracket",
  "prompt_hash": "sha256:...",
  "context_end_date": "2026-09-17", // entry at this bar's close
  "price_at_decision": 117402.5,
  "run_id": "live"                  // live | backtest run id
}
```
One line per decision. Everything needed to reproduce or audit any trade forever.
When a masked context was vol-rescaled, the model's shown-space distances are
converted back to real space BEFORE logging (the record is always real-space).

## 6. Bracket (first-passage) evaluation rules — `nai/backtest.evaluate_brackets`

1. Entry at the close of `context_end_date`; scanning starts on the NEXT bar.
2. A gap through a level exits at that bar's OPEN (realistic gap fill), not at the level.
3. A bar touching BOTH levels intrabar is **ambiguous** (daily OHLC can't order them):
   pnl = NaN, excluded from headline stats, count reported (`amb%`). Measured at
   ~0.05% of trades with 2σ/4σ geometry; if an LLM's tighter geometry pushes this
   above ~2%, re-run the affected cells with intraday data before concluding anything.
   No pessimistic tie-break is used — a rule that punishes the model would flatter its fade.
4. A trade never resolved by data end is **open**: marked to market at the last close
   for info, excluded from TP-hit statistics.
5. Round-trip cost charged once per trade. Overlapping trades in the same asset are
   treated as independent tickets (capital netting is a later refinement that only
   lowers costs).
6. Skill is read as `tpHit%` vs `tpBase%` (= mean stop/(stop+tp), the random-walk
   base rate for the chosen geometry) — never vs 50%, and never vs 0.

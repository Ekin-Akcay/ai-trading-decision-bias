"""Engine sanity tests: known-OHLC bracket cases with exact expected outcomes."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.backtest import evaluate, evaluate_brackets  # noqa: E402
from nai.metrics import wilson_ci                     # noqa: E402
from nai.prompts import parse_decision                # noqa: E402

RT_COST = 0.0010  # SPY (equities_index): 5 bps/side => 10 bps round trip


def make_prices(bars):
    """bars: list of (open, high, low, close)."""
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1.0
    return df


def one_decision(prices, action, stop, tp, day=0):
    return pd.DataFrame([{
        "model": "test", "arm": "masked", "asset": "SPY", "action": action,
        "stop_pct": stop, "tp_pct": tp, "confidence": 0.5,
        "context_end_date": prices.index[day].strftime("%Y-%m-%d"),
    }])


def test_long_tp_hit():
    px = make_prices([(100, 100, 100, 100), (101, 103.5, 100.5, 103), (103, 104, 102, 102)])
    t = evaluate_brackets(one_decision(px, "long", 0.02, 0.03), {"SPY": px})
    r = t.iloc[0]
    assert r["outcome"] == "tp" and r["bars_held"] == 1
    assert np.isclose(r["exit_price"], 103.0)          # exit at TP level
    assert np.isclose(r["pnl"], 0.03 - RT_COST)
    assert np.isclose(r["mfe"], 0.035)                 # bar high 103.5
    assert np.isclose(r["mae"], 0.0)                   # low 100.5 never below entry


def test_long_sl_hit_and_short_mirror():
    px = make_prices([(100, 100, 100, 100), (99.5, 100.5, 97.9, 98.5), (98, 99, 97, 98)])
    t = evaluate_brackets(one_decision(px, "long", 0.02, 0.03), {"SPY": px})
    assert t.iloc[0]["outcome"] == "sl"
    assert np.isclose(t.iloc[0]["pnl"], -0.02 - RT_COST)
    # short: same bar's low 97.9 is a TP touch for a 2% short target
    s = evaluate_brackets(one_decision(px, "short", 0.03, 0.02), {"SPY": px})
    assert s.iloc[0]["outcome"] == "tp"
    assert np.isclose(s.iloc[0]["pnl"], 0.02 - RT_COST)


def test_gap_through_stop_exits_at_open():
    px = make_prices([(100, 100, 100, 100), (95, 96, 94, 95)])  # gap down through 2% stop
    t = evaluate_brackets(one_decision(px, "long", 0.02, 0.05), {"SPY": px})
    r = t.iloc[0]
    assert r["outcome"] == "sl"
    assert np.isclose(r["exit_price"], 95.0)           # open, not the 98 stop level
    assert np.isclose(r["pnl"], -0.05 - RT_COST)


def test_ambiguous_bar_excluded():
    px = make_prices([(100, 100, 100, 100), (100, 104, 97, 100)])  # touches both levels
    t = evaluate_brackets(one_decision(px, "long", 0.02, 0.03), {"SPY": px})
    r = t.iloc[0]
    assert r["outcome"] == "ambiguous" and np.isnan(r["pnl"])


def test_open_trade_marked_not_scored():
    px = make_prices([(100, 100, 100, 100), (100, 101, 99.5, 100.5)])
    t = evaluate_brackets(one_decision(px, "long", 0.05, 0.05), {"SPY": px})
    r = t.iloc[0]
    assert r["outcome"] == "open"
    assert np.isclose(r["pnl"], 0.005 - RT_COST)       # mark-to-market info only


def test_flat_and_error_rows():
    px = make_prices([(100, 100, 100, 100), (101, 102, 100, 101)])
    d = one_decision(px, "flat", 0.0, 0.0)
    t = evaluate_brackets(d, {"SPY": px})
    assert t.iloc[0]["outcome"] == "none" and t.iloc[0]["pnl"] == 0.0


def test_direction_diagnostic():
    px = make_prices([(100, 100, 100, 100), (110, 110, 110, 110), (99, 99, 99, 99)])
    d = pd.concat([one_decision(px, "long", 0.02, 0.04, day=0),
                   one_decision(px, "short", 0.02, 0.04, day=1)], ignore_index=True)
    t = evaluate(d, {"SPY": px}, horizon=1).set_index("context_end_date")
    assert np.isclose(t.loc["2024-01-01", "pnl"], 0.10 - RT_COST)
    assert np.isclose(t.loc["2024-01-02", "pnl"], 0.10 - RT_COST)


def test_timeout_exit():
    px = make_prices([(100, 100, 100, 100)] + [(100, 100.5, 99.5, 100.4)] * 5)
    t = evaluate_brackets(one_decision(px, "long", 0.05, 0.05), {"SPY": px}, max_bars=3)
    r = t.iloc[0]
    assert r["outcome"] == "timeout" and r["bars_held"] == 3
    assert np.isclose(r["pnl"], 0.004 - RT_COST)       # exit at close of bar entry+3


def test_cross_series_entry_mapping():
    # context: 15m bars; evaluation: 1m bars. Decision on ctx bar 00:00 (closes
    # 00:15) -> entry = close of 1m bar 00:14, scan starts at 1m bar 00:15.
    ctx_idx = pd.date_range("2024-01-01 00:00", periods=2, freq="15min")
    ctx = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                        "close": 100.0, "volume": 1.0}, index=ctx_idx)
    ev_idx = pd.date_range("2024-01-01 00:00", periods=30, freq="1min")
    ev = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                       "close": 100.0, "volume": 1.0}, index=ev_idx)
    ev.loc[ev_idx[20], ["high", "close"]] = [101.2, 101.1]   # TP touch at 00:20
    d = pd.DataFrame([{
        "model": "test", "arm": "masked", "asset": "SPY", "action": "long",
        "stop_pct": 0.02, "tp_pct": 0.01, "confidence": 0.5,
        "context_end_date": "2024-01-01T00:00",
    }])
    t = evaluate_brackets(d, {"SPY": ctx}, eval_prices={"SPY": ev},
                          context_bar_minutes=15)
    r = t.iloc[0]
    assert r["outcome"] == "tp"
    assert r["bars_held"] == 6                          # 00:14 entry -> 00:20 hit
    assert np.isclose(r["exit_price"], 101.0)


def test_wilson():
    lo, hi = wilson_ci(50, 100)
    assert lo < 0.5 < hi and 0.39 < lo < 0.41 and 0.59 < hi < 0.61


def test_parse_decision_brackets():
    good = parse_decision('{"action": "Long", "stop_loss_pct": 2.5, '
                          '"take_profit_pct": "5%", "confidence": 0.7, "reason": "x"}')
    assert good["action"] == "long"
    assert np.isclose(good["stop_pct"], 0.025) and np.isclose(good["tp_pct"], 0.05)
    flat = parse_decision('{"action": "flat", "stop_loss_pct": 0, "take_profit_pct": 0}')
    assert flat["action"] == "flat" and flat["stop_pct"] == 0.0
    missing = parse_decision('{"action": "short", "confidence": 0.9}')
    assert missing["action"] == "error"                # no stop = no trade
    insane = parse_decision('{"action": "long", "stop_loss_pct": 90, "take_profit_pct": 5}')
    assert insane["action"] == "error"                 # 90% stop fails sanity clamp
    junk = parse_decision("I cannot advise on trading.")
    assert junk["action"] == "error"

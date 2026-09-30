#!/usr/bin/env python3
"""Generate a self-contained HTML report for simulation runs.

  .venv/bin/python scripts/sim_report_html.py --runs agent-demo-haiku agent-demo-controls \
      --out data/sim/reports/agent-demo.html

AI models get per-trade cards (stimulus chart + decision + outcome + revealed
identity); baseline models appear in the summary table only. Chart PNGs are
embedded as data URIs so the file is fully portable.
"""
import argparse
import base64
import html
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nai.sim import read_rows, sim_rows_path, summarize_sim  # noqa: E402

BASELINES = {"random", "always-long", "momentum-20", "reversal-5"}
OUTCOME_LABEL = {"tp": "TARGET HIT", "sl": "STOPPED OUT", "timeout": "TIME-STOP",
                 "ambiguous": "AMBIGUOUS", "open": "STILL OPEN", "none": "NO TRADE"}
OUTCOME_CLASS = {"tp": "win", "sl": "loss", "timeout": "neut", "ambiguous": "neut",
                 "open": "neut", "none": "neut"}


def esc(s) -> str:
    return html.escape(str(s))


def fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:,.2f}"
    return f"${p:.4f}"


def fmt_minutes(m) -> str:
    m = int(m)
    if m < 60:
        return f"{m}m"
    return f"{m // 60}h {m % 60:02d}m"


def img_data_uri(rel_path: str) -> str | None:
    p = ROOT / rel_path
    if not p.exists():
        return None
    return "data:image/png;base64," + base64.standard_b64encode(p.read_bytes()).decode()


def pnl_chart_svg(ai: pd.DataFrame) -> str:
    vals = ai["pnl_gross_pct"].astype(float).tolist()
    labels = [a.split("-")[0] for a in ai["asset"]]
    n = len(vals)
    if n == 0:
        return ""
    W, H, ml, mr, mt, mb = 720, 230, 46, 10, 16, 30
    iw, ih = W - ml - mr, H - mt - mb
    vmax = max(0.1, max(abs(v) for v in vals)) * 1.25
    y0 = mt + ih * vmax / (2 * vmax)

    def y(v):
        return mt + ih * (vmax - v) / (2 * vmax)

    bw = iw / n * 0.62
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Gross P/L per trade">']
    parts.append(f'<line x1="{ml}" y1="{y0:.1f}" x2="{W - mr}" y2="{y0:.1f}" '
                 'stroke="var(--line)" stroke-width="1"/>')
    for gv in (vmax / 1.25, -vmax / 1.25):
        parts.append(f'<text x="{ml - 6}" y="{y(gv):.1f}" text-anchor="end" '
                     f'dominant-baseline="middle" class="ax">{gv:+.1f}%</text>')
    for i, v in enumerate(vals):
        x = ml + iw * (i + 0.5) / n - bw / 2
        cls = "barwin" if v >= 0 else "barloss"
        top, bot = (y(v), y0) if v >= 0 else (y0, y(v))
        parts.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" '
                     f'height="{max(bot - top, 1):.1f}" rx="2" class="{cls}"/>')
        ly = top - 5 if v >= 0 else bot + 12
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{ly:.1f}" text-anchor="middle" '
                     f'class="ax">{v:+.2f}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" text-anchor="middle" '
                     f'class="ax">{esc(labels[i])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def model_table(df: pd.DataFrame) -> str:
    s = summarize_sim(df).reset_index()
    cols = [("model", "model"), ("n", "trades"), ("long%", "long %"),
            ("tpHit%", "TP hit %"), ("tpBase%", "TP base %"),
            ("gross%/tr", "gross %/trade"), ("afterFees%/tr", "after fees"),
            ("med_min", "median hold"),
            ("stopW%", "stop w %"), ("tpW%", "target w %")]
    head = "".join(f"<th>{esc(h)}</th>" for _, h in cols)
    body = []
    for _, r in s.iterrows():
        tds = []
        for key, _ in cols:
            v = r.get(key)
            if key == "model":
                cls = ' class="mono strong"' if r["model"] not in BASELINES else ' class="mono"'
                tds.append(f"<td{cls}>{esc(v)}</td>")
            elif key == "med_min":
                tds.append(f"<td>{fmt_minutes(v) if pd.notna(v) else '—'}</td>")
            elif key in ("gross%/tr", "afterFees%/tr"):
                cls = "pos" if pd.notna(v) and v > 0 else "neg"
                tds.append(f'<td class="{cls}">{v:+.2f}%</td>' if pd.notna(v) else "<td>—</td>")
            else:
                tds.append(f"<td>{v:.1f}</td>" if pd.notna(v) else "<td>—</td>")
        marker = "" if r["model"] not in BASELINES else ' class="ctrl"'
        body.append(f"<tr{marker}>{''.join(tds)}</tr>")
    return (f'<div class="tblwrap"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _decision_row(r: pd.Series) -> str:
    oc = r["outcome"]
    pnl = r.get("pnl_gross_pct")
    pnl_html = (f'<span class="{ "pos" if pnl and pnl > 0 else "neg" }">'
                f'{pnl:+.2f}%</span>' if pd.notna(pnl) else "—")
    mfe = r.get("mfe_pct")
    nm = ""
    if oc == "sl" and pd.notna(mfe) and r["tp_pct"] > 0 and mfe >= 0.75 * r["tp_pct"] * 100:
        nm = '<span class="chip neut">NEAR MISS</span>'
    short_name = r["model"].replace("claude-", "").replace("-agent", "")
    if r["action"] in ("long", "short"):
        detail = (f'−{r["stop_pct"] * 100:.2f}% / +{r["tp_pct"] * 100:.2f}% '
                  f'· conf {r["confidence"]:.2f} · {fmt_minutes(r["minutes_held"])}')
    else:
        detail = f'conf {r["confidence"]:.2f}'
    act_cls = {"long": "long", "short": "short"}.get(r["action"], "neut")
    return f"""
    <div class="mrow">
      <span class="mname">{esc(short_name)}</span>
      <span class="chip {act_cls}">{esc(r['action'].upper())}</span>
      <span class="chip {OUTCOME_CLASS.get(oc, 'neut')}">{OUTCOME_LABEL.get(oc, oc)}</span>
      {nm}
      <span class="mdetail">{detail}</span>
      <span class="mpnl">{pnl_html}</span>
    </div>
    <p class="reason">“{esc(r['reason'])}”</p>"""


def window_card(group: pd.DataFrame) -> str:
    first = group.iloc[0]
    img = img_data_uri(first["image"]) if isinstance(first.get("image"), str) else None
    imgtag = f'<img src="{img}" alt="stimulus chart">' if img else ""
    rows = "".join(_decision_row(r) for _, r in group.iterrows())
    return f"""
<article class="card">
  {imgtag}
  <div class="cardbody">
    <div class="mrow assetline">
      <span class="chip asset">{esc(first['asset'])}</span>
      <span class="mdetail">{esc(str(first['window_end_ts'])[:16])} UTC · {fmt_price(float(first['price_real']))} <em>(hidden from the models)</em></span>
    </div>
    {rows}
  </div>
</article>"""


def asset_table(ai: pd.DataFrame) -> str:
    """AI performance broken down by (model, asset)."""
    rows = []
    for (model, asset), g in ai.groupby(["model", "asset"]):
        traded = g[g["action"].isin(["long", "short"])]
        hit = traded[traded["outcome"].isin(["tp", "sl"])]
        closed = traded[traded["outcome"].isin(["tp", "sl", "timeout"])]
        rows.append({
            "model": model.replace("claude-", "").replace("-agent", ""),
            "asset": asset, "trades": len(traded),
            "tpHit": (hit["outcome"] == "tp").mean() * 100 if len(hit) else None,
            "pnl": closed["pnl_gross_pct"].mean() if len(closed) else None,
            "held": closed["minutes_held"].median() if len(closed) else None,
        })
    rows.sort(key=lambda r: (r["asset"], r["model"]))
    body = []
    for r in rows:
        pnl = (f'<td class="{"pos" if r["pnl"] and r["pnl"] > 0 else "neg"}">{r["pnl"]:+.2f}%</td>'
               if r["pnl"] is not None else "<td>—</td>")
        body.append(
            f'<tr><td class="mono">{esc(r["asset"])}</td><td class="mono">{esc(r["model"])}</td>'
            f'<td>{r["trades"]}</td>'
            f'<td>{f"{r['tpHit']:.0f}%" if r["tpHit"] is not None else "—"}</td>'
            f'{pnl}'
            f'<td>{fmt_minutes(r["held"]) if r["held"] is not None else "—"}</td></tr>')
    return ('<div class="tblwrap"><table><thead><tr><th>asset</th><th>model</th>'
            '<th>trades</th><th>TP hit</th><th>gross %/trade</th><th>median hold</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def build(df: pd.DataFrame, title: str) -> str:
    ai = df[~df["model"].isin(BASELINES)].reset_index(drop=True)
    traded = ai[ai["action"].isin(["long", "short"])]
    hit = traded[traded["outcome"].isin(["tp", "sl"])]
    tp_rate = (hit["outcome"] == "tp").mean() * 100 if len(hit) else float("nan")
    tp_base = (traded["stop_pct"] / (traded["stop_pct"] + traded["tp_pct"])).mean() * 100
    pnl = traded["pnl_gross_pct"].astype(float)
    ai_models = sorted(ai["model"].unique())
    models_ai = ", ".join(ai_models)
    n_win = int((pnl > 0).sum())
    cards = "".join(window_card(g) for _, g in ai.groupby("window_id", sort=False))
    windows = df["window_id"].nunique()

    # third tile: winners for one model, direction agreement for two+
    if len(ai_models) >= 2:
        piv = traded.pivot_table(index="window_id", columns="model",
                                 values="action", aggfunc="first")
        both = piv.dropna()
        agree = int((both.nunique(axis=1) == 1).sum())
        tile3 = (f'<div class="tile"><span class="k">direction agreement</span>'
                 f'<span class="v">{agree}/{len(both)}</span>'
                 f'<span class="sub">windows both traded</span></div>')
    else:
        tile3 = (f'<div class="tile"><span class="k">winners</span>'
                 f'<span class="v">{n_win}/{len(traded)}</span></div>')

    charts = "".join(
        f'<h2>Gross P/L per trade — {esc(m)}</h2>'
        f'<div class="chartbox">{pnl_chart_svg(ai[ai["model"] == m].reset_index(drop=True))}</div>'
        for m in ai_models)

    return f"""<title>{esc(title)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
:root {{
  --bg:#f7f8f9; --surface:#ffffff; --ink:#16181d; --muted:#5c6470;
  --line:#dde1e6; --accent:#0e6e6a; --win:#1e8e5a; --loss:#c73e3e;
  --chipbg:#eef1f3; --sans:'IBM Plex Sans',system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#101318; --surface:#1a1e25; --ink:#e8eaee; --muted:#98a0ac;
  --line:#2b313a; --accent:#3fb5ae; --win:#35b578; --loss:#e0655f;
  --chipbg:#242a33; color-scheme:dark;
}} }}
:root[data-theme="dark"] {{
  --bg:#101318; --surface:#1a1e25; --ink:#e8eaee; --muted:#98a0ac;
  --line:#2b313a; --accent:#3fb5ae; --win:#35b578; --loss:#e0655f;
  --chipbg:#242a33; color-scheme:dark;
}}
body {{ background:var(--bg); color:var(--ink); font-family:var(--sans);
  margin:0; padding-block:32px 48px; padding-inline:16px; line-height:1.55; }}
main {{ max-width:1060px; margin:0 auto; display:flex; flex-direction:column; gap:36px; }}
header h1 {{ font-size:1.7rem; margin:0 0 4px; letter-spacing:-0.01em; text-wrap:balance; }}
header p {{ margin:0; color:var(--muted); font-size:.95rem; }}
.eyebrow {{ font-family:var(--mono); font-size:.72rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--accent); margin:0 0 10px; }}
h2 {{ font-size:1.05rem; margin:0 0 12px; }}
.tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.tile {{ background:var(--surface); border:1px solid var(--line); border-radius:8px;
  padding:14px 16px; }}
.tile .k {{ font-family:var(--mono); font-size:.7rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); display:block; margin-bottom:6px; }}
.tile .v {{ font-family:var(--mono); font-size:1.5rem; font-weight:600;
  font-variant-numeric:tabular-nums; }}
.tile .sub {{ color:var(--muted); font-size:.8rem; margin-left:6px; }}
.pos {{ color:var(--win); }} .neg {{ color:var(--loss); }}
.tblwrap {{ overflow-x:auto; background:var(--surface); border:1px solid var(--line);
  border-radius:8px; }}
table {{ border-collapse:collapse; width:100%; font-size:.86rem;
  font-variant-numeric:tabular-nums; }}
th,td {{ text-align:right; padding:9px 12px; border-bottom:1px solid var(--line); white-space:nowrap; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ font-family:var(--mono); font-size:.68rem; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); font-weight:500; }}
tr:last-child td {{ border-bottom:none; }}
tr.ctrl td {{ color:var(--muted); }}
.mono {{ font-family:var(--mono); }} .strong {{ font-weight:600; color:var(--accent); }}
.chartbox {{ background:var(--surface); border:1px solid var(--line); border-radius:8px;
  padding:16px; }}
.chartbox svg {{ width:100%; height:auto; display:block; }}
.ax {{ font-family:var(--mono); font-size:10px; fill:var(--muted); }}
.barwin {{ fill:var(--win); }} .barloss {{ fill:var(--loss); }}
.cards {{ display:grid; grid-template-columns:repeat(2,1fr); gap:16px; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:8px;
  overflow:hidden; display:flex; flex-direction:column; }}
.card img {{ width:100%; display:block; border-bottom:1px solid var(--line);
  background:#fff; }}
.cardbody {{ padding:14px 16px 16px; display:flex; flex-direction:column; gap:10px; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; }}
.chip {{ font-family:var(--mono); font-size:.68rem; font-weight:600; letter-spacing:.06em;
  padding:3px 9px; border-radius:99px; background:var(--chipbg); color:var(--muted); }}
.chip.long {{ background:color-mix(in srgb, var(--win) 14%, transparent); color:var(--win); }}
.chip.short {{ background:color-mix(in srgb, var(--loss) 14%, transparent); color:var(--loss); }}
.chip.win {{ background:var(--win); color:#fff; }}
.chip.loss {{ background:var(--loss); color:#fff; }}
.chip.asset {{ background:color-mix(in srgb, var(--accent) 14%, transparent);
  color:var(--accent); font-size:.74rem; }}
.assetline {{ padding-bottom:2px; border-bottom:1px solid var(--line); }}
.assetline em {{ font-style:normal; opacity:.75; }}
.grid2 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px 14px; }}
.grid2 .k {{ display:block; font-family:var(--mono); font-size:.64rem; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); }}
.grid2 .v {{ font-family:var(--mono); font-size:.9rem; font-variant-numeric:tabular-nums; }}
.reason {{ margin:0 0 4px; font-size:.84rem; color:var(--muted); border-left:3px solid var(--line);
  padding-left:10px; }}
.mrow {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.mname {{ font-family:var(--mono); font-size:.78rem; font-weight:600; color:var(--accent);
  min-width:52px; }}
.mdetail {{ font-family:var(--mono); font-size:.76rem; color:var(--muted); }}
.mpnl {{ font-family:var(--mono); font-size:.85rem; font-weight:600; margin-left:auto; }}
.reveal {{ margin:0; font-size:.8rem; color:var(--muted); }}
footer {{ color:var(--muted); font-size:.82rem; border-top:1px solid var(--line);
  padding-top:16px; }}
footer p {{ margin:0 0 6px; }}
@media (max-width:780px) {{ .tiles {{ grid-template-columns:repeat(2,1fr); }}
  .cards {{ grid-template-columns:1fr; }} .grid2 {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
<main>
<header>
  <p class="eyebrow">NAI Trading · anonymized-window simulation</p>
  <h1>{esc(title)}</h1>
  <p>{esc(" + ".join(sorted(df["asset"].unique())) if df["asset"].nunique() <= 2 else str(df["asset"].nunique()) + " assets")} ·
     {windows} windows · 15-minute bars, 40 visible · price rebased to 100, no dates ·
     resolved by first passage on 1-minute history · AI: {esc(models_ai)}</p>
</header>

<section>
  <div class="tiles">
    <div class="tile"><span class="k">gross P/L per trade (no fees)</span>
      <span class="v {'pos' if pnl.mean() > 0 else 'neg'}">{pnl.mean():+.2f}%</span></div>
    <div class="tile"><span class="k">target-hit rate</span>
      <span class="v">{tp_rate:.0f}%</span><span class="sub">vs {tp_base:.0f}% geometry base</span></div>
    {tile3}
    <div class="tile"><span class="k">median holding</span>
      <span class="v">{fmt_minutes(traded['minutes_held'].median())}</span></div>
  </div>
</section>

<section>
  <h2>Models vs controls</h2>
  {model_table(df)}
</section>

{f'<section><h2>Performance by asset</h2>{asset_table(ai)}</section>' if ai["asset"].nunique() > 1 else ''}

<section>
  {charts}
</section>

<section>
  <h2>Every trade: what the model saw, what it did, what happened</h2>
  <div class="cards">{cards}</div>
</section>

<footer>
  <p>Skill is read against each trade's own geometry base rate (stop ÷ (stop + target)), never against 50%. P/L shown is GROSS (pure price movement, no fees); the models table also shows after-fees at 20 bps round trip.</p>
  <p>Sample size is anecdotal ({len(traded)} AI trades); harness: {esc(ai['model_version'].iloc[0] if len(ai) else '')}. Windows are historical and anonymized — suggestive tier per the leakage rules; confirmation comes from post-cutoff and forward runs.</p>
</footer>
</main>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default="Run Report")
    ap.add_argument("--only-asset", default=None,
                    help="filter the report to one asset (scope: SOL-USD)")
    args = ap.parse_args()

    df = pd.concat([read_rows(sim_rows_path(r)) for r in args.runs], ignore_index=True)
    if args.only_asset:
        df = df[df["asset"] == args.only_asset].reset_index(drop=True)
    out = Path(args.out) if args.out else ROOT / "data" / "sim" / "reports" / f"{args.runs[0]}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(df, args.title))
    print(f"{len(df)} rows → {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()

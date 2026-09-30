"""Check artifact completeness, input isolation, numeric consistency and preservation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import hashlib,json,re
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=json.loads((HERE/'manifest.json').read_text());SHARED=ROOT/'data/sim/pricevolume-v3';checks=[]
def check(label,condition):
    assert condition,label;checks.append(label)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=json.loads((ROOT/'data/sim/rules2to1/window_list.json').read_text());check('100 exact canonical IDs and case order',[(c['case'],c['window_id']) for c in M['cases']]==[(c['case'],c['window_id']) for c in canonical])
for c in M['cases']:
    folder=Path(c['stimulus_dir']);old=(ROOT/c['original_prompt_file']).read_text();text=(folder/'stats.txt').read_text();oldbars=[s for s in old.splitlines() if ': O=' in s];newbars=[s for s in text.splitlines() if ': O=' in s]
    assert oldbars==newbars and len(newbars)==40
    assert not re.search(r'\bMA\d+\b|\bATR\b|Volatility|Indicators|std of|Move over',text,re.I)
    assert (folder/'input.txt').read_text()==M['contract']+'\n\n'+text
    assert sha(folder/'stats.txt')==c['prompt_sha256'] and sha(folder/'input.txt')==c['input_sha256'] and sha(folder/'chart.png')==c['image_sha256']
checks+=['4000 original OHLCV text rows preserved','100 inputs contain no MA/ATR/volatility/derived summary fields','100 exact wrapper/input/image hashes verified']
ledger=ROOT/'data/sim/decisions'/f"{M['run_id']}.jsonl";rows=[json.loads(s) for s in ledger.read_text().splitlines()];check('Exactly60 unique requested decisions',len(rows)==60 and len({(r['case'],r['model']) for r in rows})==60)
check('Each original model has cases1–20 only',all(sorted(r['case'] for r in rows if r['model']==model+'-agent')==list(range(1,21)) for model in M['models']))
check('No cases21–100 launched',all(int(d.name.split('_')[1])<=20 for d in (HERE/'cli_attempts').iterdir()))
check('All forced2:1 directions/stops/confidences valid',all(r['action'] in ['long','short'] and .0005<=r['stop_pct']<=.5 and r['tp_pct']==2*r['stop_pct'] and 0<=r['confidence']<=1 for r in rows))
audit=json.loads((HERE/'isolation_audit.json').read_text());check('60 exact-model single-turn text/image audits passed;zero calls',audit['accepted']==60 and audit['excluded']==0 and all(a['passed'] and a['full_input_received'] and a['received_image_count']==1 and not a['tool_calls'] for a in audit['audits']))
check('60 raw attempts and no retries',len(list((HERE/'cli_attempts').iterdir()))==60)
check('Real canonical entry matches every saved row',all(abs(r['entry_price']-M['cases'][r['case']-1]['price_real'])<1e-8 for r in rows))
check('Net subtracts20bps for every scored trade',all(abs(r['pnl_gross_pct']-r['pnl_net_pct']-.2)<1e-9 for r in rows))
pair=pd.read_csv(HERE/'paired_v2_v3.csv');check('All60 matched pairs present',len(pair)==60 and pair[['case','model']].drop_duplicates().shape[0]==60)
# Independent native15m close checks for all requested horizons.
px=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True)
for r in rows:
    for h in [15,30,105]:
        end=pd.Timestamp(r['window_end_ts'])+pd.Timedelta(minutes=h);expected=(px.loc[end,'close']/r['entry_price']-1)*100*(1 if r['action']=='long' else -1)
        assert abs(expected-r[f'signed_{h}m_pct'])<1e-8
checks+=['180 independent fixed-horizon native15m checks passed']
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id'in a:self.ids.append(a['id'])
        if tag in ['img','a']:
            x=a.get('src' if tag=='img' else 'href')
            if x:self.links.append(x)
report=ROOT/'data/sim/reports'/f"{M['run_id']}.html";parser=Links();parser.feed(report.read_text());broken=[]
for link in parser.links:
    u=urlsplit(link)
    if u.scheme:continue
    if not u.path:
        if u.fragment not in parser.ids:broken.append(link)
    elif not (report.parent/unquote(u.path)).exists():broken.append(link)
check('All report links/images/anchors resolve',not broken)
check('Report contains20 paired case sections',sum(x.startswith('case-') for x in parser.ids)==20)
original=json.loads((SHARED/'source_preservation.json').read_text());changed=[p for p,h in original.items() if sha(ROOT/p)!=h];check('All pre-existing source/result hashes unchanged',not changed)
progress=json.loads((HERE/'progress.json').read_text());check('Progress says requested batch complete and scored60',progress['status'].startswith('complete') and progress['scored_decisions']==60 and not progress['missing_requested_pairs'])
result={'status':'passed','checks':checks,'check_count':len(checks),'requested_cases':20,'prepared_cases':100,'saved_decisions':60,'future_native_close_checks':180,'original_files_unchanged':len(original),'bad_links':broken,'browser_preview_verified':False,'browser_note':'No alternate browser route attempted after earlier local-file preview policy block; data and static HTML checks used.','figure_visually_inspected':True}
(HERE/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

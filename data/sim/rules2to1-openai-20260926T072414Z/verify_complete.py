"""Final data, provenance, preservation, and report integrity checks."""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import hashlib,json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
m=json.loads((HERE/'manifest.json').read_text())
p=ROOT/'data/sim/decisions'/f"{m['run_id']}.jsonl"
rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
assert len(rows)==300 and len({(r['model'],r['window_id']) for r in rows})==300
assert p.read_bytes().startswith((HERE/'resume_initial_ledger.jsonl').read_bytes()), 'Prior 86 rows were altered'
for model in m['models']:
    rr=[r for r in rows if r['model']==model+'-agent']
    assert len(rr)==100 and {r['case_number'] for r in rr}==set(range(1,101))
    for r in rr:
        c=m['cases'][r['case_number']-1]
        assert r['window_id']==c['window_id'] and r['window_end_ts']==c['window_end_ts']
        assert r['stimulus_text_sha256']==c['prompt_sha256'] and r['stimulus_image_sha256']==c['image_sha256']
        assert r['action'] in ('long','short') and 0.0005<=r['stop_pct']<=0.5
        assert r['tp_pct']==2*r['stop_pct']
        assert math.isclose(r['entry_price'],c['price_real'],abs_tol=1e-9)
        if r['outcome'] in ('tp','sl','timeout'):
            assert math.isclose(r['pnl_gross_pct']-r['pnl_net_pct'],0.2,abs_tol=1e-9)
progress=json.loads((HERE/'progress.json').read_text());assert progress['status']=='complete' and not progress['missing_case_model_pairs']
audit=json.loads((HERE/'isolation_audit.json').read_text());assert audit['all_eligible_passed'] and audit['eligible_decisions']==300 and not audit['missing']
assert len({r['thread_id'] for r in rows})==300
for f,h in m['original_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
class P(HTMLParser):
    def __init__(self):super().__init__();self.cards=[];self.links=[];self.images=[];self.decisions=0
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if t=='article':self.cards.append(a.get('id'))
        if t=='a':self.links.append(a.get('href'))
        if t=='img':self.images.append(a.get('src'))
        if t=='span' and a.get('class')=='mname':self.decisions+=1
html_path=ROOT/'data/sim/reports'/f"{m['run_id']}.html"
doc=html_path.read_text();parser=P();parser.feed(doc)
assert 'PARTIAL' not in doc and 'Incomplete run' not in doc
assert parser.cards==[f'setup-{n}' for n in range(1,101)] and len(parser.images)==100 and parser.decisions==300
for link in parser.links:
    if link.startswith('#'):assert link[1:] in parser.cards
    elif not link.startswith(('http:','https:','data:')):assert (html_path.parent/link).exists(),link
qa={'ledger_rows':300,'unique_pairs':300,'fresh_threads':300,'all_exact_2to1':True,'all_directional':True,'report_cards':100,'report_decisions':300,'missing_local_links':[],'original_86_rows_unchanged':True,'original_protected_files_unchanged':len(m['original_sha256']),'cli_resumed_rows':sum(r['model_version'].endswith('Codex exec') for r in rows),'excluded_attempts':len(audit['excluded_attempts']),'outcomes':{model:dict(Counter(r['outcome'] for r in rows if r['model']==model+'-agent')) for model in m['models']}}
(HERE/'report_qa.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa,indent=2))

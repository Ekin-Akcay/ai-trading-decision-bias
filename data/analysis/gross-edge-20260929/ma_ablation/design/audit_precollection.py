"""Audit prepared stimuli only; does not load model responses or forward prices."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,tempfile
import numpy as np,pandas as pd
from PIL import Image,ImageFilter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];STUDY=HERE.parent
sys.path.insert(0,str(ROOT/'src'))
from nai.sim import build_snapshot,render_chart,sim_prompt
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=Path(json.loads((STUDY/'run.json').read_text())['run_dir']);m=json.loads((run/'manifest.json').read_text());sample=json.loads((HERE/'fresh_blocks.json').read_text())
assert len(m['cases'])==270 and m['unique_windows']==90 and len(sample['blocks'])==90
assert not (run/'ALLOW_EVALUATION').exists()
assert all(sha(ROOT/p)==h for p,h in m['original_sha256'].items())
assert sha(ROOT/m['protocol_file'])==m['protocol_sha256']
bars=pd.read_csv(ROOT/'data/raw/intraday/SOL-USD_15m.csv.gz',index_col=0,parse_dates=True).sort_index()
rng=np.random.default_rng(2026092996);results=[]
for block in range(1,91):
    cases=[c for c in m['cases'] if c['block']==block];assert len(cases)==3
    assert [c['arm'] for c in cases]==rng.permutation(['MA_A','MA_B','NO_MA']).tolist()
    c={r['arm']:r for r in cases};a,b,n=[Path(c[x]['stimulus_dir']) for x in ['MA_A','MA_B','NO_MA']]
    expected=pd.Timestamp(sample['blocks'][block-1]['entry_time']).tz_convert('UTC').tz_localize(None)
    assert all(pd.Timestamp(x['entry_time'])==expected for x in cases)
    assert len({x['window_id'] for x in cases})==1
    for x in cases:
        folder=Path(x['stimulus_dir'])
        for name,key in [('stats.txt','prompt_sha256'),('input.txt','input_sha256'),('chart.png','image_sha256')]:assert sha(folder/name)==x[key]
    for file in ['stats.txt','input.txt','chart.png']:assert (a/file).read_bytes()==(b/file).read_bytes()
    full=(a/'stats.txt').read_text();bare=(n/'stats.txt').read_text()
    removed=[line for line in full.splitlines() if line.startswith('Indicators (')];assert len(removed)==1
    assert bare=='\n'.join(line for line in full.splitlines() if not line.startswith('Indicators ('))
    assert 'MA20' not in bare and 'MA50' not in bare
    assert (a/'input.txt').read_text()==m['contract']+'\n\n'+full
    assert (n/'input.txt').read_text()==m['contract']+'\n\n'+bare
    snap=build_snapshot(bars,expected-pd.Timedelta(minutes=15),40,200)
    assert sim_prompt(snap)==full
    fa=np.array(Image.open(a/'chart.png').convert('RGB'));na=np.array(Image.open(n/'chart.png').convert('RGB'))
    assert fa.shape==na.shape
    changed=np.any(fa!=na,axis=2);yy,xx=np.where(changed);assert len(yy)>0
    assert not changed[int(fa.shape[0]*.75):].any(),'Volume/ticks changed'
    assert not changed[:,:45].any(),'Left-axis/crop shift'
    # Differences must lie at/adjacent to blue/orange MA artists (including antialias).
    f=fa.astype(int);r,g,bl=f[:,:,0],f[:,:,1],f[:,:,2]
    artists=((bl>g+10)&(g>r+10))|((r>g+10)&(g>bl+10))
    allowed=np.array(Image.fromarray((artists*255).astype('uint8')).filter(ImageFilter.MaxFilter(9)))>0
    weak_edge=(np.abs(fa.astype(int)-na.astype(int)).max(axis=2)<=2)
    assert not (changed&~allowed&~weak_edge).any(),'Material difference outside MA artist vicinity'
    # Verify the full-input plot is literally the canonical original rendering.
    with tempfile.TemporaryDirectory(dir=HERE) as temp:
        reference=Path(temp)/'canonical.png';render_chart(snap,reference)
        ra=np.array(Image.open(reference).convert('RGB'));assert ra.shape==fa.shape and np.array_equal(ra,fa),'Original render differs'
    results.append({'block':block,'shape':list(fa.shape),'MA_A_B_byte_identical':True,'only_MA_text_line_removed':True,'canonical_full_image_pixel_identical':True,'volume_axes_unchanged':True,'all_material_changes_near_MA_artists':True,'weak_edge_pixels_outside_color_mask':int((changed&~allowed).sum()),'changed_pixels':int(changed.sum()),'changed_bbox':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]})
    if block%15==0:print('Audited stimulus pairs',block,flush=True)
assert all(sha(ROOT/p)==h for p,h in m['original_sha256'].items())
out={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'run_id':m['run_id'],'calendar_windows':90,'isolated_inputs':270,'all_full_inputs_canonical_original_pixels':True,'all_MA_repeats_byte_identical':True,'all_ablations_only_one_MA_text_line_and_MA_artists':True,'fixed_pixel_dimensions_and_volume_axes_unchanged':True,'randomized_arm_order_reproduced':True,'all_source_and_stimulus_hashes_verified':True,'no_model_responses_or_forward_prices_loaded':True,'model_calls':0,'blocks':results}
(HERE/'precollection_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='blocks'},indent=2))

from pathlib import Path
from datetime import UTC,datetime
import hashlib,json,os,resource,sys,traceback,subprocess
import numpy as np
import polars as pl
ROOT=Path('/mnt/d/codex/coin')
sys.path.insert(0,str(ROOT))
from scripts.research_v8 import public_donchian_adapter as public
MIN=60_000_000
B=120*MIN
expected={'scripts/research_v8/public_donchian_adapter.py':'169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2',
 'scripts/investment/compare_simple_strategies.py':'5b42c2c8fca0d456a54d9a6d2cd6e9ae358b5f2d9485f13df66b29085818edbc',
 'tests/test_public_donchian_2h.py':'f59a29fca7b20f68ce6b4a9805a68c07a6b869cd0d8293633772a24e9a2415e8',
 'protocols/PUBLIC_DONCHIAN_2H_122D_V1.json':'8d67fe5a3bfcaa4f0c2666b069c3fe0000fad400dccc1b0d300a96fe1639cf51'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
 if not bool(v):raise ValueError(m)
report={'version':'PUBLIC_DONCHIAN_2H_INDEPENDENT_BOUNDARY_AUDIT_20261002_V1','status':'FAIL_STATIC_OR_EXACT_200BAR_BOUNDARY',
 'verified_source_hashes':expected,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'independent_source':str(Path(__file__)),'independent_source_sha256':sha(__file__),'independent_task_id':os.environ.get('COIN_TASK_ID'),
 'python':sys.executable,'cases':[],'market_inputs_read':False,'market_models_fit':0,'candidate_status':'NO_QUALIFIED_CANDIDATE'}
try:
 need({p:sha(ROOT/p) for p in expected}==expected,'Frozen2h bytes')
 start=int(datetime(2025,8,1,tzinfo=UTC).timestamp())*1_000_000
 stamps=np.arange(start-200*B,start,MIN,dtype=np.int64)
 bar=np.arange(len(stamps))//120
 prices=100.+bar*.05
 frames=[]
 for symbol,scale in (('BTCUSDT',100.),('ETHUSDT',10.)):
  close=prices*scale
  frames.append(pl.DataFrame({'symbol':[symbol]*len(stamps),'open_us':stamps,'high':close+scale*.001,
    'low':close-scale*.001,'close':close,'available_us':stamps+MIN}))
 frame=pl.concat(frames)
 calendar=np.arange(start,start+3*MIN,MIN,dtype=np.int64)
 bars=public.closed_hours(frame,timeframe_minutes=120)
 need(bars.height==400 and (bars['count']==120).all() and (bars['close_us']%B==0).all(),'Exact200 paired complete UTC2h bars')
 positive=public.fixed_targets(frame,calendar,timeframe_minutes=120)
 first=positive.calendar_ledger.filter(pl.col('decision_us')==start)
 need(not positive.receipt['warmup_failed'] and positive.receipt['paired_comparison_allowed']
      and positive.strategy_id=='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
      and first.height==2 and (first['target_weight']==.3).all(),'Exactly200 valid bars must be evaluable with non-vacuous long signal')
 report['cases'].append({'id':'EXACT200_COMPLETE_AVAILABLE_BARS','status':'PASS','bars_per_symbol':200,
    'first_decision_weights':first.select('symbol','target_weight').to_dicts(),'receipt_status':positive.receipt['status']})
 shorter=frame.filter(pl.col('open_us')>=start-199*B)
 negative=public.fixed_targets(shorter,calendar,timeframe_minutes=120)
 need(negative.receipt['warmup_failed'] and not negative.receipt['paired_comparison_allowed']
      and (negative.calendar_ledger['target_weight']==0).all()
      and negative.receipt['status']=='NOT_EVALUABLE_PAIRED_FOLD_WARMUP','199bar shortfall must not be admitted or traded')
 report['cases'].append({'id':'ONLY199_COMPLETE_AVAILABLE_BARS','status':'PASS','bars_per_symbol':199,
    'receipt_status':negative.receipt['status'],'all_intent_weights_zero':True})
 need({p:sha(ROOT/p) for p in expected}==expected,'Source changed during probe')
 report.update(status='PASS_2H_STATIC_AND_EXACT_WARMUP_BOUNDARY_ONLY',static_findings={
  'UTC_candles':'floor(open_us/120MIN); require120 unique minute-aligned samples with exactfirst/last; close=end; avail=max constituent availability',
  'causal_endpoint':'expected UTC120min close<=decision and199 adjacent deltas120MIN; all200 available<=decision',
  'hooks_and_risk':'Pinned originalhooks/DC20 excludescurrent/SMA200, common frozenrisk/funds/cost/execution unchanged; default60min route preserved',
  'predefined_scope':'Single120min strategy at fixed30/32/36bp and fixed122day window; known historical development, no new split or unseen claim',
  'missing_delayed_future':'Already covered by bound new builder tiny case; auditor did not rerun those cases; availability/warmup guard confirmed statically',
  'actual_accounts':'Not evaluated by this synthetic/static report; require separate actual3 completed0 audit'},
  registry_appended_by_auditor=False,locked_consumed=False,orders_sent=0)
except Exception as e:
 report.update(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc())
 raise
finally:
 report.update(created_utc=datetime.now(UTC).isoformat(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
 out=ROOT/'reports/fast_research/PUBLIC_DONCHIAN_2H_INDEPENDENT_BOUNDARY_AUDIT_20261002_V1.json'
 with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write(chr(10))
 print(json.dumps({'status':report['status'],'path':str(out),'sha256':sha(out),'task_id':report['independent_task_id']}))
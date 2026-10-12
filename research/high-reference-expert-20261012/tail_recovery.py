"""Audit the published genuine paid endpoint without advancing any account."""
import argparse,gzip,json,sys,time
from pathlib import Path
from decimal import Decimal as D,localcontext
import numpy as np
from driver import HERE,ROOT,Closing,native,SYMBOLS,sha,save,verify,load,b
from tail import TERMINAL,original_api

def restore(state,parent,artifact):
 assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in ('/workspace/expert-structure-state/OBSERVED_Y2023','/workspace/expert-structure-state/OBSERVED_Y2025','/workspace/expert-structure-state/TAIL_Y2025','/workspace/terminal-readiness-2025-state/OBSERVED','/workspace/portfolio-risk-2025-state/OBSERVED_STATIC50')):blocked.append(str(p));raise RuntimeError('Observed account forbidden during public paid endpoint recovery')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/summary/Y2025_EXIT/';ix=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'))
 for r in ix['members']:
  raw=b.git('show',artifact+':'+prefix+r['name']);assert len(raw)==r['bytes'] and __import__('hashlib').sha256(raw).hexdigest()==r['SHA256'];(state/r['name']).write_bytes(raw)
 r=json.loads((state/'TAIL.json').read_text());raw=gzip.decompress((state/'FINAL_ACCOUNT.json.gz').read_bytes());assert sha(state/'FINAL_ACCOUNT.json.gz')==r['final_snapshot_SHA256'] and __import__('hashlib').sha256(raw).hexdigest()==r['final_account_state_SHA256'];final=json.loads(raw)
 assert sha(parent/'RESULT.json')==r['original_annual_RESULT_SHA256'] and sha(parent/'ACCOUNT.json')==r['original_annual_ACCOUNT_SHA256'];ptr=json.loads((parent/'recovery/POINTER.json').read_text());assert ptr['state_hash']==r['parent_genuine_state_hash'] and ptr['snapshot_SHA256']==r['parent_snapshot_SHA256'];p=parent/'recovery'/ptr['snapshot_path'];assert sha(p)==ptr['snapshot_SHA256'];original=json.loads(gzip.decompress(p.read_bytes()))['account']
 api=original_api();f=load('unchanged_highref_tail_journal_verification',TERMINAL/'archive.py')
 native.NativeDailySimulator.advance_day=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('No financial advance authorized'))
 account=Closing.from_snapshot(final);assert account.snapshot()==final and account.summary()==r['after']
 with np.load(TERMINAL/'source/INPUTS.npz',allow_pickle=False) as z:prices={s:z[s+'_open'] for s in SYMBOLS};volume={s:z[s+'_quote_volume'] for s in SYMBOLS};marks={s:z[s+'_mark'] for s in SYMBOLS}
 assert sha(TERMINAL/'source/INPUTS.npz')==r['source_INPUTS_SHA256'] and sha(TERMINAL/'source/EVENTS.json')==r['source_EVENTS_SHA256'];events=json.loads((TERMINAL/'source/EVENTS.json').read_text());f.verify_tail_journals(original,final,r,events,marks)
 for k,v in original['fill_requests'].items():assert final['fill_requests'][k]==v
 for k,v in original['funding_events'].items():assert final['funding_events'][k]==v
 for row in r['requests']:
  at=row['event_us']-1;i=(at-api.START)//api.MINUTE;s=row['symbol'];assert 1<=i<60 and row['signal_us']==api.START and row['previous_quote_available_us']==at
  with localcontext() as c:c.prec=28;cap=D(str(float(volume[s][i-1])))*D('.001')/D(str(float(prices[s][i])))
  assert str(cap)==row['capacity_quantity'] and final['fill_requests'][row['fill_id']]['receipt']==row['receipt']
 _,q=native.episodes(account.trades,SYMBOLS)
 for s in SYMBOLS:assert q[s]==account.positions[s].quantity
 finance=native.nav_bridge(account.trades,account.funding,q,{s:float(account.marks[s][-1]['price']) for s in SYMBOLS},account.nav());assert finance==r['independent_decimal_NAV_bridge']
 save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_HIGH_REFERENCE_PAID_ENDPOINT_ZERO_ADVANCE',artifact_commit=artifact,parent_public_account=str(parent),all_old_maps_and_journal_prefixes='EXACT',new_requests_fills_funding_source_capacity='EXACT',paid_flat=r['paid_flat'],minutes=r['minutes'],final_account_state_SHA256=r['final_account_state_SHA256'],independent_decimal_NAV_bridge=finance,source_scope='REUSED_EXACT_ALREADY_PUBLIC_JAN1_HOUR_INPUTS_SHA_BOUND',observed_STATE_open_attempts=len(blocked),account_advances=0,new_short_tail_forks=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began));print('HIGH_REFERENCE_PAID_ENDPOINT_PUBLIC_RECOVERY_PASS',r['paid_flat'],time.monotonic()-began,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--artifact-commit',required=True);a=p.parse_args();restore(a.state,a.parent,a.artifact_commit)

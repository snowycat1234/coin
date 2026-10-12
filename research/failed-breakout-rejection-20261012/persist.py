"""Thin publication/recovery adapter; independent saved quantity arithmetic."""
import argparse,io,json,subprocess,sys,time,zipfile
from decimal import Decimal as D
from pathlib import Path
import numpy as np
from source import ROOT,HERE,sha,save
def pack(kind,source):
 dest=HERE/'public'/kind;assert not dest.exists();dest.mkdir(parents=True)
 names={'SOURCE':['Y2023_SOURCE.npz','Y2025_SOURCE.npz','SOURCE_PROJECTION.json'],'TARGETS':['Y2023.npz','Y2025.npz','PREPARATION.json'],'RESULTS':['RESULT.json']+[f'Y{y}_{a}.json' for y in (2023,2025) for a in ('FADE','FOLLOW')]}[kind];stream=io.BytesIO();members={}
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in names:
   b=(source/name).read_bytes();members[name]=dict(bytes=len(b),SHA256=sha(b));info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
 raw=stream.getvalue();assert len(raw)<6_000_000;(dest/'PACKET.zip').write_bytes(raw);save(dest/'INDEX.json',dict(kind=kind,bytes=len(raw),SHA256=sha(raw),members=members));print('REJECTED_BREAK_PUBLIC_PACKET',kind,len(raw),flush=True)
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and Path(args[0]).absolute().is_relative_to(Path('/workspace/failed-breakout-state')):blocked.append(str(args[0]));raise RuntimeError('Original experiment STATE forbidden')
 sys.addaudithook(audit);total=0
 for kind in ('SOURCE','TARGETS','RESULTS'):
  prefix=str(HERE.relative_to(ROOT))+'/public/'+kind+'/';index=json.loads(subprocess.check_output(['git','show',commit+':'+prefix+'INDEX.json'],cwd=ROOT));b=subprocess.check_output(['git','show',commit+':'+prefix+'PACKET.zip'],cwd=ROOT);assert len(b)==index['bytes'] and sha(b)==index['SHA256'];total+=len(b)
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   assert z.testzip() is None and len(z.namelist())==len(index['members']) and set(z.namelist())==set(index['members'])
   for name,r in index['members'].items():
    raw=z.read(name);assert len(raw)==r['bytes'] and sha(raw)==r['SHA256'];p=state/kind/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 prep=json.loads((state/'TARGETS/PREPARATION.json').read_text());src=json.loads((state/'SOURCE/SOURCE_PROJECTION.json').read_text());result=json.loads((state/'RESULTS/RESULT.json').read_text());assert sha((state/'SOURCE/SOURCE_PROJECTION.json').read_bytes())==prep['SOURCE_PROJECTION_SHA256'] and sha((state/'TARGETS/PREPARATION.json').read_bytes())==result['PREPARATION_SHA256'];checked=0;maximum=D(0)
 for year in (2023,2025):
  path=state/'SOURCE'/f'Y{year}_SOURCE.npz';assert sha(path.read_bytes())==src['years'][str(year)]['SOURCE_SHA256']==prep['years'][str(year)]['SOURCE_SHA256'];path=state/'TARGETS'/f'Y{year}.npz';assert sha(path.read_bytes())==prep['years'][str(year)]['INPUTS_SHA256']
  with np.load(path,allow_pickle=False) as z:
   np.testing.assert_array_equal(z['FADE'],-z['FOLLOW']);d=z['decision_us'];p0=z['p0'];p1=z['p1'];fp=z['funding_per_unit']
   for arm in ('FADE','FOLLOW'):
    account=json.loads((state/'RESULTS'/f'Y{year}_{arm}.json').read_text());assert account['summary']==result['years'][str(year)]['arms'][arm];previous=[D(0)]*5;before=D(10000)
    for i,row in enumerate(account['rows']):
     assert row['decision_us']==int(d[i]) and row['decision_us']<row['execution_us']<row['owned_end_us']<row['conservative_mature_us'];q=[D(str(v)) for v in row['held_quantity']];a=[D(str(v)) for v in p0[i]];b=[D(str(v)) for v in p1[i]];f=[D(str(v)) for v in fp[i]]
     pnl=sum((q[j]*(b[j]-a[j]) for j in range(5) if q[j]!=0),D(0));fund=sum((q[j]*f[j] for j in range(5) if q[j]!=0),D(0));cost=sum((abs(q[j]-previous[j])*a[j] for j in range(5) if q[j]!=previous[j]),D(0))*D('.00135')
     if i==364 and account['summary']['hypothetical_cost_terminal']:cost+=sum((abs(q[j])*b[j] for j in range(5)),D(0))*D('.00135')
     for observed,expected in [(row['nav_before'],before),(row['price_pnl'],pnl),(row['funding_debit_proxy'],fund),(row['trading_cost_proxy'],cost),(row['nav_after'],before+pnl-fund-cost)]:maximum=max(maximum,abs(D(str(observed))-expected))
     before=D(str(row['nav_after']));previous=q;checked+=1
 assert maximum<D('1e-8') and checked==1460 and not blocked
 proof=dict(status='PASS_EXACT_PUBLIC_REJECTED_BREAK_ZERO_REPLAY',artifact_commit=commit,packet_bytes=total,saved_daily_rows=checked,independent_Decimal_max_error_USDT=str(maximum),original_STATE_open_attempts=len(blocked),new_reference_calls=0,new_fits=0,new_native_wallets=0,provider_GETs=0,seconds=time.monotonic()-begin);save(state/'PUBLIC_RESTORE.json',proof);print('REJECTED_BREAK_ZERO_REPLAY_PASS',checked,str(maximum),proof['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['pack','restore']);p.add_argument('--kind',choices=['SOURCE','TARGETS','RESULTS']);p.add_argument('--source',type=Path);p.add_argument('--state',type=Path);p.add_argument('--artifact-commit');a=p.parse_args()
 if a.phase=='pack':pack(a.kind,a.source)
 else:restore(a.state,a.artifact_commit)

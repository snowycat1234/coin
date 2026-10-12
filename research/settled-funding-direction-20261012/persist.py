"""Exact public packets and zero-reference-call recovery with independent algebra."""
import argparse,io,json,subprocess,time,zipfile
from decimal import Decimal as D
from pathlib import Path
import numpy as np
from prepare import HERE,ROOT,sha,save
def pack(kind,source):
 destination=HERE/'public'/kind;assert not destination.exists();destination.mkdir(parents=True)
 names=['Y2023.npz','Y2025.npz','Y2023_RAW_EVENTS.json','Y2025_RAW_EVENTS.json','PREPARATION.json'] if kind=='INPUTS' else ['RESULT.json']+[f'Y{y}_{a}.json' for y in (2023,2025) for a in ('SHORT','CARRY')]
 stream=io.BytesIO();members={}
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in names:
   b=(source/name).read_bytes();members[name]=dict(bytes=len(b),SHA256=sha(b));info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
 raw=stream.getvalue();assert len(raw)<4_000_000;(destination/'PACKET.zip').write_bytes(raw);save(destination/'INDEX.json',dict(kind=kind,bytes=len(raw),SHA256=sha(raw),members=members,new_financial_calls=0));print('FINANCING_PUBLIC_PACKET',kind,len(raw),len(members),flush=True)
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);start=time.monotonic();opened=[]
 def forbid(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if p.is_relative_to(Path('/workspace/settled-funding-direction-state')):opened.append(str(p));raise RuntimeError('Original experiment STATE forbidden in cold restore')
 import sys;sys.addaudithook(forbid);total=0;membercount=0
 for kind in ('INPUTS','SCORES'):
  prefix=str(HERE.relative_to(ROOT))+'/public/'+kind+'/';index=json.loads(subprocess.check_output(['git','show',commit+':'+prefix+'INDEX.json'],cwd=ROOT));raw=subprocess.check_output(['git','show',commit+':'+prefix+'PACKET.zip'],cwd=ROOT);assert len(raw)==index['bytes'] and sha(raw)==index['SHA256'];total+=len(raw)
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   assert z.testzip() is None and set(z.namelist())==set(index['members']) and len(z.namelist())==len(index['members'])
   for name,r in index['members'].items():
    b=z.read(name);assert len(b)==r['bytes'] and sha(b)==r['SHA256'];p=state/kind/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);membercount+=1
 prep=json.loads((state/'INPUTS/PREPARATION.json').read_text());result=json.loads((state/'SCORES/RESULT.json').read_text());assert sha((state/'INPUTS/PREPARATION.json').read_bytes())==result['PREPARATION_SHA256'];rows_checked=0;maxerror=D(0)
 for year in (2023,2025):
  p=state/'INPUTS'/f'Y{year}.npz';assert sha(p.read_bytes())==prep['years'][str(year)]['INPUTS_SHA256']
  with np.load(p,allow_pickle=False) as z:
   d=z['decision_us'];p0=z['p0'];p1=z['p1'];fp=z['funding_per_unit']
   for arm in ('SHORT','CARRY'):
    account=json.loads((state/'SCORES'/f'Y{year}_{arm}.json').read_text());assert account['summary']==result['years'][str(year)]['arms'][arm];previous=[D(0)]*5;before=D(10000)
    for i,row in enumerate(account['rows']):
     assert row['decision_us']==int(d[i]) and row['decision_us']<row['execution_us']<row['owned_end_us']<row['conservative_mature_us']
     quantity=[D(str(v)) for v in row['held_quantity']];prices=[D(str(v)) for v in p0[i]];ends=[D(str(v)) for v in p1[i]];funds=[D(str(v)) for v in fp[i]]
     price=sum((quantity[j]*(ends[j]-prices[j]) for j in range(5) if quantity[j]!=0),D(0));fund=sum((quantity[j]*funds[j] for j in range(5) if quantity[j]!=0),D(0));cost=sum((abs(quantity[j]-previous[j])*prices[j] for j in range(5) if quantity[j]!=previous[j]),D(0))*D('.00135')
     if i==364 and account['summary']['hypothetical_cost_terminal']:cost+=sum((abs(quantity[j])*ends[j] for j in range(5)),D(0))*D('.00135')
     for observed,expected in [(row['nav_before'],before),(row['price_pnl'],price),(row['funding_debit_proxy'],fund),(row['trading_cost_proxy'],cost),(row['nav_after'],before+price-fund-cost)]:maxerror=max(maxerror,abs(D(str(observed))-expected))
     before=D(str(row['nav_after']));previous=quantity;rows_checked+=1
 assert maxerror<D('1e-8') and rows_checked==1460 and not opened
 proof=dict(status='PASS_EXACT_PUBLIC_FINANCING_DIRECTION_ZERO_REPLAY',artifact_commit=commit,packet_bytes=total,members=membercount,saved_daily_rows=rows_checked,independent_Decimal_cash_price_funding_cost_max_error_USDT=str(maxerror),new_reference_calls=0,new_fits=0,new_native_wallets=0,provider_GETs=0,original_STATE_open_attempts=len(opened),seconds=time.monotonic()-start);save(state/'PUBLIC_RESTORE.json',proof);print('FINANCING_PUBLIC_ZERO_REPLAY_PASS',rows_checked,str(maxerror),proof['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['pack','restore']);p.add_argument('--kind',choices=['INPUTS','SCORES']);p.add_argument('--source',type=Path);p.add_argument('--state',type=Path);p.add_argument('--artifact-commit');a=p.parse_args()
 if a.phase=='pack':pack(a.kind,a.source)
 else:restore(a.state,a.artifact_commit)

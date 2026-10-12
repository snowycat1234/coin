"""Read original paid-cost journals only; no account construction or advance."""
import argparse,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
from decimal import Decimal as D,localcontext
import numpy as np
import pandas as pd
from core import SYMBOLS,persistence,DAY
from run import utc,save,sha,HERE,ROOT
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def directions(body):
 out={label:dict(gross=D(0),fees=D(0),execution_cost=D(0),funding=D(0)) for label in ('LONG','SHORT')}
 with localcontext() as c:
  c.prec=50
  for r in body['trades']:
   x=r['decimal_strings'];owner=D(x['quantity_before']) if r['leg']=='CLOSE' else D(x['position_delta']);b=out['LONG' if owner>0 else 'SHORT'];b['gross']-=D(x['position_delta'])*D(x['mid_price']);b['fees']+=D(x['fee_amount']);b['execution_cost']+=D(x['execution_cost'])
  for s,row in body['summary']['positions'].items():
   q=D(row['decimal_strings']['quantity'])
   if q:out['LONG' if q>0 else 'SHORT']['gross']+=q*D(str(body['summary']['terminal_mark_prices'][s]))
  for r in body['funding']:
   if r['quantity']:out['LONG' if r['quantity']>0 else 'SHORT']['funding']+=D(r['decimal_strings']['signed_funding_USDT'])
  for row in out.values():row['net_contribution']=row['gross']-row['fees']-row['execution_cost']+row['funding']
  error=abs(sum(x['net_contribution'] for x in out.values())-D(body['summary']['decimal_strings']['net_PnL']));assert error<D('1e-8')
 return {label:{k:float(v) for k,v in row.items()} for label,row in out.items()},str(error)
def run(state):
 assert not state.exists();state.mkdir(parents=True);began=time.monotonic();model=json.loads((HERE/'model/MODEL.json').read_text());cases=[]
 configs=[('P1',['2021-04-01','2022-07-01'],'714e8f577284449774d3bd4b6089074958e1e7a5','research/cs-continuous-economics-20261012/native-result/','/workspace/cs-continuous-state/NATIVE_OBSERVED',False),('Y2023',['2023-01-01','2024-01-01'],'b8373a0167482f28a900e430b94a03433f947588','research/cs-2023-continuous-economics-20261012/native-result/','/workspace/cs-2023-state/NATIVE_OBSERVED',False),('Y2025',['2025-01-01','2026-01-01'],'af6d8e1426c663f3d5afb2da311755487681c232','research/portfolio-risk-2025-native-20261012/result/Y2025/','/workspace/portfolio-risk-2025-state',True)]
 for key,calendar,artifact,prefix,local,separate in configs:
  arms={};daily={}
  for arm in ('CS_MATCHED','VOL_MATCHED'):
   index=json.loads(git('show',artifact+':'+prefix+(arm+'/' if separate else '')+'INDEX.json'));root=Path(local)/('OBSERVED_'+arm if separate else arm);members={r['name']:r for r in index['members']};proof={}
   for name in ('ACCOUNT.json','DAILY.csv'):
    data=(root/name).read_bytes();r=members[name if separate else arm+'/'+name];assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['SHA256'];proof[name]=r['SHA256']
   body=json.loads((root/'ACCOUNT.json').read_text());parts,error=directions(body);summary=body['summary'];frame=pd.read_csv(root/'DAILY.csv');nav=np.r_[10000.,frame.nav.to_numpy()];daily[arm]=frame
   arms[arm]=dict(net_USDT=summary['net_PnL'],paid_flat=summary['terminal_cash_realized'],direction_contributions=parts,Decimal_full_wallet_bridge_error=error,original_byte_proof=proof,contract=summary['contract'],annual_daily_vol=float(np.std(np.diff(nav)/nav[:-1],ddof=1)*np.sqrt(365)))
  np.testing.assert_array_equal(daily['CS_MATCHED'].close_us,daily['VOL_MATCHED'].close_us)
  d=daily['CS_MATCHED'].close_us.to_numpy(np.int64)-DAY
  if key=='Y2025':
   import sys;sys.path.insert(0,str(ROOT/'research/portfolio-risk-2025-admission-20261012'))
   spec=importlib.util.spec_from_file_location('unchanged2025_public_causal_prices',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);t,p,_,_,_,_=m.causal_inputs()
  else:
   with np.load(ROOT/'research/monetary-policy-information-20261012/input/INPUTS.npz',allow_pickle=False) as z:t=z['close_available_us'];p=z['close']
  x=persistence(t,p,d);cs=np.r_[10000.,daily['CS_MATCHED'].nav.to_numpy()];hold=np.r_[10000.,daily['VOL_MATCHED'].nav.to_numpy()];delta=np.diff(cs)/cs[:-1]-np.diff(hold)/hold[:-1];groups=[]
  for j in (0,1):
   mask=np.isfinite(x)&((x>=model['threshold'])==j);groups.append(dict(bin=j,actual_dates=int(mask.sum()),mean_original_native_return_difference=float(delta[mask].mean()) if mask.any() else None))
  cases.append(dict(period=key,calendar=calendar,artifact_commit=artifact,arms=arms,rank_persistence_median=float(np.nanmedian(x)),rank_persistence_same_training_threshold=model['threshold'],original_native_advantage_by_bin=groups,scope='READ_ONLY_DIFFERENT_INDEPENDENT_SEEN_WALLETS_CONTRACT_SCOPE_RETAINED_NOT_ROUTED_INCOME'))
 report=dict(status='COMPLETE_READ_ONLY_ORIGINAL_DIRECTION_AND_PERSISTENCE_DIAGNOSIS',cases=cases,new_fits=0,new_wallets=0,account_advances=0,provider_requests=0,seconds=time.monotonic()-began,conclusion='CS2021-22 relativepositiveconcentrates2022H1/notall2021;2023shortlossesoffsetlonggains;2025directionsreportedwithdifferentcoarsecontract. Temporalrankpersistencealonecannotreliablyseparatematureconditionaladvantageacrossallpredeclaredfolds; no year/regime switching or causalproof.');save(state/'DIAGNOSIS.json',report)
 for row in cases:print('ORIGINAL_DIRECTION_DIAGNOSIS',row['period'],{arm:r['direction_contributions'] for arm,r in row['arms'].items()},row['original_native_advantage_by_bin'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);run(p.parse_args().state)

"""Causal signed target arithmetic from four byte-identical public originals."""
import base64,hashlib,io,json,subprocess,time
from datetime import date,datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];S=HERE/'public/ORIGINAL_TARGETS'
DAY=86400000000;SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def sha(b):return hashlib.sha256(b).hexdigest()
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
def load_json(p):return json.loads(p.read_text())
def clock(x):return int(datetime.combine(date.fromisoformat(x),datetime.min.time(),tzinfo=timezone.utc).timestamp()*1000000)
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def original(name):
 ix=load_json(S/'INDEX.json')['files'][name];raw=base64.b64decode((S/ix['UTF8_Base64_file']).read_bytes(),validate=False)
 assert len(raw)==ix['bytes'] and sha(raw)==ix['SHA256']==sha(git(ix['commit']+':'+ix['path']))
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k].copy() for k in ('decision_us','symbol_order',ix['selected_weights'])},ix
def validate(clock_us,order,w):
 assert tuple(order)==SYMBOLS and clock_us.shape==(365,) and w.shape==(365,5) and np.isfinite(w).all()
 assert np.abs(w).max()<=.3+1e-12 and np.abs(w).sum(axis=1).max()<=.6+1e-12
def mix(clock_a,order_a,a,clock_b,order_b,b,calendar):
 validate(clock_a,order_a,a);validate(clock_b,order_b,b)
 assert tuple(order_a)==tuple(order_b) and np.array_equal(clock_a,clock_b)
 np.testing.assert_array_equal(clock_a,np.arange(clock(calendar[0]),clock(calendar[1]),DAY,dtype=np.int64))
 result=.5*a+.5*b;validate(clock_a,order_a,result)
 assert np.all(np.abs(result)<=.5*np.abs(a)+.5*np.abs(b)+1e-15)
 return result
def run():
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
 P=load_json(HERE/'PROTOCOL.json');ix=load_json(S/'INDEX.json');dest=HERE/'input';assert not dest.exists();dest.mkdir();results={};begin=time.monotonic()
 for year,calendar in P['years'].items():
  s,si=original('STATIC50_'+year+'.npz');m,mi=original('SMA200_'+year+'.npz');a=s['STATIC50'];b=m['SMA200_10PCT']
  w=mix(s['decision_us'],s['symbol_order'],a,m['decision_us'],m['symbol_order'],b,calendar)
  ps=P['original_sources']['STATIC50_'+year+'.npz'];assert si['risk_SHA256']==sha(git(ps['commit']+':'+ps['risk_path']))
  static_prefix='research/portfolio-risk-budget-20261012/summary/P2/STATIC50/' if year=='Y2023' else 'research/portfolio-risk-2025-native-20261012/summary/STATIC50/'
  sma_prefix='research/sma200-native-20261013/summary/'+year+'/'
  static_commit=ps['commit'];sma_commit=mi['commit']
  sb=json.loads(git(static_commit+':'+static_prefix+'BINDING.json'));sr=json.loads(git(static_commit+':'+static_prefix+'RESULT.json'))
  mb=json.loads(git(sma_commit+':'+sma_prefix+'BINDING.json'));mr=json.loads(git(sma_commit+':'+sma_prefix+'RESULT.json'))
  assert sb['arm']==sr['arm']=='STATIC50' and mb['arm']==mr['arm']=='SMA200_10PCT'
  assert sb['target_archive_SHA256']==si['SHA256'] and mb['target_archive_SHA256']==mi['SHA256']
  assert sb['risk_proof_SHA256']==si['risk_SHA256'] and sb['source_index_SHA256']==mb['source_index_SHA256']
  assert sb['account_class']==mb['account_class']==sr['summary']['version']==mr['summary']['version']
  assert sb['quantity_profile_SHA256']==mb['quantity_profile_SHA256']==sr['summary']['contract']['quantity_profile_SHA256']==mr['summary']['contract']['quantity_profile_SHA256']
  assert sb['contract_from_initial_capital'] is mb['contract_from_initial_capital'] is True
  assert sr['calendar']==mr['calendar']==mb['calendar']==calendar
  assert sr['summary']['completed_minutes']==mr['summary']['completed_minutes']==525600
  assert sr['summary']['contract']==mr['summary']['contract'] and sr['summary']['cost_scenario']==mr['summary']['cost_scenario']
  for path in ('scripts/investment/resumable_perpetual.py','scripts/investment/perpetual_closing_exempt_account.py','research/quantity-grid-sensitivity-20261012/grid_account.py','src/quant/perpetual_account.py'):
   assert git(sb['science_source_commit']+':'+path)==git(mb['science_source_commit']+':'+path),path
  p=dest/(year+'.npz');np.savez_compressed(p,decision_us=s['decision_us'],symbol_order=s['symbol_order'],STATIC50=a,SMA200_10PCT=b,COMBINED=w)
  with np.load(p,allow_pickle=False) as z:
   np.testing.assert_array_equal(z['COMBINED'],.5*z['STATIC50']+.5*z['SMA200_10PCT']);np.testing.assert_array_equal(z['decision_us'],s['decision_us'])
  opposed=(a*b<0);internal_nettable=.5*np.abs(a)+.5*np.abs(b)-np.abs(w)
  assert np.all(internal_nettable>=-1e-15)
  results[year]=dict(calendar=calendar,source_SHA256={'STATIC50':si['SHA256'],'SMA200_10PCT':mi['SHA256']},risk_SHA256=si['risk_SHA256'],target_SHA256=sha(p.read_bytes()),days=365,asset_days=1825,opposed_asset_days=int(opposed.sum()),same_signed_asset_days=int(((a*b)>0).sum()),one_or_both_zero_asset_days=int(((a*b)==0).sum()),mean_STATIC50_gross=float(np.abs(a).sum(axis=1).mean()),mean_SMA_gross=float(np.abs(b).sum(axis=1).mean()),mean_combined_gross=float(np.abs(w).sum(axis=1).mean()),max_combined_asset=float(np.abs(w).max()),max_combined_gross=float(np.abs(w).sum(axis=1).max()),mean_internal_nettable_gross=float(internal_nettable.sum(axis=1).mean()),source_index_SHA256=sb['source_index_SHA256'],account_class=sb['account_class'],quantity_profile_SHA256=sb['quantity_profile_SHA256'],financial_code_byte_identity='EXACT',cost_contract_identity='EXACT',outcomes_used_in_target='NONE')
  print('ACTUAL_STATIC50_SMA_TARGET_READY',year,results[year]['target_SHA256'],flush=True)
 save(dest/'READINESS.json',dict(status='PASS_FROZEN_SAVED_STATIC50_PLUS_ORIGINAL_SMA_EQUAL_HALF_TARGETS',protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),original_export_INDEX_SHA256=sha((S/'INDEX.json').read_bytes()),years=results,new_wallets=0,old_wallet_replays=0,fits=0,downloads=0,RNG=0,seconds=time.monotonic()-begin))
if __name__=='__main__':run()

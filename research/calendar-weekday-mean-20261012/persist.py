"""Exact public saved model/forecasts, zero fits or economic replays."""
import argparse,io,json,subprocess,sys,time,zipfile
from pathlib import Path
import numpy as np
from core import weekday,FIT,DAY
from prepare import ROOT,HERE,sha,save
def pack(kind,source):
 dest=HERE/'public'/kind;assert not dest.exists();dest.mkdir(parents=True)
 names={'INPUTS':['TRAIN_INPUTS.npz','Y2023.npz','Y2025.npz','PREPARATION.json'],'MODEL':['MODEL.json','TRAINING.json'],'SCORES':['Y2023_FORECASTS.npz','Y2025_FORECASTS.npz','RESULT.json']}[kind];members={};stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in names:
   raw=(source/name).read_bytes();members[name]=dict(bytes=len(raw),SHA256=sha(raw));info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
 raw=stream.getvalue();assert len(raw)<4_000_000;(dest/'PACKET.zip').write_bytes(raw);save(dest/'INDEX.json',dict(kind=kind,bytes=len(raw),SHA256=sha(raw),members=members));print('CALENDAR_PUBLIC_PACKET',kind,len(raw),flush=True)
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();blocked=[];total=0
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and Path(args[0]).absolute().is_relative_to(Path('/workspace/calendar-weekday-state')):blocked.append(str(args[0]));raise RuntimeError('Original experiment STATE forbidden')
 sys.addaudithook(audit)
 for kind in ('INPUTS','MODEL','SCORES'):
  prefix=str(HERE.relative_to(ROOT))+'/public/'+kind+'/';ix=json.loads(subprocess.check_output(['git','show',commit+':'+prefix+'INDEX.json'],cwd=ROOT));raw=subprocess.check_output(['git','show',commit+':'+prefix+'PACKET.zip'],cwd=ROOT);assert sha(raw)==ix['SHA256'] and len(raw)==ix['bytes'];total+=len(raw)
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   assert z.testzip() is None and set(z.namelist())==set(ix['members']) and len(z.namelist())==len(ix['members'])
   for name,r in ix['members'].items():
    b=z.read(name);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];p=state/kind/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 model=json.loads((state/'MODEL/MODEL.json').read_text());result=json.loads((state/'SCORES/RESULT.json').read_text());prep=json.loads((state/'INPUTS/PREPARATION.json').read_text());assert sha((state/'MODEL/MODEL.json').read_bytes())==result['MODEL_SHA256'] and sha((state/'INPUTS/PREPARATION.json').read_bytes())==model['PREPARATION_SHA256']==result['PREPARATION_SHA256'];checks={}
 with np.load(state/'INPUTS/TRAIN_INPUTS.npz',allow_pickle=False) as z:
  ix=np.array(model['train_indices']);d=z['decision_us'];y=z['price_return'][ix];m=z['label_mature_us'];np.testing.assert_array_equal(ix,np.flatnonzero(np.isfinite(z['price_return']).all(1)&(m<FIT)));assert int(m[ix].max())==model['maximum_train_maturity_us']<FIT;wd=weekday(d[ix]);means=np.array(model['mean_by_weekday']);constant=np.array(model['constant_mean']);sigma=np.array(model['training_std']);counts=np.bincount(wd,minlength=7);np.testing.assert_array_equal(counts,model['weekday_train_counts'])
  conditional_residual=np.max(np.abs(np.stack([(y[wd==k]-means[k]).sum(0) for k in range(7)])));constant_residual=np.max(np.abs((y-constant).sum(0)));variance_residual=np.max(np.abs(((y-constant)**2).sum(0)-(len(y)-1)*sigma**2));assert conditional_residual<1e-10 and constant_residual<1e-10 and variance_residual<1e-10
 for year in (2023,2025):
  p=state/'INPUTS'/f'Y{year}.npz';assert sha(p.read_bytes())==prep['validation'][str(year)]['INPUTS_SHA256'];p=state/'SCORES'/f'Y{year}_FORECASTS.npz';assert sha(p.read_bytes())==result['years'][str(year)]['FORECASTS_SHA256']
  with np.load(p,allow_pickle=False) as z:
   a=means[weekday(z['decision_us'])];b=np.broadcast_to(constant,a.shape);np.testing.assert_array_equal(a,z['candidate_prediction']);np.testing.assert_array_equal(b,z['constant_prediction']);la=((z['price_return']-a)/sigma)**2;lb=((z['price_return']-b)/sigma)**2;np.testing.assert_array_equal(la,z['candidate_normalized_squared_loss']);np.testing.assert_array_equal(lb,z['constant_normalized_squared_loss']);np.testing.assert_array_equal((lb-la).mean(1),z['paired_date_loss_improvement']);assert float(la.mean())==result['years'][str(year)]['candidate_normalized_MSE'] and float(lb.mean())==result['years'][str(year)]['constant_normalized_MSE'];checks[str(year)]=dict(natural_dates=365,asset_forecasts=1825,forecast_and_loss_bits='EXACT',bootstrap='SAVED_ORIGINAL_CI_NO_NEW_RNG')
 proof=dict(status='PASS_EXACT_PUBLIC_CALENDAR_ZERO_REFIT',artifact_commit=commit,packet_bytes=total,train_dates=len(ix),training_optimum_residual_max=float(conditional_residual),constant_residual_max=float(constant_residual),normalizer_variance_residual_max=float(variance_residual),validation=checks,new_fits=0,new_prediction_sets=0,new_bootstrap_draws=0,new_references=0,new_native_wallets=0,provider_GETs=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);assert not blocked;save(state/'PUBLIC_RESTORE.json',proof);print('CALENDAR_ZERO_REFIT_PASS',len(ix),3650,proof['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['pack','restore']);p.add_argument('--kind',choices=['INPUTS','MODEL','SCORES']);p.add_argument('--source',type=Path);p.add_argument('--state',type=Path);p.add_argument('--artifact-commit');a=p.parse_args()
 if a.phase=='pack':pack(a.kind,a.source)
 else:restore(a.state,a.artifact_commit)

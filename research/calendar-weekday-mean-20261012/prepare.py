"""Exact public price labels; no old policy-known or teacher sample selection."""
import argparse,io,json,time,subprocess,importlib.util
from pathlib import Path
import numpy as np
from core import DAY,START,FIT
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('calendar_public_source_loader',ROOT/'research/failed-breakout-rejection-20261012/source.py');sha=old.sha;save=old.save;SYMBOLS=old.SYMBOLS
def prepare(state):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();commit='53056adaa3b54f93ef6859269106ac288331dd9c';prefix='research/monetary-policy-information-20261012/input/';raw=subprocess.check_output(['git','show',commit+':'+prefix+'INPUTS.npz'],cwd=ROOT);assert sha(raw)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
 meta=json.loads(subprocess.check_output(['git','show',commit+':'+prefix+'PREPARATION.json'],cwd=ROOT));assert tuple(meta['symbol_order'])==SYMBOLS
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:
  ids=(z['decision_us']>=START)&(z['decision_us']<FIT);d=z['decision_us'][ids];p0=z['p0'][ids];p1=z['p1'][ids]
 assert len(d)==730 and np.all(np.diff(d)==DAY);valid=np.isfinite(p0)&np.isfinite(p1)&(p0>0)&(p1>0);y=np.full_like(p0,np.nan);np.divide(p1,p0,out=y,where=valid);y[valid]-=1;mature=d+2*DAY
 np.savez_compressed(state/'TRAIN_INPUTS.npz',symbol_order=np.array(SYMBOLS),decision_us=d,p0=p0,p1=p1,price_return=y,label_mature_us=mature)
 common=np.isfinite(y).all(1);mature_ok=mature<FIT;report=dict(natural_train_dates=730,common_known_price_dates=int(common.sum()),common_mature_train_dates=int((common&mature_ok).sum()),purge_dates=d[~mature_ok].tolist(),source_unknown_dates=d[~common].tolist(),source_commit=commit,source_INPUTS_SHA256=sha(raw),TRAIN_INPUTS_SHA256=sha((state/'TRAIN_INPUTS.npz').read_bytes()),old_known_training_indices_teacher_reused=False)
 economics,proof=old.economics();evalproof={}
 for year,inp in economics.items():
  assert len(inp['decision_us'])==365 and int(inp['decision_us'][0])==int(np.datetime64(f'{year}-01-01','us').astype('int64'));assert np.isfinite(inp['p0']).all() and np.isfinite(inp['p1']).all() and (inp['p0']>0).all() and (inp['p1']>0).all();labels=inp['p1']/inp['p0']-1;np.savez_compressed(state/f'Y{year}.npz',**inp,price_return=labels,label_mature_us=inp['decision_us']+2*DAY);evalproof[str(year)]=dict(rows=365,known_asset_labels=1825,INPUTS_SHA256=sha((state/f'Y{year}.npz').read_bytes()))
 save(state/'PREPARATION.json',dict(status='PASS_REAL_CALENDAR_PRICE_LABEL_SOURCE',train=report,validation=evalproof,validation_source=proof,protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),new_fits=0,new_references=0,provider_GETs=0,seconds=time.monotonic()-begin));assert time.monotonic()-begin<120;print('ACTUAL_CALENDAR_SOURCE_READY',report['common_mature_train_dates'],365,365,report['source_unknown_dates'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();prepare(a.state)

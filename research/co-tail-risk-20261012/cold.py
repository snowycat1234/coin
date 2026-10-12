"""Public saved-parameter arithmetic; no fitting, RNG, provider or original STATE."""
import argparse,json,sys,time
from pathlib import Path
import numpy as np
from core import DAY,FIT,cohort,assemble,predict,qlike
from source import original,aligned,npz
from util import HERE,save,verify,public_packet
PREFIX='research/co-tail-risk-20261012/public/'
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();blocked=[];prefixes=json.loads((HERE/'evidence/ORIGINAL_STATE_PREFIXES.json').read_text())
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and any(Path(args[0]).absolute().is_relative_to(Path(p)) for p in prefixes):blocked.append(str(args[0]));raise RuntimeError('Original scientific STATE forbidden')
 sys.addaudithook(audit);verify();packets={};indices={};total=0
 for kind in ('INPUTS','MODEL','SCORES'):
  packet,index=public_packet(commit,PREFIX+kind+'/');packets[kind]=packet;indices[kind]=index;total+=index['bytes']
  for name,b in packet.items():
   n=Path(name);assert not n.is_absolute() and '..' not in n.parts;p=state/kind/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 old,oi=original();prep=json.loads(packets['INPUTS']['PREPARATION.json']);m=json.loads(packets['MODEL']['MODEL.json']);r=json.loads(packets['SCORES']['RESULTS.json']);assert oi['SHA256']==prep['original_packet_SHA256']==m['original_packet_SHA256'];assert m['inputs_packet_SHA256']==r['inputs_packet_SHA256']==indices['INPUTS']['SHA256'] and r['model_packet_SHA256']==indices['MODEL']['SHA256'];assert m['inputs_commit']==r['inputs_commit']
 a=npz(packets['INPUTS']['TRAIN.npz']);derived,z=aligned(old['TRAIN.npz'])
 for k in a:np.testing.assert_array_equal(a[k],derived[k])
 ix=cohort(a['decision_us'],a['base_features'],a['causal_sigma5m'],a['target_basket_RV'],a['label_mature_us']);np.testing.assert_array_equal(ix,m['train_indices']);np.testing.assert_array_equal(a['decision_us'][ix],prep['admitted_decisions']);assert len(ix)==prep['train_common_dates']==696 and int(a['label_mature_us'][ix].max())==m['maximum_train_maturity_us']<FIT
 # Verify the saved threshold's two order statistics, without choosing a new threshold.
 ordered=np.sort(np.abs(z[ix]).reshape(-1,5),axis=0);position=.95*(len(ordered)-1);lo=int(np.floor(position));fraction=position-lo
 expected=ordered[lo+1]-(ordered[lo+1]-ordered[lo])*(1-fraction) if fraction>=.5 else ordered[lo]+(ordered[lo+1]-ordered[lo])*fraction
 np.testing.assert_array_equal(expected,m['threshold_absZ_q95']);assert len(ordered)==m['threshold_observations_per_asset'];x=assemble(a['base_features'],z,np.array(m['threshold_absZ_q95']));np.testing.assert_array_equal(x[ix].mean(0),m['feature_mean']);np.testing.assert_array_equal(x[ix].std(0,ddof=1),m['feature_std']);scaled=(x[ix]-np.array(m['feature_mean']))/np.array(m['feature_std']);target=np.log(a['target_basket_RV'][ix]);residual=0.
 for arm,k in (('CONTROL',33),('CO_TAIL',34)):
  design=np.column_stack([np.ones(len(ix)),scaled[:,:k]]);error=target-design@np.array(m['coefficients'][arm]);residual=max(residual,float(np.abs(design.T@error).max()));assert float(np.exp(error).mean())==m['smearing'][arm]
 assert residual<1e-8;tr=npz(old['TRAIN.npz']);v23=npz(old['Y2023.npz']);v25=npz(old['Y2025.npz']);np.testing.assert_array_equal(v23['previous_close'],tr['five_close'][698,-1]);np.testing.assert_array_equal(v25['previous_close'],[q['final_close'] for q in prep['anchor2025']]);assert all(q['minute_grid']==43200 and q['available_us']==1733011200000000 for q in prep['anchor2025']);years={}
 for year in (2023,2025):
  a=npz(packets['INPUTS'][f'Y{year}.npz']);derived,z=aligned(old[f'Y{year}.npz'])
  for k in a:np.testing.assert_array_equal(a[k],derived[k])
  s=npz(packets['SCORES'][f'Y{year}.npz']);np.testing.assert_array_equal(a['decision_us'],s['decision_us']);assert len(a['decision_us'])==365 and np.all(np.diff(a['decision_us'])==DAY);pred,x=predict(m,a['base_features'],z);np.testing.assert_array_equal(x,s['full_features']);np.testing.assert_array_equal(pred['CO_TAIL'],s['candidate_basket_RV']);np.testing.assert_array_equal(pred['CONTROL'],s['control_basket_RV']);lc=qlike(a['target_basket_RV'],pred['CO_TAIL']);lb=qlike(a['target_basket_RV'],pred['CONTROL']);delta=lb-lc
  for k,val in (('candidate_QLIKE',lc),('control_QLIKE',lb),('daily_loss_increment',delta)):np.testing.assert_array_equal(val,s[k])
  assert s['bootstrap_starts'].shape==(1000,27);saved=np.array([float(delta[((v[:,None]+np.arange(14))%365).ravel()[:365]].mean()) for v in s['bootstrap_starts']]);np.testing.assert_array_equal(saved,s['bootstrap_means']);row=r['years'][str(year)];assert float(lc.mean())==row['candidate_QLIKE'] and float(lb.mean())==row['control_QLIKE'] and float(1-lc.mean()/lb.mean())==row['relative_QLIKE_gain'];assert [float(v) for v in np.quantile(saved,[.025,.975])]==row['paired14day95CI'] and not row['information_pass'];years[str(year)]=dict(days=365,base_scale_label_event_features_prediction_loss_bootstrap_bits='EXACT')
 assert r['status']=='STOP_FIXED_CO_TAIL_RISK_INFORMATION_GATE' and r['new_economic_refs']==r['new_native_wallets']==r['new_validation_fits']==0 and not blocked
 proof=dict(status='PASS_EXACT_PUBLIC_CO_TAIL_ZERO_REFIT',artifact_commit=commit,public_bytes=total,original_public_source_packet_SHA256=oi['SHA256'],public_source_transport='PREVIOUSLY_VERIFIED_PUBLIC_GIT_OBJECT_CACHE_FRESH_WORKTREE_AND_STATE',train_common_dates=len(ix),stored_threshold_order_statistic_certificates=5,OLS_optimum_residual_max=residual,validation=years,saved_forecast_scalar_checks=1460,saved_bootstrap_mean_checks=2000,November2024_full_month_reparse='NOT_RUN_COLD_PRIOR_SOURCE_PARSE_RECEIPTS_AND_EXACT_ANCHOR_REUSED',new_fits=0,new_scientific_prediction_sets=0,new_RNG_draws=0,new_economic_refs=0,new_native_wallets=0,provider_GETs=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);save(state/'PUBLIC_RESTORE.json',proof);print('ACTUAL_CO_TAIL_PUBLIC_COLD_PASS',len(ix),total,residual,proof['seconds'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--state',type=Path,required=True);q.add_argument('--artifact-commit',required=True);a=q.parse_args();restore(a.state,a.artifact_commit)

"""Original complete HEADROOM recovery path, forbid all financial transitions."""
import os,sys,json,hashlib,time,tempfile,resource,importlib.util,copy,traceback
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--candidate-root',type=Path,required=True);parser.add_argument('--workspace-root',type=Path,required=True);parser.add_argument('--wallet',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--feature',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--temporary-parent',type=Path,required=True);args=parser.parse_args()
R=args.temporary_parent.resolve();B=args.candidate_root.resolve();W=args.workspace_root.resolve();O=args.wallet.resolve();S=args.source.resolve();F=args.feature.resolve();assert R.is_dir() and not args.output.exists();started=time.monotonic()
os.environ.update(COIN_HEADROOM_WORKSPACE=str(W),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1');sys.path.insert(0,str(B));resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
from freeze_candidate import verify
verify(W,require_review=True)
from source_adapter import load_port,source_window
from feature_tape import FeatureTape
port=load_port(W)
from fine_account import FineGridAccount
from headroom_policy import HeadroomFullExitSimulator
case=next(c for c in json.loads((B/'CASE_BINDINGS.json').read_text())['cases'] if c['year']==2024);binding=json.loads((O/'BINDING.json').read_text());pointer=json.loads((O/'recovery/POINTER.json').read_text());saved=json.loads((O/'ACCOUNT.json').read_text());result=json.loads((O/'RESULT.json').read_text());fingerprint=json.loads((O/'MINUTE_NUMERIC.json').read_text())['columns'];temp=Path(tempfile.mkdtemp(prefix='zero-advance-',dir=R));recover=temp/'recovery';recover.mkdir()
for name in ['POINTER.json',pointer['snapshot_path'],*[r['path'] for r in pointer['chunks']]]:os.link(O/'recovery'/name,recover/name)
source=source_window(case,S,port,W);source['headroom_features']=FeatureTape.load(F,json.loads((B/'features/Y2024.json').read_text()));trace=[];blocked=[];counts={}
def observe(frame,event,arg):
 if event!='call':return
 name=frame.f_code.co_name;path=frame.f_code.co_filename
 if str(W) not in path and str(B) not in path:return
 if name in ('advance_day','attempt','schedule','terminal','book_fill','apply_funding','receive_funding','apply_liquidation'):
  blocked.append(dict(function=name,path=path));raise RuntimeError('Forbidden financial transition during zero-advance recovery: '+name)
 if name in ('from_snapshot','verified_freeze','snapshot','state_hash','result','__init__'):
  key=path+':'+name;counts[key]=counts.get(key,0)+1
  if name in ('from_snapshot','verified_freeze'):trace.append(dict(function=name,path=str(Path(path).relative_to(B)),line=frame.f_code.co_firstlineno))
try:
 sys.setprofile(observe)
 snapshot,restored_pointer=port.restore_snapshot(recover,binding)
 sim=HeadroomFullExitSimulator.from_snapshot(snapshot,source,account_class=FineGridAccount)
 assert sim.state_hash()==pointer['state_hash']==result['genuine_state_hash']
 assert sim.cursor==pointer['cursor'] and sim.stop==pointer['stop'] and sim.rows_written==pointer['completed_minutes']
 view=copy.copy(sim);view.minute_chunks=[];image=view.snapshot();original=copy.copy(snapshot);original['minute_chunks']=[];assert image==original,'Full nonnumeric state, exact Decimal account, targets, pending/budget, protective locks/coverage differ'
 output=sim.result()
 assert output['summary']==saved['summary'] and output['protective_policy']==saved['protective_policy']==result['protective_policy']
 for k in ('trades','funding','rejections','breaches','extrema','target_meta'):assert output[k]==saved[k],k
 assert output['targets'].to_dicts()==saved['targets']
 assert port.fingerprint(output['minute'])==fingerprint
 assert sim.state_hash()==pointer['state_hash'],'Readonly result mutated transition state'
 _,inventory=port.native.episodes(output['trades'],tuple(source['symbols']));bridge=port.native.nav_bridge(output['trades'],output['funding'],inventory,output['summary']['terminal_mark_prices'],sim.account.nav());assert bridge==result['independent_decimal_NAV_bridge']
 assert not blocked
 sys.setprofile(None)
 locks=image['state']['protective_locks'];pending=image['state']['pending']
 receipt=dict(status='PASS_ORIGINAL_COMPLETE_CHECKPOINT_ZERO_ADVANCE',case=result['case_id'],state_hash=pointer['state_hash'],checkpoint_sha256=pointer['snapshot_SHA256'],all_day_chunks_verified=len(pointer['chunks']),all_numeric_rows_verified=sim.rows_written,all_numeric_columns_verified=len(fingerprint),exact_complete_snapshot_equal=True,Decimal_NAV_bridge=bridge,original_recovery_trace=trace,recovery_function_counts={k.replace(str(B)+'/',''):v for k,v in counts.items()},financial_transition_calls=blocked,historical_minutes_advanced=0,new_economic_wallets=0,recovery_object_allocations='Original NativeDailySimulator.from_snapshot invokes cls constructor for temporary recovery allocation, then original validated account_class.from_snapshot replaces it with exact saved financial state; no trading/advance or new economic case.',target_rows_equal=True,funding_journal_equal=True,same_minute_capacity_budget_equal=True,protective_locks_equal=True,persistent_pending_equal=True,final_lock_count=len(locks),final_pending_count=len(pending),lock_path_scope='Original GUARD50.from_snapshot identity/schema/persistent-exit validation path executed. Final and all 30-day checkpoints have empty locks/pending. No claim of real nonempty persistent-lock cold restoration; historical event/fill journals separately prove observed lock lifecycle.',elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,temporary_restore_directory_recorded_locally_only=True)
 args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({k:receipt[k] for k in ('status','all_day_chunks_verified','all_numeric_rows_verified','state_hash','historical_minutes_advanced','new_economic_wallets','elapsed_seconds','peak_RSS_bytes')}))
except BaseException as e:
 sys.setprofile(None);args.output.with_suffix('.failure.json').write_text(json.dumps(dict(error=str(e),traceback=traceback.format_exc(),recovery_trace=trace,blocked_calls=blocked,historical_minutes_advanced=0,new_economic_wallets=0),indent=2)+'\n');raise

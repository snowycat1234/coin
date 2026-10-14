"""Matched-wallet preparation; financial imports only after identity checks.
This release has no admitted target packet and cannot launch historical cases.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util,sys,os
import inherited_input_binding as inputs
HERE=Path(__file__).resolve().parent
S=inputs.S;MINUTE=60000000;DAY=86400000000
class GateError(ValueError):pass
def read(p):return json.loads(Path(p).read_text())
def sha(p):return inputs.sha(p)
def check(p,h):
 p=Path(p)
 if p.is_symlink() or not p.is_file() or sha(p)!=h:raise GateError('EXACT_BYTES_REQUIRED:'+p.name)
def logical(roots,r):
 if r['root'] not in roots:raise GateError('MISSING_LOGICAL_ROOT:'+r['root'])
 return inputs.safe(roots[r['root']],r['path'])
def verify_release(root=HERE):
 root=Path(root);pins=read(root/'PREPARATION_PINS.json')
 for n,h in pins['files_SHA256'].items():check(inputs.safe(root,n),h)
 return pins
def verify_common(roots):
 f=read(HERE/'ORIGINAL_COMMON_FREEZE.json');check(Path(roots['common'])/'FROZEN_CODE.json','c1c50dd484400a175bf28b16ae16a500a5c195f0f88403e5d5dc4d08f275d5e6')
 for n,h in f['files_SHA256'].items():check(inputs.safe(roots['common'],n),h)
 for n,h in f['dependencies_SHA256'].items():check(inputs.safe(roots['workspace'],n),h)
 return {'common_code':len(f['files_SHA256']),'common_dependencies':len(f['dependencies_SHA256'])}
def verify_port_closure(roots,year=2023):
 term=read(HERE/'ORIGINAL_TERMINAL_FREEZE.json');repo=Path(roots['repo']);folder=repo/'research/static50-sma-20261013'
 for filename,count in [('LOCAL_CODE_MANIFEST.json',26),('LOCAL_CODE_MANIFEST_2025.json',28)]:
  name='coin_native_half_mix_20261013/repo/research/static50-sma-20261013/'+filename
  check(folder/filename,term['dependencies_SHA256'][name]);m=read(folder/filename)
  if len(m['sha256'])!=count:raise GateError('PORT_CLOSURE_COUNT')
  for n,h in m['sha256'].items():
   if term['dependencies_SHA256'].get('coin_native_half_mix_20261013/repo/'+n)!=h:raise GateError('PORT_TRANSITIVE_OMISSION')
   check(inputs.safe(repo,n),h)
 return folder/('local_native_apis_2025.py' if year==2025 else 'local_native_apis.py')
def verify_fine(roots):
 fine=Path(roots['workspace'])/'coin_quantity_resolution_20261013';f=read(HERE/'ORIGINAL_FINE_FREEZE.json');t=read(HERE/'ORIGINAL_TERMINAL_FREEZE.json')
 check(fine/'FROZEN_CODE.json',sha(HERE/'ORIGINAL_FINE_FREEZE.json'))
 expected={'fine_account.py','run_cases.py','preflight.py','PROTOCOL.md','FINE_PROFILE.json','CASE_BINDINGS.json','test_pure.py'}
 if set(f['files_SHA256'])!=expected:raise GateError('ORIGINAL_FINE_REGISTRY_KEYS')
 for n,h in f['files_SHA256'].items():check(fine/n,h)
 check(fine/'freeze_bootstrap.py',t['dependencies_SHA256']['coin_quantity_resolution_20261013/freeze_bootstrap.py']);check(fine/'REVIEW_RECEIPT.json',t['dependencies_SHA256']['coin_quantity_resolution_20261013/REVIEW_RECEIPT.json'])
 receipt=read(fine/'REVIEW_RECEIPT.json')
 if receipt['freeze_manifest_SHA256']!=sha(fine/'FROZEN_CODE.json') or receipt['bootstrap_SHA256']!=sha(fine/'freeze_bootstrap.py') or receipt['status']!='REVIEW_ONLY_NO_FINE_HISTORICAL_WALLET':raise GateError('ORIGINAL_FINE_REVIEW')
 profile=read(fine/'FINE_PROFILE.json')
 if tuple(profile['symbols'])!=S or profile['quantity_step_base_asset']!='0.00000001' or profile['opening_min_notional_USDT']!='10' or profile['closing_min_notional_exempt'] is not True:raise GateError('ORIGINAL_FINE_SYMBOL_PROFILE')
 return fine

def verify_complete_identity(roots):
 verify_release();common=verify_common(roots);verify_fine(roots);verify_port_closure(roots)
 b=read(HERE/'TRANSITIVE_BINDINGS.json');t=read(HERE/'ORIGINAL_TERMINAL_FREEZE.json')
 unresolved=[]
 for n,h in t['dependencies_SHA256'].items():
  r=b['dependencies'].get(n)
  if r is None:
   # Missing original evidence remains a mandatory, explicitly supplied root.
   p=inputs.safe(roots.get('restored','/NONEXISTENT'),n)
   try:check(p,h)
   except GateError:unresolved.append({'name':n,'SHA256':h})
  else:
   if r['SHA256']!=h:raise GateError('FROZEN_DEPENDENCY_MAPPING_CHANGED')
   check(logical(roots,r),h)
 terminal=Path(roots['terminal']);check(terminal/'FROZEN_CODE.json',sha(HERE/'ORIGINAL_TERMINAL_FREEZE.json'));check(terminal/'freeze_terminal.py',t['bootstrap_SHA256'])
 for n,h in t['files_SHA256'].items():check(inputs.safe(terminal,n),h)
 receipt=read(terminal/'REVIEW_RECEIPT.json')
 if receipt.get('status')!='PASS_INDEPENDENT_PRE_GO_REVIEW' or receipt.get('new_historical_wallets_executed')!=0 or receipt.get('freeze_manifest_SHA256')!=sha(terminal/'FROZEN_CODE.json') or receipt.get('bootstrap_SHA256')!=sha(terminal/'freeze_terminal.py'):raise GateError('ORIGINAL_TERMINAL_REVIEW')
 if unresolved:raise GateError('MISSING_FROZEN_DEPENDENCIES:'+json.dumps(unresolved,sort_keys=True))
 check(Path(roots['common'])/'inputs/2024_DERIVED_MARK_OHLC.csv','0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c')
 return {'status':'PASS_FULL_TRANSITIVE_IDENTITY',**common,'terminal_dependencies':len(t['dependencies_SHA256'])}

def normalize_daily(records):
 import polars as pl
 frame=pl.DataFrame(records)
 if set(frame.columns)!={'symbol','close_us','close'}:raise GateError('DAILY_SCHEMA')
 if frame['symbol'].null_count() or frame['close_us'].null_count() or frame['close'].null_count():raise GateError('DAILY_NULL')
 if frame.schema['symbol']!=pl.String or frame.schema['close_us']!=pl.Int64 or frame.schema['close']!=pl.Float64:raise GateError('DAILY_DTYPES')
 if frame.select(pl.struct(['symbol','close_us']).is_duplicated().any()).item():raise GateError('DUPLICATE_DAILY_CLOCK')
 return frame

def source_window(year,source_root):
 if year==2021:raise GateError('2021_SKIPPED_EXACT_TARGET_IDENTITY_PROOF_BLOCKER_RETAINED')
 w=inputs.source_window(year,source_root);w['daily']=normalize_daily(w['daily']);return w

def validate_saved_arrays(arrays,year,expected_array_hashes=None):
 import numpy as np
 required={'decision_us','symbol_order','PRICE_ONLY_CSH','FUNDING_ADJUSTED_CSH','annual_covariance','original_daily_admission','required_source_not_ready','owning_rank_us','owning_rank_source_known'}
 if set(arrays)!=required:raise GateError('TARGET_SCHEMA_EXACT_NINE_FIELDS')
 start,end=inputs.registry()['years'][str(year)]['calendar'];n=(end-start)//DAY
 shapes={'decision_us':(n,),'symbol_order':(5,),'PRICE_ONLY_CSH':(n,5),'FUNDING_ADJUSTED_CSH':(n,5),'annual_covariance':(n,5,5),'original_daily_admission':(n,),'required_source_not_ready':(n,),'owning_rank_us':(n,),'owning_rank_source_known':(n,)}
 dtypes={'decision_us':'int64','symbol_order':'<U8','PRICE_ONLY_CSH':'float64','FUNDING_ADJUSTED_CSH':'float64','annual_covariance':'float64','original_daily_admission':'bool','required_source_not_ready':'bool','owning_rank_us':'int64','owning_rank_source_known':'bool'}
 for k in required:
  x=np.asarray(arrays[k])
  if x.shape!=shapes[k] or x.dtype!=np.dtype(dtypes[k]):raise GateError('TARGET_SCHEMA:'+k)
  if expected_array_hashes and hashlib.sha256(x.tobytes()).hexdigest()!=expected_array_hashes[k]:raise GateError('EXACT_TARGET_ARRAY_HASH:'+k)
 if not np.array_equal(arrays['decision_us'],np.arange(start,end,DAY,dtype=np.int64)):raise GateError('TARGET_CLOCKS')
 if tuple(arrays['symbol_order'])!=S:raise GateError('TARGET_SYMBOL_ORDER')
 inactive=~arrays['original_daily_admission'] | arrays['required_source_not_ready']
 for k in ('PRICE_ONLY_CSH','FUNDING_ADJUSTED_CSH'):
  w=arrays[k]
  if not np.isfinite(w).all() or np.any(np.abs(w)>.3+1e-12) or np.any(np.abs(w).sum(axis=1)>.6+1e-12):raise GateError('ORIGINAL_TARGET_CAPS')
  if np.any(w[inactive]!=0):raise GateError('AUTHORITATIVE_ADMISSION_READINESS_CASH')
  w.flags.writeable=False
 for x in arrays.values():x.flags.writeable=False
 return {'control':arrays['PRICE_ONLY_CSH'],'candidate':arrays['FUNDING_ADJUSTED_CSH'],'raw_arrays':arrays}

def bind_targets(year,target_root):
 binding=read(HERE/'TARGET_REMOTE_BINDING.json');root=Path(target_root)
 for name in ('OUTPUT_MANIFEST.json','OUTPUT_REVIEW_RECEIPT.json',f'Y{year}_TARGETS.npz'):
  rec=binding['files'][name];inputs.check_file(root,name,{'SHA256':rec['SHA256'],'bytes':rec['bytes']})
 manifest=read(root/'OUTPUT_MANIFEST.json');review=read(root/'OUTPUT_REVIEW_RECEIPT.json')
 if review.get('schema')!='EXACT_CSH_TARGET_SAVED_ONLY_INDEPENDENT_REVIEW_V1' or review.get('status')!='PASS_EXACT_CSH_TARGET_SAVED_OUTPUT_NO_ECONOMICS' or review.get('output_manifest_sha256')!=binding['files']['OUTPUT_MANIFEST.json']['SHA256']:raise GateError('SAVED_OUTPUT_REVIEW_CONTRACT')
 rec=manifest['files'][f'Y{year}_TARGETS.npz'];bound=binding['files'][f'Y{year}_TARGETS.npz']
 if rec['sha256']!=bound['SHA256'] or rec['bytes']!=bound['bytes']:raise GateError('OUTPUT_MANIFEST_ARCHIVE_BINDING')
 import numpy as np
 with np.load(root/f'Y{year}_TARGETS.npz',allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
 return validate_saved_arrays(arrays,year,read(HERE/'TARGET_ARRAY_BINDINGS.json')[str(year)])

def target_factory(bound,arm,pl):
 # Only transport immutable exact weights to native rows; no eligibility labels invented.
 if arm not in ('control','candidate'):raise GateError('EXACT_ARM_REQUIRED')
 def factory(daily,clocks,mode):
  import numpy as np
  if mode!='LONG_SHORT' or not np.array_equal(clocks,bound['raw_arrays']['decision_us']):raise GateError('NATIVE_TARGET_CLOCK_MODE')
  w=bound[arm]
  return pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(S)]),{'source':'EXACT_ARCHIVED_READONLY_ARM','arm':arm}
 return factory

def require_economic_review(review_root):
 binding=read(HERE/'TARGET_BINDINGS_PENDING.json')
 if binding['launcher_economic_review_SHA256'] is None:raise GateError('WAITING_LAUNCHER_ECONOMIC_REVIEW / NO_GO')
 p=Path(review_root)/binding['launcher_economic_review_name'];check(p,binding['launcher_economic_review_SHA256']);review=read(p)
 if review.get('status')!='PASS_INDEPENDENT_NATIVE_PAIR_PRE_GO_REVIEW' or review.get('protocol_SHA256')!=sha(HERE/'PROTOCOL.json') or review.get('preparation_pins_SHA256')!=sha(HERE/'PREPARATION_PINS.json') or review.get('target_output_manifest_SHA256')!=read(HERE/'TARGET_REMOTE_BINDING.json')['files']['OUTPUT_MANIFEST.json']['SHA256']:raise GateError('LAUNCHER_ECONOMIC_REVIEW_BINDING')
 return review

def require_parent_go(go,year,arm,completed):
 if not go:raise GateError('EXPLICIT_PARENT_GO_REQUIRED / NO_GO')
 if year not in (2023,2024,2025) or arm not in ('control','candidate'):raise GateError('FIXED_CASE_SET')
 if year!=2023:raise GateError('SEPARATE_LATER_YEAR_PARENT_GO_REQUIRED')
 if arm=='candidate' and '2023_control' not in completed:raise GateError('CONTROL_FIRST_REQUIRED')
 if str(year)+'_'+arm in completed:raise GateError('NO_DUPLICATE_CASE')

def load_synthetic_engine(roots,year=2023):
 """Only used by tiny synthetic fixtures; never opens a real source window."""
 verify_release();verify_common(roots);fine=verify_fine(roots);port_path=verify_port_closure(roots,year)
 repo=Path(roots['repo']);sys.path[:0]=[str(repo),str(repo/'src'),str(fine)];os.environ['QUANT_ROOT']=str(repo);os.environ['QUANT_STATE']=str(roots['workspace']);os.environ['CONFIG_FILE']='/dev/null'
 spec=importlib.util.spec_from_file_location('pair_exact_native_port',port_path);port=importlib.util.module_from_spec(spec);spec.loader.exec_module(port);port.verify()
 import fine_account
 if Path(fine_account.__file__).resolve()!= (fine/'fine_account.py').resolve():raise GateError('FINE_IMPORT_SHADOWING')
 if port.native.COSTS[0]!={'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27} or port.native.UNITS[0]!={'id':'RAW_AS_FRACTION','scale':1.0}:raise GateError('ORIGINAL_COST_FUNDING_REGISTRY')
 if tuple(port.SYMBOLS)!=S or port.native.NativeDailySimulator.__module__!='scripts.investment.resumable_perpetual':raise GateError('NATIVE_SYMBOL_CLASS_IDENTITY')
 import terminal_adapter
 check(Path(terminal_adapter.__file__),'923f23a56a3c9a84de49f2527889f2b4c50ac5ad66ad150416f9ed7c2b7d1280')
 return port,fine_account.FineGridAccount,terminal_adapter.EarlierTerminalSimulator

def classify(summary):
 full=summary['completed_minutes']==summary['required_minutes'];flat=bool(summary['terminal_cash_realized']);halt=summary.get('stop_us') is not None
 return 'PAID_FLAT' if full and flat and not halt else 'HALTED_MARKED' if halt else 'FULL_MARKED_NOT_PAID'
def main():
 p=argparse.ArgumentParser();p.add_argument('--roots',required=True);p.add_argument('--year',type=int,choices=(2023,2024,2025),required=True);p.add_argument('--arm',choices=('control','candidate'),required=True);p.add_argument('--target-root');p.add_argument('--check-only',action='store_true');p.add_argument('--parent-go',action='store_true');a=p.parse_args()
 roots=read(a.roots);status={'historical_wallets':0,'historical_minutes':0,'year':a.year,'arm':a.arm,'targets':'WAITING_TARGET_BINDING / NO_GO'}
 try:status['identity']=verify_complete_identity(roots)
 except Exception as e:status['identity']='BLOCKED:'+str(e)
 try:status['source']=inputs.verify_source(a.year,roots['source'+str(a.year)])
 except Exception as e:status['source']='BLOCKED:'+str(e)
 try:
  bind_targets(a.year,a.target_root or roots.get('targets'));status['targets']='PASS_EXACT_SAVED_OUTPUT_READONLY_NINE_FIELDS'
 except Exception as e:status['targets']=str(e)
 try:require_economic_review(None)
 except Exception as e:status['economic_review']=str(e)
 status['launch']='NO_GO';print(json.dumps(status,sort_keys=True))
 # A parent-go flag cannot supply missing finalized packet/review/release bytes.
 # Actual financial controller implementation must be independently bound at later GO.
 return 3
if __name__=='__main__':raise SystemExit(main())

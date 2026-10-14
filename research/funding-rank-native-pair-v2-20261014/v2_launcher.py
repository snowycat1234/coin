"""V2 direct native paired construction. Independent review and GO precede history.
Only synthetic callers are admitted by this preparation publication.
"""
from pathlib import Path
import argparse,hashlib,json,sys,os,importlib.util
import inherited_input_binding as inp
HERE=Path(__file__).resolve().parent;S=inp.S;DAY=86400000000;M=60000000
class GateError(ValueError):pass
def read(p):return json.loads(Path(p).read_text())
def sha(p):return inp.sha(p)
def check(p,h):
 p=Path(p)
 if p.is_symlink() or not p.is_file() or sha(p)!=h:raise GateError('EXACT_BYTES_REQUIRED:'+p.name)
def verify_publication_files():
 freeze=read(HERE/'V2_FREEZE.json')
 for n,h in freeze['files_SHA256'].items():check(inp.safe(HERE,n),h)
 return freeze

def verify_financial(roots):
 verify_publication_files();closure=read(HERE/'EXECUTABLE_CLOSURE.json');repo=Path(roots['repo']);fine=Path(roots['fine'])
 for n,r in closure['repo_files'].items():inp.check_file(repo,n,r)
 manifest=closure['financial_port_manifest'];check(repo/manifest['path'],manifest['SHA256']);port=read(repo/manifest['path'])
 if len(port['sha256'])!=26 or set(port['sha256'])!=set(closure['repo_files']):raise GateError('ORIGINAL26_PORT_CLOSURE')
 for n,h in port['sha256'].items():
  if closure['repo_files'][n]['SHA256']!=h:raise GateError('PORT_REGISTRY_CLOSURE_OMISSION')
 for n,r in closure['fine_files'].items():inp.check_file(fine,n,r)
 f=read(fine/'FROZEN_CODE.json');r=read(fine/'REVIEW_RECEIPT.json')
 required={'CASE_BINDINGS.json','FINE_PROFILE.json','PROTOCOL.md','fine_account.py','preflight.py','run_cases.py','test_pure.py'}
 if set(f['files_SHA256'])!=required or f['status']!='REVIEWED_CODE_AND_INPUT_BINDING_PRE_GO':raise GateError('ORIGINAL_FINE_7_GUARD')
 if r['status']!='REVIEW_ONLY_NO_FINE_HISTORICAL_WALLET' or r['new_fine_wallets_executed']!=0 or r['freeze_manifest_SHA256']!=sha(fine/'FROZEN_CODE.json') or r['bootstrap_SHA256']!=sha(fine/'freeze_bootstrap.py'):raise GateError('ORIGINAL_FINE_REVIEW_BOOTSTRAP')
 profile=read(fine/'FINE_PROFILE.json')
 if tuple(profile['symbols'])!=S or profile['quantity_step_base_asset']!='0.00000001' or profile['opening_min_notional_USDT']!='10' or profile['closing_min_notional_exempt'] is not True:raise GateError('FINE_SYMBOL_PROFILE')
 check(HERE/'terminal_adapter.py',closure['terminal_adapter_SHA256'])
 if 'resource_only_guard' in closure:
  r=closure['resource_only_guard'];check(Path(roots['workspace'])/r['path'],r['SHA256'])
 return {'original_port_files':26,'fine_guard_files':7,'fine_freeze_bootstrap_review':3,'status':'PASS_V2_FINANCIAL_CLOSURE_ONLY_NOT_V1_DIAGNOSIS'}

def verify_imported_financial(roots,port):
 """Bind actual file-backed runtime imports, including cached modules, before accounts."""
 closure=read(HERE/'EXECUTABLE_CLOSURE.json');repo=Path(roots['repo']);fine=Path(roots['fine'])
 def module_identity(module,path,expected):
  filename=getattr(module,'__file__',None);spec=getattr(module,'__spec__',None);origin=getattr(spec,'origin',None)
  if filename is None or origin is None or Path(filename).resolve()!=path.resolve() or Path(origin).resolve()!=path.resolve():raise GateError('FINANCIAL_IMPORT_SHADOW:'+str(path.name))
  check(Path(filename),expected)
 for n,r in closure['repo_files'].items():
  # public_sma_perpetual is the unchanged original port's intentional in-memory stub.
  if n=='scripts/investment/public_sma_perpetual.py':continue
  if n.startswith('src/quant/') and n.endswith('.py'):name=n[4:-3].replace('/','.')
  elif n.startswith('scripts/') and n.endswith('.py'):name=n[:-3].replace('/','.')
  else:continue
  module_identity(sys.modules.get(name),repo/n,r['SHA256'])
 for name in ('fine_account','freeze_bootstrap'):module_identity(sys.modules.get(name),fine/(name+'.py'),closure['fine_files'][name+'.py']['SHA256'])
 for module,n in ((port,'research/static50-sma-20261013/local_native_apis.py'),(port.grid,'research/quantity-grid-sensitivity-20261012/grid_account.py'),(port.state_io,'research/cs-continuous-economics-20261012/state_io.py'),(port.activity,'research/short-native-activity-20261012/activity.py')):module_identity(module,repo/n,closure['repo_files'][n]['SHA256'])
 module_identity(sys.modules.get('terminal_adapter'),HERE/'terminal_adapter.py',closure['terminal_adapter_SHA256'])

def load_engine(roots):
 verify_financial(roots);repo=Path(roots['repo']);fine=Path(roots['fine']);sys.path[:0]=[str(repo),str(repo/'src'),str(fine)]
 os.environ['QUANT_ROOT']=str(repo);os.environ['QUANT_STATE']=str(roots.get('workspace',fine.parent));os.environ['CONFIG_FILE']='/dev/null'
 path=repo/'research/static50-sma-20261013/local_native_apis.py';spec=importlib.util.spec_from_file_location('v2_original_direct_port',path);port=importlib.util.module_from_spec(spec);spec.loader.exec_module(port);port.verify()
 import fine_account,terminal_adapter
 if Path(fine_account.__file__).resolve()!= (fine/'fine_account.py').resolve() or Path(terminal_adapter.__file__).resolve()!=HERE/'terminal_adapter.py':raise GateError('FINANCIAL_IMPORT_SHADOW')
 if tuple(port.SYMBOLS)!=S or port.native.NativeDailySimulator.__module__!='scripts.investment.resumable_perpetual':raise GateError('NATIVE_CLASS_SYMBOL_IDENTITY')
 if port.native.COSTS[0]!={'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27} or port.native.UNITS[0]!={'id':'RAW_AS_FRACTION','scale':1.0}:raise GateError('COST_FUNDING_REGISTRY')
 verify_imported_financial(roots,port)
 return port,fine_account.FineGridAccount,terminal_adapter.EarlierTerminalSimulator

def daily_frame(records):
 import polars as pl
 f=records if isinstance(records,pl.DataFrame) else pl.DataFrame(records)
 if set(f.columns)!={'symbol','close_us','close'} or f.schema['symbol']!=pl.String or f.schema['close_us']!=pl.Int64 or f.schema['close']!=pl.Float64:raise GateError('DAILY_POLARS_SCHEMA')
 if any(f[k].null_count() for k in f.columns) or f.select(pl.struct(['symbol','close_us']).is_duplicated().any()).item():raise GateError('DAILY_NULL_DUPLICATE')
 if not f['close'].is_finite().all() or (f['close']<=0).any():raise GateError('DAILY_PRICE')
 return f

def validate_raw(arrays,clocks,hashes=None):
 import numpy as np
 required={'decision_us','symbol_order','PRICE_ONLY_CSH','FUNDING_ADJUSTED_CSH','annual_covariance','original_daily_admission','required_source_not_ready','owning_rank_us','owning_rank_source_known'}
 if set(arrays)!=required:raise GateError('EXACT9_FIELDS')
 n=len(clocks);shapes={'decision_us':(n,),'symbol_order':(5,),'PRICE_ONLY_CSH':(n,5),'FUNDING_ADJUSTED_CSH':(n,5),'annual_covariance':(n,5,5),'original_daily_admission':(n,),'required_source_not_ready':(n,),'owning_rank_us':(n,),'owning_rank_source_known':(n,)}
 types={'decision_us':'int64','symbol_order':'<U8','PRICE_ONLY_CSH':'float64','FUNDING_ADJUSTED_CSH':'float64','annual_covariance':'float64','original_daily_admission':'bool','required_source_not_ready':'bool','owning_rank_us':'int64','owning_rank_source_known':'bool'}
 for k in required:
  a=arrays[k]
  if a.shape!=shapes[k] or a.dtype!=np.dtype(types[k]):raise GateError('RAW_SCHEMA:'+k)
  if hashes is not None and hashlib.sha256(a.tobytes()).hexdigest()!=hashes[k]:raise GateError('RAW_HASH:'+k)
 if not np.array_equal(arrays['decision_us'],clocks) or tuple(arrays['symbol_order'])!=S:raise GateError('CLOCK_SYMBOL_ORDER')
 inactive=~arrays['original_daily_admission'] | arrays['required_source_not_ready']
 if np.any(arrays['original_daily_admission'] & ~arrays['owning_rank_source_known']):raise GateError('ADMITTED_UNKNOWN_OWNER')
 for k in ('PRICE_ONLY_CSH','FUNDING_ADJUSTED_CSH'):
  a=arrays[k]
  if not np.isfinite(a).all() or np.any(np.abs(a)>.3+1e-12) or np.any(np.abs(a).sum(axis=1)>.6+1e-12):raise GateError('RAW_FINITE_ASSET_GROSS_CAPS')
  if np.any(a[inactive]!=0):raise GateError('ADMISSION_READINESS_MASK')
 for a in arrays.values():a.flags.writeable=False
 return {'control':arrays['PRICE_ONLY_CSH'],'candidate':arrays['FUNDING_ADJUSTED_CSH'],'raw_arrays':arrays}

def bind_saved_targets(year,target_root):
 import numpy as np
 if year not in (2023,2024,2025):raise GateError('2021_SKIP_AND_PROOF_BLOCK_RETAINED')
 root=Path(target_root);b=read(HERE/'TARGET_REMOTE_BINDING.json')
 for n in ('OUTPUT_MANIFEST.json','OUTPUT_REVIEW_RECEIPT.json',f'Y{year}_TARGETS.npz'):inp.check_file(root,n,b['files'][n])
 review=read(root/'OUTPUT_REVIEW_RECEIPT.json');manifest=read(root/'OUTPUT_MANIFEST.json')
 if review['schema']!='EXACT_CSH_TARGET_SAVED_ONLY_INDEPENDENT_REVIEW_V1' or review['status']!='PASS_EXACT_CSH_TARGET_SAVED_OUTPUT_NO_ECONOMICS' or review['output_manifest_sha256']!=b['files']['OUTPUT_MANIFEST.json']['SHA256']:raise GateError('SAVED_ONLY_REVIEW')
 r=manifest['files'][f'Y{year}_TARGETS.npz'];expected=b['files'][f'Y{year}_TARGETS.npz']
 if r['sha256']!=expected['SHA256'] or r['bytes']!=expected['bytes']:raise GateError('TARGET_MANIFEST_BINDING')
 with np.load(root/f'Y{year}_TARGETS.npz',allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
 start,end=inp.registry()['years'][str(year)]['calendar'];return validate_raw(arrays,np.arange(start,end,DAY,dtype=np.int64),read(HERE/'TARGET_ARRAY_BINDINGS.json')[str(year)])

def source_window(year,root,derived_csv=None):
 if year==2021:raise GateError('2021_TARGET_IDENTITY_SKIP_ORIGINAL_PROOF_BLOCK_UNCHANGED')
 w=inp.source_window(year,root);w['daily']=daily_frame(w['daily'])
 if year==2024:
  if derived_csv is None:raise GateError('ORIGINAL10_DERIVED_PROVENANCE_REQUIRED')
  check(derived_csv,'0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c')
  import csv
  with Path(derived_csv).open() as f:rows=list(csv.DictReader(f))
  if len(rows)!=10 or {(r['symbol'],int(r['open_time_ms'])) for r in rows}!={(s,t) for s in S for t in (1723456920000,1723456980000)} or any(r['source_missing']!='True' for r in rows):raise GateError('ORIGINAL_DERIVED_COORDINATES')
 return w

def validate_target_frame(frame,clocks,bound,arm):
 """Must run inside native target_factory, before native account_for_cost."""
 import numpy as np,polars as pl
 if arm not in ('control','candidate') or not isinstance(frame,pl.DataFrame):raise GateError('EXPLICIT_ARM_POLARS_TARGET')
 if frame.columns!=['available_us','symbol','target_weight'] or frame.schema!={'available_us':pl.Int64,'symbol':pl.String,'target_weight':pl.Float64}:raise GateError('FACTORY_SCHEMA')
 n=len(clocks)
 if frame.height!=n*5 or any(frame[k].null_count() for k in frame.columns):raise GateError('FACTORY_COMPLETE_ROWS')
 if not np.array_equal(frame['available_us'].to_numpy(),np.repeat(clocks,5)) or frame['symbol'].to_list()!=list(S)*n:raise GateError('FACTORY_CLOCK_ORDER')
 w=frame['target_weight'].to_numpy().reshape(n,5)
 if not np.isfinite(w).all() or np.any(np.abs(w)>.3+1e-12) or np.any(np.abs(w).sum(axis=1)>.6+1e-12):raise GateError('FACTORY_FINITE_ASSET_GROSS_CAPS')
 raw=bound['raw_arrays']
 if not np.array_equal(raw['decision_us'],clocks) or tuple(raw['symbol_order'])!=S:raise GateError('FACTORY_RAW_CLOCK_ORDER')
 if np.any(w[~raw['original_daily_admission']|raw['required_source_not_ready']]!=0):raise GateError('FACTORY_AUTHORITATIVE_MASK')
 if not np.array_equal(w,bound[arm]) or w.tobytes()!=bound[arm].tobytes():raise GateError('FACTORY_EXACT_ARM_BYTES')
 return frame

def exact_factory(bound,arm,pl):
 def factory(daily,clocks,mode):
  if mode!='LONG_SHORT':raise GateError('EXACT_NATIVE_MODE')
  w=bound[arm];frame=pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(S)])
  return validate_target_frame(frame,clocks,bound,arm),{'source':'EXACT_READONLY_SAVED_ARM','arm':arm}
 return factory

def require_review(review=None,expected_sha=None,publication_commit=None):
 if review is None or expected_sha is None or publication_commit is None:raise GateError('WAITING_INDEPENDENT_V2_PUBLICATION_REVIEW / NO_GO')
 check(review,expected_sha);r=read(review)
 if r.get('schema')!='INDEPENDENT_V2_NATIVE_PAIR_PUBLICATION_REVIEW_V1' or r.get('status')!='PASS_EXACT_V2_PREPARATION_NO_HISTORY' or r.get('publication_commit')!=publication_commit or r.get('V2_FREEZE_SHA256')!=sha(HERE/'V2_FREEZE.json') or r.get('economic_protocol_SHA256')!=sha(HERE/'PROTOCOL.json') or r.get('code_dependency_closure_SHA256')!=sha(HERE/'EXECUTABLE_CLOSURE.json') or r.get('source_binding_SHA256')!=sha(HERE/'INPUT_BINDINGS.json') or r.get('target_output_manifest_SHA256')!=read(HERE/'TARGET_REMOTE_BINDING.json')['files']['OUTPUT_MANIFEST.json']['SHA256'] or r.get('synthetic_parity_review')!='PASS':raise GateError('V2_REVIEW_TAMPER_OR_SCOPE')
 return r

def require_parent_go(go,year,arm,completed=()):
 if not go:raise GateError('PARENT_GO_REQUIRED_PRE_ACCOUNT / NO_GO')
 if year!=2023:raise GateError('SEPARATE_LATER_YEAR_GO_REQUIRED')
 if arm not in ('control','candidate'):raise GateError('FIXED_ARM')
 if arm=='candidate' and '2023_control' not in completed:raise GateError('CONTROL_FIRST')
 if f'{year}_{arm}' in completed:raise GateError('NO_REPEAT')

def history_admission(roots,year,arm,*,review=None,review_sha=None,publication_commit=None,parent_go=False,completed=()):
 # No financial account is constructed by admission. Fresh resources checked later by authorized controller.
 verify_financial(roots);require_review(review,review_sha,publication_commit);require_parent_go(parent_go,year,arm,completed)
 bound=bind_saved_targets(year,roots['targets']);w=source_window(year,roots['source'+str(year)],roots.get('derived_csv'))
 return w,bound

def construct_synthetic(roots,window,bound,arm):
 # Narrow fixture admission cannot accept an actual historical source window.
 if window.get('fixture_identity')!='PURE_SYNTHETIC_CONSTANT_QUOTES' or window['start']!=0 or window['end'] not in (DAY,2*DAY) or 'minute_blocks' in window:raise GateError('SYNTHETIC_ONLY_NO_HISTORY')
 port,account,sim=load_engine(roots);w=dict(window);w.pop('fixture_identity');w['daily']=daily_frame(w['daily'])
 return sim(w,'LONG_SHORT',port.native.COSTS[0],port.native.UNITS[0],target_factory=exact_factory(bound,arm,port.native.pl),account_factory=account)

def main():
 p=argparse.ArgumentParser();p.add_argument('--roots',required=True);p.add_argument('--year',type=int,choices=(2023,2024,2025),required=True);p.add_argument('--arm',choices=('control','candidate'),required=True);p.add_argument('--check-only',action='store_true',required=True);a=p.parse_args();roots=read(a.roots)
 report={'wallets':0,'historical_minutes':0,'historical_status':'NO_GO','V1':'UNCHANGED_BLOCKED_DIAGNOSIS'}
 for n,fn in [('financial',lambda:verify_financial(roots)),('targets',lambda:bind_saved_targets(a.year,roots['targets'])),('source',lambda:source_window(a.year,roots['source'+str(a.year)],roots.get('derived_csv'))),('review',require_review)]:
  try:fn();report[n]='PASS'
  except Exception as e:report[n]=str(e)
 print(json.dumps(report,sort_keys=True));return 3
if __name__=='__main__':raise SystemExit(main())

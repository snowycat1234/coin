"""Portable synthetic-only code binding. The original historical gate is refused.

This gate neither opens nor hashes any target/source market array. It verifies a
separate code carrier, then imports the unchanged original financial bodies.
The earlier c249 gate hashed historical target files; that receipt is not this
gate's receipt and the original 26-file historical closure is never asserted.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, sys
from importlib.machinery import PathFinder
sys.dont_write_bytecode=True

HERE=Path(__file__).resolve().parent
CARRIER=HERE/'dependency_carrier'
REPO=CARRIER/'repo'; FINE=CARRIER/'fine'; TERMINAL=CARRIER/'terminal'
HELPER=CARRIER/'helper'; ORIGINALS=CARRIER/'original_csh'
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MANIFEST_SHA256='72bac79b961a9572748114b740d0a63f0ddf7ba6b0f434325551c95546f6af65'

class GateError(ValueError): pass

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe(relative):
 p=Path(relative)
 if p.is_absolute() or '..' in p.parts: raise GateError('RELATIVE_CARRIER_PATH_REQUIRED')
 path=HERE/p
 if any(x.is_symlink() for x in [path,*path.parents] if x!=HERE.parent):
  raise GateError('SYMLINK_CARRIER_REFUSED')
 if not path.is_file() or not path.resolve().is_relative_to(HERE):
  raise GateError('MISSING_OR_ESCAPING_CODE_CARRIER:'+str(p))
 return path

def verify_code_only():
 if any(p.name=='__pycache__' or p.suffix=='.pyc' for p in HERE.rglob('*')):
  raise GateError('UNBOUND_BYTECODE_CACHE_REFUSED')
 manifest_path=HERE/'CODE_ONLY_CARRIER.json'
 if sha(manifest_path)!=MANIFEST_SHA256: raise GateError('CODE_CARRIER_MANIFEST_PIN')
 manifest=json.loads(manifest_path.read_text())
 if manifest['schema']!='SYNTHETIC_ONLY_CODE_CARRIER_V1': raise GateError('CODE_ONLY_SCHEMA')
 for name,r in manifest['files'].items():
  p=safe(name)
  if p.suffix.lower() in ('.npz','.npy','.parquet','.arrow'):
   raise GateError('ARRAYS_NOT_ADMITTED_BY_CODE_GATE')
  if p.stat().st_size!=r['bytes'] or sha(p)!=r['SHA256']:
   raise GateError('EXACT_SOURCE_PIN:'+name)
 return dict(status='PASS_SYNTHETIC_CODE_CARRIER_ONLY',
  code_carrier_manifest_SHA256=MANIFEST_SHA256, files_verified=len(manifest['files']),
  original26_historical_closure_verified=False, historical_admission='REFUSED',
  historical_target_artifacts_opened=0, historical_target_artifacts_hashed=0)

def configure_runtime(sites=None):
 if sites is None:
  try: sites=json.loads(os.environ.get('BOT_NATIVE_RUNTIME_SITES','null'))
  except Exception as e: raise GateError('EXPLICIT_RUNTIME_SITES_JSON_REQUIRED') from e
 if not isinstance(sites,list) or not sites or any(type(x) is not str for x in sites):
  raise GateError('EXPLICIT_CONSUMER_LOCAL_RUNTIME_SITES_REQUIRED')
 paths=[Path(x).resolve() for x in sites]
 if len(set(paths))!=len(paths) or any(not p.is_dir() for p in paths):
  raise GateError('RUNTIME_SITE_DIRECTORY_REQUIRED')
 if os.environ.get('PYTHONOPTIMIZE') or not __debug__:
  raise GateError('ASSERTIONS_MUST_REMAIN_ENABLED')
 sys.path[:0]=[str(p) for p in paths]
 if sys.version_info[:3]!=(3,12,14): raise GateError('EXACT_PYTHON_3_12_14_RUNTIME_REQUIRED')
 manifest=json.loads((HERE/'CODE_ONLY_CARRIER.json').read_text())
 identities={}
 for name in ('numpy','polars','pyarrow'):
  expected=PathFinder.find_spec(name,[str(p) for p in paths])
  if expected is None or expected.origin is None:
   raise GateError('RUNTIME_PACKAGE_NOT_IN_DECLARED_SITES:'+name)
  module=__import__(name);file=getattr(module,'__file__',None)
  origin=getattr(getattr(module,'__spec__',None),'origin',None)
  if file is None or origin is None or Path(file).resolve()!=Path(origin).resolve():
   raise GateError('RUNTIME_FILE_IDENTITY:'+name)
  path=Path(file).resolve()
  if path!=Path(expected.origin).resolve():
   raise GateError('RUNTIME_SITE_PRIORITY_OR_CACHED_SHADOW:'+name)
  if not any(path.is_relative_to(p) for p in paths):
   raise GateError('RUNTIME_OUTSIDE_DECLARED_SITES:'+name)
  if module.__version__!=manifest['runtime'][name]: raise GateError('RUNTIME_VERSION:'+name)
  identities[name]={'version':module.__version__,'file':str(path),'file_SHA256':sha(path)}
 return identities

def exact_import(name,path):
 path=Path(path).resolve()
 if name in sys.modules: raise GateError('PRELOADED_DYNAMIC_MODULE:'+name)
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module
 spec.loader.exec_module(module)
 module_identity(module,path)
 return module

def module_identity(module,path):
 if module is None: raise GateError('MISSING_RUNTIME_MODULE:'+path.name)
 filename=getattr(module,'__file__',None)
 origin=getattr(getattr(module,'__spec__',None),'origin',None)
 if filename is None or origin is None or Path(filename).resolve()!=path.resolve() or Path(origin).resolve()!=path.resolve():
  raise GateError('SOURCE_IMPORT_SHADOW:'+path.name)
 records=json.loads((HERE/'CODE_ONLY_CARRIER.json').read_text())['files']
 record=records[str(path.relative_to(HERE))]
 if sha(path)!=record['SHA256']: raise GateError('RUNTIME_RAW_SOURCE_CHANGED:'+path.name)

def refuse_history(*args,**kwargs):
 raise GateError('SYNTHETIC_ONLY_TRANSPORT_REFUSES_ORIGINAL26_HISTORICAL_ADMISSION')

# Explicit public denial aliases: no alternate target/window check-only path.
verify_financial=history_admission=bind_saved_targets=source_window=refuse_history

_LOADED=None
def load():
 global _LOADED
 verify_code_only();configure_runtime()
 if _LOADED is not None:
  # Cached objects belong to this gate only, with source/runtime rechecks.
  verify_runtime_objects(*_LOADED[:5])
  return _LOADED
 for name in tuple(sys.modules):
  if name=='quant' or name.startswith('quant.') or name=='scripts' or name.startswith('scripts.') or name in ('fine_account','freeze_bootstrap','terminal_adapter','grid_policy','risk_gate'):
   raise GateError('PRELOADED_FINANCIAL_NAMESPACE:'+name)
 sys.path[:0]=[str(REPO),str(REPO/'src'),str(FINE),str(TERMINAL),str(HELPER)]
 os.environ['QUANT_ROOT']=str(REPO);os.environ['QUANT_STATE']=str(HERE/'synthetic_state_never_read')
 os.environ['CONFIG_FILE']='/dev/null'
 port=exact_import('portable_original_direct_port',REPO/'research/static50-sma-20261013/local_native_apis.py')
 # Original locator/closure functions are transport entry points, not finance.
 # Refuse them explicitly instead of weakening their original historical pins.
 port.verify=port.window=port.prepared=refuse_history
 import fine_account,terminal_adapter,grid_policy,risk_gate
 verify_runtime_objects(port,fine_account.FineGridAccount,terminal_adapter.EarlierTerminalSimulator,grid_policy,risk_gate)
 originals=exact_import('portable_original_csh_functions',ORIGINALS/'original_functions.py')
 functions=originals.load_originals()
 _LOADED=port,fine_account.FineGridAccount,terminal_adapter.EarlierTerminalSimulator,grid_policy,risk_gate,functions
 return _LOADED

def verify_runtime_objects(port,account,sim,grid_policy,risk_gate):
 manifest=json.loads((HERE/'CODE_ONLY_CARRIER.json').read_text())
 for name,r in manifest['files'].items():
  path=HERE/name
  if name.startswith('dependency_carrier/repo/src/quant/') and path.suffix=='.py':
   module_identity(sys.modules.get('quant.'+path.stem),path)
  elif name.startswith('dependency_carrier/repo/scripts/') and path.suffix=='.py':
   key='.'.join(path.relative_to(REPO).with_suffix('').parts)
   module_identity(sys.modules.get(key),path)
 for module,path in ((port,REPO/'research/static50-sma-20261013/local_native_apis.py'),
  (port.grid,REPO/'research/quantity-grid-sensitivity-20261012/grid_account.py'),
  (port.state_io,REPO/'research/cs-continuous-economics-20261012/state_io.py'),
  (port.activity,REPO/'research/short-native-activity-20261012/activity.py'),
  (sys.modules.get('fine_account'),FINE/'fine_account.py'),(sys.modules.get('freeze_bootstrap'),FINE/'freeze_bootstrap.py'),
  (sys.modules.get('terminal_adapter'),TERMINAL/'terminal_adapter.py'),(grid_policy,HELPER/'grid_policy.py'),(risk_gate,HELPER/'risk_gate.py')):
  module_identity(module,path)
 if tuple(port.SYMBOLS)!=S or port.native.NativeDailySimulator.__module__!='scripts.investment.resumable_perpetual':
  raise GateError('NATIVE_CLASS_SYMBOL_IDENTITY')
 if port.native.COSTS[0]!={'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27} or port.native.UNITS[0]!={'id':'RAW_AS_FRACTION','scale':1.0}:
  raise GateError('COST_FUNDING_REGISTRY')
 if account is not sys.modules['fine_account'].FineGridAccount or sim is not sys.modules['terminal_adapter'].EarlierTerminalSimulator:
  raise GateError('RETURNED_NATIVE_CLASS_IDENTITY')
 if any(getattr(port,key) is not refuse_history for key in ('verify','window','prepared')):
  raise GateError('HISTORICAL_LOCATOR_REFUSAL_CHANGED')

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--runtime-site',action='append',required=True)
 args=p.parse_args();os.environ['BOT_NATIVE_RUNTIME_SITES']=json.dumps(args.runtime_site)
 report=verify_code_only();report['runtime']=configure_runtime(args.runtime_site)
 load();print(json.dumps(report,indent=2))

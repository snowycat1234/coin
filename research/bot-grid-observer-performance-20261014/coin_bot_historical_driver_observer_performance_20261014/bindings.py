"""Stdlib metadata gates. No historical array or finance import at module load."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
ORIGINAL_NATIVE=ROOT/'coin_bot_native_adapter_synthetic_20261014'
NATIVE=ROOT/'coin_bot_native_adapter_observer_performance_20261014'
LEGACY=ROOT/'native_pair_replacement_review_20261014/loader_identity_patch'
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000;M=60000000
SOURCE_ADAPTER_SHA='65277cc7fc79955792198ceaf1c300a0aac4b7c0ad461ec88d11ae1b320ed5c4'
ADAPTER_SHA='503dcdda95927e612f5c2bb81a900bf7bbb8f65376a66600379d04d5219e2e37'
NATIVE_FREEZE_SHA='c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b'
TRANSPORT_SHA='b9d079718d262bfad9d487a05ba8d80c7b866ee2c823dd7582540b7a69500e58'
SOURCE_PREPARATION_SHA='ec309d829dbf7943875b7256973fe4e46c5427bd23603e345768ff5d70c3ad2d'
DISPATCH_SHA='4be0422b6ff5b552268b824f1a03028a10015a9fa809f45caaaba5fc54827ea8'

def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(p,expected,bytes_=None):
 p=Path(p)
 if p.is_symlink() or not p.is_file() or sha(p)!=expected or bytes_ is not None and p.stat().st_size!=bytes_:
  raise ValueError('EXACT_BYTES_REQUIRED:'+str(p))
 return p

def module(name,p):
 from verified_source import require_runtime
 require_runtime()
 if name in sys.modules:raise ValueError('UNVERIFIED_OR_DUPLICATE_DYNAMIC_MODULE:'+name)
 p=Path(p).resolve();spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
 if Path(m.__file__).resolve()!=p or Path(m.__spec__.origin).resolve()!=p:raise ValueError('MODULE_SHADOW')
 return m

def metadata_manifest():
 from verified_source import require_runtime
 require_runtime()
 if sys.flags.optimize:raise ValueError('ORIGINAL_ASSERTIONS_MUST_REMAIN_ENABLED')
 manifest=read(HERE/'INPUT_MANIFEST.json')
 for record in manifest['metadata_pins']:
  check(ROOT/record['path'],record['SHA256'],record['bytes'])
 return manifest

def load_transport():
 check(LEGACY/'inherited_input_binding.py',TRANSPORT_SHA)
 return module('grid_original_input_transport',LEGACY/'inherited_input_binding.py')

def load_runtime(case_go,case_go_sha,year,arm):
 g=require_go(case_go,case_go_sha,'ONE_FRESH_NATIVE_CASE',year,arm)
 from verified_source import require_runtime
 runtime=require_runtime()
 if runtime.mode!='source_case':raise ValueError('ORIGINAL26_HISTORICAL_RUNTIME_REQUIRED_PORTABLE_REFUSED')
 if not getattr(runtime,'bounded_worker_admitted',False):raise ValueError('BOUNDED_CONTROLLER_HANDOFF_REQUIRED_BEFORE_ORIGINAL_RUNTIME')
 if g.get('original26_hash_only_target_artifacts')!=['Y2023.npz','Y2025.npz']:
  raise ValueError('ORIGINAL26_TWO_ARTIFACT_HASH_ONLY_SCOPE_REQUIRED')
 check(ORIGINAL_NATIVE/'FINAL_MANIFEST.json',NATIVE_FREEZE_SHA);check(ORIGINAL_NATIVE/'native_adapter.py',SOURCE_ADAPTER_SHA);check(NATIVE/'native_adapter.py',ADAPTER_SHA)
 # Original adapter loader verifies all financial source paths/spec origins,
 # original26-file/fine closure and exact helper before returning the engine.
 sys.path.insert(0,str(NATIVE));a=__import__('native_adapter')
 if Path(a.__file__).resolve()!=NATIVE/'native_adapter.py':raise ValueError('ADAPTER_IMPORT_SHADOW')
 import pyarrow
 if sys.version_info[:3]!=(3,12,14) or a.np.__version__!='2.3.5' or a.PORT.native.pl.__version__!='1.44.2' or pyarrow.__version__!='23.0.1':raise ValueError('EXACT_C249_RUNTIME_IDENTITY_REQUIRED')
 runtime.audit()
 return a

def load_controller():
 check(LEGACY/'dispatcher.py',DISPATCH_SHA);sys.path.insert(0,str(LEGACY))
 return module('grid_original_resource_dispatcher',LEGACY/'dispatcher.py')

def require_go(path,expected,action,year,arm=None):
 if action not in ('SOURCE_ONLY_ORIGINAL_PROJECTION','ONE_FRESH_NATIVE_CASE'):raise ValueError('EXACT_ORIGINAL_ACTION_REQUIRED')
 if path is None or expected is None:raise ValueError('SEPARATE_PARENT_GO_REQUIRED_BEFORE_ARRAY_OR_WALLET')
 check(path,expected);g=read(path)
 if (g.get('schema')!='EXPLICIT_ORIGINAL_CSH_GRID_SOURCE_OR_CASE_GO_V1' or g.get('parent_GO') is not True
  or g.get('action')!=action or g.get('year')!=year or year not in (2023,2024,2025)
  or g.get('target_field')!='STATIC50_UNLAGGED' or g.get('rank_feature_lag_hours')!=0
  or g.get('native_adapter_SHA256')!=(SOURCE_ADAPTER_SHA if action=='SOURCE_ONLY_ORIGINAL_PROJECTION' else ADAPTER_SHA) or g.get('input_manifest_SHA256')!=sha(HERE/'INPUT_MANIFEST.json')
  or g.get('preparation_manifest_SHA256')!=(SOURCE_PREPARATION_SHA if action=='SOURCE_ONLY_ORIGINAL_PROJECTION' else sha(HERE/'PREPARATION_MANIFEST.json'))):
  raise ValueError('EXACT_ORIGINAL_CSH_GO_SCOPE_REQUIRED')
 if action=='ONE_FRESH_NATIVE_CASE' and g.get('source_preparation_SHA256')!=SOURCE_PREPARATION_SHA:raise ValueError('EXACT_EC309_SOURCE_LINEAGE_REQUIRED')
 if action=='ONE_FRESH_NATIVE_CASE' and (g.get('arm')!=arm or arm not in ('CSH','CASH','GRID')):
  raise ValueError('EXACT_ONE_CASE_YEAR_ARM_REQUIRED')
 return g

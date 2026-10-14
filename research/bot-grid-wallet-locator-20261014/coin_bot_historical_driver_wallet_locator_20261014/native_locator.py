"""Relocation-only original runtime binding. Full original26 closure is retained."""
from pathlib import Path
import hashlib,importlib.util,json,sys,os
from importlib.machinery import PathFinder
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REVIEW=ROOT/'native_pair_replacement_review_20261014'
LAUNCHER=REVIEW/'loader_identity_patch'
HELPER=ROOT/'coin_bot_risk_matched_synthetic_20261014'
PINS={
 'launcher':('native_pair_replacement_review_20261014/loader_identity_patch/v2_launcher.py','400b689959a219cf9e71987b34d524a37969550e97a6d9802d435e761a77005f'),
 'helper':('coin_bot_risk_matched_synthetic_20261014/grid_policy.py','823382e61ccd3e6ea6b2e2678da70c4c7482ba51b5284178677a3e83ada284b8'),
 'risk_helper':('coin_bot_risk_matched_synthetic_20261014/risk_gate.py','2d3994097e240a2b88778be0374bf91682fc5a0be1dd1e9e8b1b927b1e2ba05d'),
 'original_functions':('coin_funding_target_discriminator_20261014/original2021/original_functions.py','d8f8eff11edb3a770611d6b57eef19f04a2fbd750acd87651c0f0bf053f80ddc'),
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

RUNTIME_VERSIONS={'numpy':'2.3.5','polars':'1.44.2','pyarrow':'23.0.1'}


def relocated_roots():
 base=REVIEW/'synthetic_dependencies_ca11e94d'
 roots={key:base/key for key in ('repo','fine','workspace')}
 for key,path in roots.items():
  if any(p.is_symlink() for p in (path,*path.parents) if p.is_relative_to(ROOT)):
   raise ValueError('SYMLINKED_ORIGINAL_RUNTIME_LOCATOR:'+key)
  if not path.is_dir() or not path.resolve().is_relative_to(ROOT):
   raise ValueError('CONSUMER_RELATIVE_ORIGINAL_RUNTIME_REQUIRED:'+key)
 return {key:str(path.resolve()) for key,path in roots.items()}


def configure_runtime():
 try:sites=json.loads(os.environ.get('BOT_NATIVE_RUNTIME_SITES','null'))
 except Exception as error:raise ValueError('EXPLICIT_RUNTIME_SITES_JSON_REQUIRED') from error
 if not isinstance(sites,list) or not sites or any(type(p) is not str or not Path(p).is_absolute() for p in sites):
  raise ValueError('EXPLICIT_ABSOLUTE_CONSUMER_RUNTIME_SITES_REQUIRED')
 paths=[Path(p).resolve() for p in sites]
 if len(set(paths))!=len(paths) or any(not p.is_dir() for p in paths):raise ValueError('RUNTIME_SITE_DIRECTORY_REQUIRED')
 if sys.version_info[:3]!=(3,12,14) or sys.flags.optimize or os.environ.get('PYTHONOPTIMIZE'):
  raise ValueError('EXACT_ASSERTION_ENABLED_PYTHON_3_12_14_REQUIRED')
 sys.path[:0]=[str(p) for p in paths]
 identities={}
 for name,version in RUNTIME_VERSIONS.items():
  expected=PathFinder.find_spec(name,[str(p) for p in paths])
  if expected is None or expected.origin is None:raise ValueError('RUNTIME_PACKAGE_NOT_IN_DECLARED_SITES:'+name)
  module=__import__(name);filename=getattr(module,'__file__',None);origin=getattr(getattr(module,'__spec__',None),'origin',None)
  if filename is None or origin is None or Path(filename).resolve()!=Path(origin).resolve() or Path(filename).resolve()!=Path(expected.origin).resolve():
   raise ValueError('RUNTIME_SITE_PRIORITY_OR_CACHED_SHADOW:'+name)
  path=Path(filename).resolve()
  if not any(path.is_relative_to(p) for p in paths) or module.__version__!=version:raise ValueError('EXACT_RUNTIME_SITE_VERSION_REQUIRED:'+name)
  identities[name]={'version':version,'package_entry_SHA256':sha(path)}
 return identities


def exact_import(name,path):
 p=Path(path).resolve();spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
 if Path(m.__file__).resolve()!=p or Path(m.__spec__.origin).resolve()!=p:raise ValueError('IMPORT_SHADOW')
 return m


def load():
 from verified_source import require_runtime
 runtime=require_runtime()
 if runtime.mode!='source_case' or not getattr(runtime,'bounded_worker_admitted',False):raise ValueError('BOUNDED_ORIGINAL26_RUNTIME_REQUIRED')
 configure_runtime()
 for key,(name,want) in PINS.items():
  if want and sha(ROOT/name)!=want:raise ValueError('SOURCE_PIN:'+key)
 sys.path[:0]=[str(LAUNCHER),str(HELPER)]
 v=exact_import('bot_native_verified_launcher',LAUNCHER/'v2_launcher.py')
 roots=relocated_roots()
 port,account,sim=v.load_engine(roots)
 helper=__import__('grid_policy');risk=__import__('risk_gate')
 if Path(helper.__file__).resolve()!=HELPER/'grid_policy.py' or Path(risk.__file__).resolve()!=HELPER/'risk_gate.py':raise ValueError('HELPER_SHADOW')
 originals=exact_import('bot_original_csh_functions',ROOT/PINS['original_functions'][0]);functions=originals.load_originals()
 return port,account,sim,helper,risk,functions

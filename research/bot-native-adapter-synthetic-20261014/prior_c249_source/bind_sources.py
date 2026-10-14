"""Exact existing source imports only; no market loader or historical target load."""
from pathlib import Path
import hashlib,importlib.util,json,sys
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

def exact_import(name,path):
 p=Path(path).resolve();spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
 if Path(m.__file__).resolve()!=p or Path(m.__spec__.origin).resolve()!=p:raise ValueError('IMPORT_SHADOW')
 return m


def load():
 for key,(name,want) in PINS.items():
  if want and sha(ROOT/name)!=want:raise ValueError('SOURCE_PIN:'+key)
 sys.path[:0]=[str(REVIEW/'site'),str(ROOT/'coin_funding_rank_dependencies_20261013/site'),str(LAUNCHER),str(HELPER)]
 v=exact_import('bot_native_verified_launcher',LAUNCHER/'v2_launcher.py')
 roots=json.loads((REVIEW/'synthetic_dependencies_ca11e94d/SYNTHETIC_ROOTS.json').read_text())
 port,account,sim=v.load_engine(roots)
 helper=__import__('grid_policy');risk=__import__('risk_gate')
 if Path(helper.__file__).resolve()!=HELPER/'grid_policy.py' or Path(risk.__file__).resolve()!=HELPER/'risk_gate.py':raise ValueError('HELPER_SHADOW')
 originals=exact_import('bot_original_csh_functions',ROOT/PINS['original_functions'][0]);functions=originals.load_originals()
 return port,account,sim,helper,risk,functions

"""Code-only binding with raw-source compilation; bytecode caches are unused."""
from pathlib import Path
import hashlib, importlib.util, importlib.machinery, json, marshal, sys, types
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PORTABLE=ROOT/'coin_bot_native_adapter_portable_synthetic_20261014'
COMMON=ROOT/'native_independent_oracle_publication_20261014/remote_restored/synthetic_dependencies/common'
PROTECTIVE=COMMON/'runtime_dependencies/coin_margin_protective_policy_20261013'
PAIRED=ROOT/'coin_paired_headroom_discriminator_20261014'
EXECUTED_SOURCE={}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def exact(name,path):
    if name in sys.modules:raise ValueError('PRELOADED_MODULE:'+name)
    path=path.resolve();source=path.read_bytes()
    code=compile(source,str(path),'exec',dont_inherit=True,optimize=0)
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    # Deliberately do not call SourceFileLoader.exec_module/get_code, which
    # may select timestamp-valid stale .pyc despite hashing the .py source.
    exec(code,module.__dict__)
    if Path(module.__file__).resolve()!=path or Path(module.__spec__.origin).resolve()!=path:
        raise ValueError('IMPORT_SHADOW:'+name)
    EXECUTED_SOURCE[name]=dict(path=str(path.relative_to(ROOT)),
        raw_source_SHA256=hashlib.sha256(source).hexdigest(),
        executed_code_SHA256=hashlib.sha256(marshal.dumps(code)).hexdigest(),
        mechanism='COMPILE_PINNED_RAW_SOURCE_NO_PYC')
    return module

def load():
    pins=json.loads((HERE/'DEPENDENCY_PINS.json').read_text())
    for name,want in pins['files_SHA256'].items():
        p=ROOT/name
        if any(x.is_symlink() for x in [p,*p.parents] if x!=ROOT.parent) or sha(p)!=want:
            raise ValueError('CODE_PIN:'+name)
    transport=exact('paired_native_code_transport',PORTABLE/'bind_sources.py')
    # The reviewed portable carrier refuses any unbound .pyc/__pycache__ in
    # its entire code closure before its unchanged native financial imports.
    port,account,terminal,_,_,originals=transport.load()
    headroom_buffer=exact('headroom_buffer',COMMON/'headroom_buffer.py')
    feature_tape=exact('feature_tape',COMMON/'feature_tape.py')
    protective_policy=exact('protective_policy',PROTECTIVE/'protective_policy.py')
    headroom_policy=exact('headroom_policy',COMMON/'headroom_policy.py')
    if 'vendor' in sys.modules:raise ValueError('PRELOADED_VENDOR_NAMESPACE')
    vendor=types.ModuleType('vendor');vendor.__path__=[str(PAIRED/'vendor')]
    vendor.__package__='vendor'
    vendor.__spec__=importlib.machinery.ModuleSpec('vendor',loader=None,is_package=True)
    vendor.__spec__.submodule_search_locations=vendor.__path__
    sys.modules['vendor']=vendor
    original=exact('vendor.headroom_buffer',PAIRED/'vendor/headroom_buffer.py')
    paired_buffer=exact('paired_buffer',PAIRED/'paired_buffer.py')
    if paired_buffer.original is not original:raise ValueError('PAIRED_ORIGINAL_SHADOW')
    protective_policy.verified_freeze()
    return port,account,terminal,originals,headroom_buffer,feature_tape,protective_policy,headroom_policy,paired_buffer

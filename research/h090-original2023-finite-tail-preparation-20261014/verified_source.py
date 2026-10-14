"""Exact source loader for bounded original-driver preparation and generated tests.

All project imports compile verified .py bytes. No project .pyc is consumed.
Cached project modules without this runtime's source identity are rejected.
"""
import hashlib,importlib.abc,importlib.machinery,importlib.util,json,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
_ACTIVE=None


def sha(data):return hashlib.sha256(data).hexdigest()


def code_identity(module):
    found={}
    def take(name,value):
        if isinstance(value,types.FunctionType):
            found[name]=(id(value),id(value.__code__),sha(value.__code__.co_code))
        elif isinstance(value,(staticmethod,classmethod)):
            take(name,value.__func__)
        elif isinstance(value,property):
            for role,function in (('get',value.fget),('set',value.fset),('del',value.fdel)):
                if function is not None:take(name+'.'+role,function)
    for name,value in vars(module).items():
        if isinstance(value,types.FunctionType) and value.__module__==module.__name__:
            take(name,value)
        elif isinstance(value,type) and value.__module__==module.__name__:
            for field,member in vars(value).items():take(name+'.'+field,member)
    return found


class VerifiedLoader(importlib.abc.Loader):
    def __init__(self,runtime,name,path):
        self.runtime=runtime;self.name=name;self.path=Path(path).resolve()
    def create_module(self,spec):return None
    def exec_module(self,module):
        data=self.runtime.bytes(self.path)
        # Compile the checked bytes themselves, never a timestamp .pyc cache.
        self.runtime.loading[self.name]=(module,self.path,self)
        try:
            exec(compile(data,str(self.path),'exec'),module.__dict__)
            self.runtime.records[self.name]=(module,self.path,sha(data),code_identity(module),self)
            if self.path.name=='local_native_apis.py' and hasattr(module,'strategy'):
                self.runtime.register_strategy_stub(module)
            if self.runtime.mode=='generated' and self.path.name=='native_adapter.py' and hasattr(module,'PORT'):
                self.runtime.register_portable_refusals(module.PORT)
        finally:
            self.runtime.loading.pop(self.name,None)


class VerifiedFinder(importlib.abc.MetaPathFinder):
    def __init__(self,runtime):self.runtime=runtime
    def find_spec(self,name,path=None,target=None):
        if name in self.runtime.modules:
            filename=self.runtime.modules[name]
            loader=VerifiedLoader(self.runtime,name,filename)
            return self.runtime.original_spec(name,filename,loader=loader,
                submodule_search_locations=[str(filename.parent)] if filename.name=='__init__.py' else None)
        if name in self.runtime.packages:
            spec=importlib.machinery.ModuleSpec(name,None,is_package=True)
            spec.submodule_search_locations=[str(p) for p in self.runtime.packages[name]]
            return spec
        if any(name.startswith(p+'.') for p in self.runtime.packages):
            raise ValueError('UNBOUND_PROJECT_MODULE:'+name)
        return None


class VerifiedRuntime:
    def __init__(self,expected_freeze,mode):
        raw=(HERE/'PREPARATION_MANIFEST.json').read_bytes()
        if sha(raw)!=expected_freeze:raise ValueError('EXTERNAL_PREPARATION_FREEZE_MISMATCH')
        freeze=json.loads(raw);self.mode=mode;self.files={}
        for name,want in freeze['files'].items():self.add_path(HERE/name,want['SHA256'])
        closure=json.loads(self.bytes(HERE/'EXECUTED_SOURCE_CLOSURE.json'))
        if mode not in closure['modes']:raise ValueError('EXACT_RUNTIME_MODE_REQUIRED')
        selected=closure['modes'][mode]
        for name,want in selected['files_SHA256'].items():self.add_path(ROOT/name,want)
        self.modules={};self.packages={};self.records={};self.loading={};self.bound_stubs={};self.transport_refusals={}
        self.bootstrap=sys.modules[__name__];self.bootstrap_body=code_identity(self.bootstrap)
        for path in self.files:
            if path.parent==HERE and path.suffix=='.py':self.modules[path.stem]=path
        for name,path in selected['module_paths'].items():self.modules[name]=(ROOT/path).resolve()
        for name,path in self.modules.items():
            parts=name.split('.');parent=path.parent
            for count in range(len(parts)-1,0,-1):
                self.packages.setdefault('.'.join(parts[:count]),set()).add(parent);parent=parent.parent
        self.protected_roots=[(ROOT/p).resolve() for p in selected['protected_roots']]
        self.original_spec=importlib.util.spec_from_file_location
        self.finder=VerifiedFinder(self)

    def add_path(self,path,want):
        unresolved=Path(path)
        if not isinstance(want,str) or len(want)!=64:raise ValueError('EXACT_SOURCE_PIN_REQUIRED')
        if any(p.is_symlink() for p in (unresolved,*unresolved.parents) if p.is_relative_to(ROOT)):
            raise ValueError('SYMLINKED_FROZEN_PROJECT_SOURCE')
        path=unresolved.resolve()
        if not path.is_relative_to(ROOT):raise ValueError('PROJECT_SOURCE_ESCAPE')
        if path in self.files and self.files[path]!=want:raise ValueError('CONFLICTING_PROJECT_SOURCE_PIN')
        self.files[path]=want

    def bytes(self,path):
        unresolved=Path(path)
        if unresolved.is_symlink():raise ValueError('SYMLINKED_FROZEN_PROJECT_SOURCE')
        path=unresolved.resolve()
        if path not in self.files:raise ValueError('FROZEN_SOURCE_CLOSURE_REQUIRED:'+str(path.name))
        data=path.read_bytes()
        if sha(data)!=self.files[path]:raise ValueError('EXECUTED_SOURCE_BYTES_MISMATCH:'+str(path.name))
        return data

    def stub_identity(self,module):
        return (module.SYMBOLS,module.MODES,
                id(module.symbol_order),id(module.symbol_order.__code__),
                id(module.fixed_targets),id(module.fixed_targets.__code__))

    def register_strategy_stub(self,port):
        name='scripts.investment.public_sma_perpetual'
        module=sys.modules.get(name)
        record=next((r for r in self.records.values() if r[0] is port),None)
        if (record is None or record[0] is not port or module is not port.strategy
                or module.symbol_order is not port.symbol_order
                or module.fixed_targets is not port.no_default
                or module.SYMBOLS!=('BTCUSDT','ETHUSDT')
                or module.MODES!=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH')):
            raise ValueError('EXACT_COMPILED_ORIGINAL_STRATEGY_STUB_REQUIRED')
        self.bound_stubs[name]=(module,port,self.stub_identity(module))

    def register_portable_refusals(self,port):
        binder=sys.modules.get('bind_sources');refusal=getattr(binder,'refuse_history',None)
        if self.mode!='generated' or binder is None or 'bind_sources' not in self.records:
            raise ValueError('VERIFIED_GENERATED_BINDER_REQUIRED')
        name,record=next((n,r) for n,r in self.records.items() if r[0] is port)
        body=code_identity(port);old=record[3];changed={n for n in set(old)|set(body) if old.get(n)!=body.get(n)}
        if changed!={'verify','window','prepared'} or any(getattr(port,n) is not refusal for n in changed):
            raise ValueError('EXACT_PORTABLE_HISTORY_REFUSALS_REQUIRED')
        self.records[name]=(*record[:3],body,record[4]);self.transport_refusals[name]=(port,binder,refusal)

    def check_cache(self):
        for name,path in self.modules.items():
            module=sys.modules.get(name)
            if module is None:continue
            if name=='verified_source':
                if module is not self.bootstrap or code_identity(module)!=self.bootstrap_body:
                    raise ValueError('VERIFIED_SOURCE_BOOTSTRAP_BODY_CHANGED')
                continue
            if name in self.bound_stubs:
                stub,port,identity=self.bound_stubs[name]
                if module is not stub or self.stub_identity(stub)!=identity:
                    raise ValueError('VERIFIED_ORIGINAL_STRATEGY_STUB_CHANGED')
                continue
            pending=self.loading.get(name)
            if pending is not None and pending[0] is module and getattr(getattr(module,'__spec__',None),'loader',None) is pending[2]:
                self.bytes(pending[1]);continue
            record=self.records.get(name)
            if record is None or record[0] is not module:
                raise ValueError('UNVERIFIED_CACHED_PROJECT_MODULE:'+name)
            self.check_record(name,record)

    def check_record(self,name,record):
        if name in self.transport_refusals:
            port,binder,refusal=self.transport_refusals[name]
            if binder is not sys.modules.get('bind_sources') or getattr(binder,'refuse_history',None) is not refusal or any(getattr(port,n) is not refusal for n in ('verify','window','prepared')):
                raise ValueError('PORTABLE_HISTORY_REFUSAL_CHANGED')
        module,path,digest,body,loader=record
        if (getattr(module,'__file__',None) is None or Path(module.__file__).resolve()!=path
                or getattr(getattr(module,'__spec__',None),'loader',None) is not loader
                or sha(self.bytes(path))!=digest or code_identity(module)!=body):
            raise ValueError('CACHED_PROJECT_SOURCE_BODY_CHANGED:'+name)

    def audit(self):
        self.check_cache()
        for name,record in self.records.items():self.check_record(name,record)
        return {'executed_source_modules':len(self.records),'project_bytecode_consumed':False,
                'cached_project_module_identity':'CHECKED_LOADER_MODULE_OBJECT_AND_FUNCTION_CODE'}

    def spec(self,name,location,*args,**kwargs):
        if location is not None:
            path=Path(location).resolve()
            if path in self.files or any(path.is_relative_to(root) for root in self.protected_roots):
                self.bytes(path)
                kwargs['loader']=VerifiedLoader(self,name,path)
        return self.original_spec(name,location,*args,**kwargs)

    def install(self):
        self.check_cache()
        sys.meta_path.insert(0,self.finder)
        # Unchanged original helpers use explicit file specs. Bind those too.
        importlib.util.spec_from_file_location=self.spec


def install(expected_freeze,mode):
    global _ACTIVE
    if _ACTIVE is not None:
        if sha((HERE/'PREPARATION_MANIFEST.json').read_bytes())!=expected_freeze or _ACTIVE.mode!=mode:
            raise ValueError('ACTIVE_SOURCE_FREEZE_IDENTITY_CHANGED')
        _ACTIVE.audit();return _ACTIVE
    runtime=VerifiedRuntime(expected_freeze,mode)
    runtime.install();_ACTIVE=runtime
    return runtime


def require_runtime():
    if _ACTIVE is None:raise ValueError('VERIFIED_SOURCE_COLD_BOOTSTRAP_REQUIRED_USE_RUN_VERIFIED')
    _ACTIVE.audit()
    return _ACTIVE

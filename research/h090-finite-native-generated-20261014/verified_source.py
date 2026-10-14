"""Narrow frozen Python-source loader for this generated simulator package.

All project imports compile verified .py bytes. No project .pyc is consumed.
Cached project modules without this runtime's source identity are rejected.
"""
import hashlib,importlib.abc,importlib.machinery,importlib.util,json,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
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
        return None


class VerifiedRuntime:
    def __init__(self,expected_freeze):
        raw=(HERE/'SOURCE_FREEZE.json').read_bytes()
        if sha(raw)!=expected_freeze:raise ValueError('EXTERNAL_H090_SOURCE_FREEZE_MISMATCH')
        freeze=json.loads(raw)
        self.files={}
        for name,want in freeze['files_SHA256'].items():
            self.add(name,want)
        pin_path=HERE/'DEPENDENCY_PINS.json'
        pins=json.loads(self.bytes(pin_path))
        for name,want in pins['files_SHA256'].items():self.add(name,want)
        self.modules={};self.packages={};self.records={};self.loading={};self.bound_stubs={}
        self.bootstrap=sys.modules[__name__]
        self.bootstrap_body=code_identity(self.bootstrap)
        for path in self.files:
            if path.suffix!='.py':continue
            relative=path.relative_to(HERE)
            name=None
            if len(relative.parts)==1:name=path.stem
            elif relative.parts[:3]==('dependencies','repo','src'):
                name='.'.join(relative.parts[3:])[:-3]
            elif relative.parts[:3]==('dependencies','repo','scripts'):
                name='.'.join(relative.parts[2:])[:-3]
            elif relative.parts[:2]==('dependencies','fine'):
                name=path.stem
            elif relative.parts[:3]==('dependencies','account','vendor_quant'):
                name='.'.join(relative.parts[2:])[:-3]
            elif relative.parts==('dependencies','account','bounded_policy.py'):
                name='bounded_policy'
            elif relative.parts==('dependencies','terminal_adapter.py'):
                name='terminal_adapter'
            if name is None:continue
            if name.endswith('.__init__'):name=name[:-9]
            self.modules[name]=path
            parts=name.split('.')
            parent=path.parent if path.name!='__init__.py' else path.parent.parent
            for count in range(len(parts)-1,0,-1):
                package='.'.join(parts[:count])
                self.packages.setdefault(package,set()).add(parent)
                parent=parent.parent
        self.original_spec=importlib.util.spec_from_file_location
        self.finder=VerifiedFinder(self)

    def add(self,name,want):
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or not isinstance(want,str) or len(want)!=64:
            raise ValueError('SAFE_FROZEN_PROJECT_SOURCE_PATH_REQUIRED')
        unresolved=HERE/relative
        if any(candidate.is_symlink() for candidate in (unresolved,*unresolved.parents) if candidate.is_relative_to(HERE)):
            raise ValueError('SYMLINKED_FROZEN_PROJECT_SOURCE')
        path=unresolved.resolve()
        if not path.is_relative_to(HERE):raise ValueError('PROJECT_SOURCE_ESCAPE')
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
        record=self.records.get('h090_exact_original_port')
        if (record is None or record[0] is not port or module is not port.strategy
                or module.symbol_order is not port.symbol_order
                or module.fixed_targets is not port.no_default
                or module.SYMBOLS!=('BTCUSDT','ETHUSDT')
                or module.MODES!=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH')):
            raise ValueError('EXACT_COMPILED_ORIGINAL_STRATEGY_STUB_REQUIRED')
        self.bound_stubs[name]=(module,port,self.stub_identity(module))

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
            if path.is_relative_to(HERE):
                self.bytes(path)
                kwargs['loader']=VerifiedLoader(self,name,path)
        return self.original_spec(name,location,*args,**kwargs)

    def install(self):
        self.check_cache()
        sys.meta_path.insert(0,self.finder)
        # Unchanged original helpers use explicit file specs. Bind those too.
        importlib.util.spec_from_file_location=self.spec


def install(expected_freeze):
    global _ACTIVE
    if _ACTIVE is not None:
        if sha((HERE/'SOURCE_FREEZE.json').read_bytes())!=expected_freeze:
            raise ValueError('ACTIVE_SOURCE_FREEZE_IDENTITY_CHANGED')
        _ACTIVE.audit();return _ACTIVE
    runtime=VerifiedRuntime(expected_freeze)
    runtime.install();_ACTIVE=runtime
    return runtime


def require_runtime():
    if _ACTIVE is None:raise ValueError('VERIFIED_SOURCE_COLD_BOOTSTRAP_REQUIRED_USE_RUN_VERIFIED')
    _ACTIVE.audit()
    return _ACTIVE

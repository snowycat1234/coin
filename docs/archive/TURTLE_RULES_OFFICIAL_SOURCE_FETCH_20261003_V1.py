"""D047 pinned Turtle/ATR code only; reuse accepted fetch and installed Rust.
No market input, private LOCK body, package installation or registry append.
The source-only task verifies API availability, not ATR numerics or returns.
"""
import argparse,ast,hashlib,importlib.util,json,os,re,resource,shlex,signal,subprocess,sys,tarfile,time
from datetime import UTC,datetime
from pathlib import Path
from typing import Union
from urllib.request import urlopen
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
VENDOR=ROOT/'third_party/jesse_example_turtle_rules'
PRE='DOWNLOAD_PREBIND_20261003_V1.json';PRE_SHA='9698ec8417378ace850eb334fa1d96a2e5e177f6475722cef921ac9b2929667c'
ARCHIVE='docs/archive/TURTLE_RULES_OFFICIAL_SOURCE_FETCH_20261003_V1.py'
STATUS='PASS_D047_PINNED_TURTLE_ATR_SOURCE_AND_EXISTING_KERNEL_API_ONLY'
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(p,value):
    with Path(p).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
def stop(signum,frame):raise TimeoutError('Fixed180s source-only deadline')
p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert a.run_dir==STATE/'d047-turtle-official-source-20261003-v1' and a.output==ROOT/'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V1.json'
assert not a.run_dir.exists() and not a.output.exists() and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and os.environ.get('COIN_TASK_ID')
assert sha(__file__)==sha(ROOT/ARCHIVE) and sha(VENDOR/PRE)==PRE_SHA
spec=json.loads((VENDOR/PRE).read_bytes());assert spec['budgets']==dict(new_owned_bytes=1000000,wall_seconds=180,new_dependency_installs=0)
for name,digest in spec['reused_source_hashes'].items():assert sha(ROOT/name)==digest
a.run_dir.mkdir();start=time.monotonic();before=resources.status();assert before['ram_limit_bytes']<=5000000000 and before['swap_bytes']==0 and not before['gpu_used']
binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_source_sha256=sha(__file__),prebind_sha256=PRE_SHA,source_hashes=dict(spec['reused_source_hashes']),exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sys_prefix=sys.prefix)
write(a.run_dir/'RUN_BINDING.json',binding)
report=dict(status='FAIL_D047_PINNED_TURTLE_SOURCE_PROVENANCE',binding=binding,run_dir=str(a.run_dir),run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),market_inputs_read=False,locked_consumed=False,models_fit=0,orders_sent=0,GPU=0,new_dependency_installs=0,registry_appended=False,ATR_numeric_semantics_tested=False,investment_qualification=False)
signal.signal(signal.SIGALRM,stop);signal.alarm(175);error=None
try:
    reused=ROOT/'docs/archive/RSI2_KERNEL_DEPENDENCY_OPERATION_SOURCE_20261002_V1.py';tree=ast.parse(reused.read_text())
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fetch','progress')];assert len(functions)==2 and {n.name for n in functions}=={'fetch','progress'}
    ns=dict(urlopen=urlopen,STATE=STATE,os=os,json=json,time=time);exec(compile(ast.Module(functions,type_ignores=[]),str(reused),'exec'),ns)
    ns['progress']('获取固定Turtle与官方ATR源码',0,2,'源码');sources={}
    for i,entry in enumerate(spec['source_files'],1):
        raw=ns['fetch'](entry['url'],entry['maximum_bytes']);parsed=ast.parse(raw)
        if entry['local_name']=='turtle_rules_original.py':
            classes=[n for n in parsed.body if isinstance(n,ast.ClassDef)];assert len(classes)==1 and classes[0].name=='TurtleRules'
        else:
            atr_nodes=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='atr' and not n.decorator_list];assert len(atr_nodes)==1
        path=VENDOR/entry['local_name']
        with path.open('xb') as stream:stream.write(raw)
        sources[entry['local_name']]=dict(url=entry['url'],path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=len(raw),git_blob_sha1=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),upstream_modified=False)
        ns['progress']('已保存固定官方原字节',i,2,'源码')
    module_spec=importlib.util.spec_from_file_location('_d047_existing_indicator',ROOT/'scripts/investment/public_rsi2_indicator.py');indicator=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(indicator)
    helper_ns,kernel=indicator._context();package=sys.modules['jesse_rust'];assert all(callable(getattr(package,name,None)) for name in ('atr','atr_last','donchian'))
    atr_ns=dict(np=indicator.np,Union=Union,slice_candles=helper_ns['slice_candles'],rust_atr=package.atr,rust_atr_last=package.atr_last)
    original=ast.parse((VENDOR/'atr_indicator_original.py').read_text());node=[n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='atr' and not n.decorator_list][0]
    exec(compile(ast.Module([node],type_ignores=[]),str(VENDOR/'atr_indicator_original.py'),'exec'),atr_ns);assert callable(atr_ns['atr'])
    rust_sources=[];sdist=Path(spec['kernel_sdist_reuse_path'])
    if sdist.is_file():
        assert sha(sdist)==spec['kernel_sdist_sha256']
        with tarfile.open(sdist,'r:gz') as tar:
            for member in tar.getmembers():
                if not member.isfile() or not member.name.startswith('jesse_rust-1.3.0/src/') or not member.name.endswith('.rs'):continue
                assert member.size<=300000;raw=tar.extractfile(member).read()
                if not re.search(rb'fn\s+atr(?:_last)?\s*\(',raw):continue
                path=VENDOR/('atr_kernel_'+Path(member.name).name)
                with path.open('xb') as stream:stream.write(raw)
                rust_sources.append(dict(sdist_path=str(sdist),sdist_sha256=spec['kernel_sdist_sha256'],member=member.name,path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=len(raw),upstream_modified=False))
        assert rust_sources
    note=('# Fixed public TurtleRules and mature ATR dependency\n\n'
        f"Turtle: {spec['repo']}, commit `{spec['commit']}`, `TurtleRules/__init__.py`; MIT, raw SHA `{sources['turtle_rules_original.py']['sha256']}`.\n"
        f"Original ATR wrapper: Jesse commit `417f8765225e3bfc12043d4b712f19fe15a3c078`, raw SHA `{sources['atr_indicator_original.py']['sha256']}`; MIT notice reused at `third_party/jesse_example_donchian/JESSE_LICENSE`.\n\n"
        'No original source is modified. Donchian scalar implementation directly reuses `third_party/jesse_example_donchian/donchian_indicator_original.py`; helper/config/requirements/license identities reuse the frozen RSI2 originals. The already installed official jesse-rust 1.3.0 wheel is used unchanged, without a new environment or installation.\n\n'
        'Original ATR API: `atr(candles, period=14, sequential=False)`; Turtle calls period20. Jesse nonsequential helper retains the last240 candles. Donchian uses current-inclusive candles in this upstream class; it does not use Donchian strategy prior-bar semantics. No local TR/EMA/ATR recurrence is written.\n\n'
        'Original before() fixes S1/entry20/exit10/ATR20/stop2ATR/unit-risk1%/pyramid threshold0.5ATR/max4. The class supports both directions, balance/ATR sizing, pyramiding, stop-loss and prior-profitable S1 filter. It specifies no timeframe. These are source facts, not a promise of a complete COIN execution replication.\n\n'
        'This source task verifies original bytes, frozen installation identity and callable ATR/atr_last/Donchian API. It does not call numeric ATR, read market data, replay strategy or establish profitability, publication availability or native market qualification.\n')
    with (VENDOR/'UPSTREAM.md').open('x',encoding='utf-8') as stream:stream.write(note)
    source_hashes={**spec['reused_source_hashes'],ARCHIVE:sha(__file__)}
    for path in VENDOR.iterdir():assert path.is_file() and not path.is_symlink();source_hashes[path.relative_to(ROOT).as_posix()]=sha(path)
    report.update(status=STATUS,source_files=sources,kernel_rust_sources=rust_sources,sdist_original_reused=bool(rust_sources),existing_kernel_receipt=kernel,ATR_API=dict(signature='atr(candles,period=14,sequential=False)',Turtle_period=20,scalar_window=240,original_function_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),compiled_without_body_modification=True,numeric_called=False),Donchian_API=dict(signature='donchian(candles,period=20,sequential=False)',original_path='third_party/jesse_example_donchian/donchian_indicator_original.py',current_bar_inclusive=True),source_hashes=source_hashes)
except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught));report['status']='FAIL_D047_PINNED_TURTLE_SOURCE_PROVENANCE'
finally:
    signal.alarm(0);report.update(resources_before=before,resources_after=resources.status(),created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    owned=sum(p.stat().st_size for base in (a.run_dir,VENDOR) for p in base.rglob('*') if p.is_file());report['owned_bytes_before_result']=owned
    try:
        assert report['elapsed_seconds']<=180 and owned+len(json.dumps(report).encode())<=1000000 and report['resources_after']['ram_limit_bytes']<=5000000000 and report['resources_after']['swap_bytes']==0 and not report['resources_after']['gpu_used']
    except Exception as caught:error=error or caught;report['status']='FAIL_D047_PINNED_TURTLE_SOURCE_PROVENANCE';report['budget_error']=str(caught)
    write(a.output,report);print(json.dumps(dict(status=report['status'],task_id=binding['task_id'],report_sha256=sha(a.output))))
if error:raise error

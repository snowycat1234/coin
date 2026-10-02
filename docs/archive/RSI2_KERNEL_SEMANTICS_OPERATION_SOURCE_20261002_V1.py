"""Prebound official RSI kernel synthetic semantics; no market IO or model fit."""
import argparse,hashlib,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
import numpy as np
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');VENDOR=ROOT/'third_party/jesse_example_rsi2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with Path(p).open('x') as stream:json.dump(v,stream,indent=2,allow_nan=False)
p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
work=a.run_dir.resolve();out=a.output.resolve()
if work.exists() or out.exists() or not work.is_relative_to(STATE) or not out.is_relative_to(ROOT/'reports/fast_research'):raise ValueError('Exclusive STATE/report required')
if sys.prefix!='/home/xflops/coin-state/v8-clean-env-20261002-v2':raise ValueError('Frozen clean interpreter required')
work.mkdir();sources={str(path.relative_to(ROOT)):sha(path) for path in [ROOT/'scripts/investment/public_rsi2_indicator.py',*VENDOR.iterdir()] if path.is_file()}
binding=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),task_id=os.environ['COIN_TASK_ID'],exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),helper_source_sha256=sha(__file__),source_sha256=sources,base_environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'),base_sys_prefix=sys.prefix,install_pass_report_sha256=sha(ROOT/'reports/fast_research/RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V3.json'),data_scope='SYNTHETIC_PRICES_ONLY_NO_MARKET_IO',seed='NONE_FIXED_HAND_AUTHORED_FIXTURES',models_fit=0,GPU=0)
write(work/'RUN_BINDING.json',binding);write(work/'START.json',dict(binding,status='PREBOUND_START',created_utc=datetime.now(UTC).isoformat()))
report=dict(status='FAIL_OFFICIAL_RSI_KERNEL_SYNTHETIC_SEMANTICS',binding=binding,run_dir=str(work),cases=[],market_inputs_read=False,locked_consumed=False,orders_sent=0,models_fit=0)
started=time.monotonic()
def progress(label,done):
    path=STATE/'task-progress'/('task-'+os.environ['COIN_TASK_ID']+'.json');v=json.loads(path.read_text());v.update(phase=label,completed=done,total=6,unit='关键语义',last_activity_at=time.time());temp=path.with_suffix('.tmp');temp.write_text(json.dumps(v,ensure_ascii=False));os.replace(temp,path)
def record(name,values):
    report['cases'].append(dict(name=name,status='PASS',observations=values));progress(name,len(report['cases']))
def candles(close):
    result=np.empty((len(close),6),np.float64);result[:,0]=np.arange(len(close))*3600000;result[:,1:5]=np.asarray(close)[:,None];result[:,5]=1;return result
try:
    progress('官方RSI ABI及语义实测',0)
    sys.path.insert(0,str(ROOT));from scripts.investment import public_rsi2_indicator as indicator
    runtime=indicator.kernel_receipt();kernel=sys.modules['jesse_rust'];report['supplementary_runtime']=runtime
    assert sys.version_info[:2]==(3,12) and int(np.__version__.split('.')[0])==2
    assert Path(kernel.__file__).resolve()==Path(runtime['package_file']) and runtime['package_version']=='1.3.0'
    record('CP312_NUMPY2_OFFICIAL_BINARY_ABI',dict(numpy_version=np.__version__,python_version=sys.version,extension_sha256=runtime['extension_sha256']))
    source=np.array([100.,101.,100.,101.,100.]);actual=indicator.rsi_series(source,2);expected=np.array([np.nan,np.nan,50.,75.,37.5]);np.testing.assert_array_equal(actual,expected)
    assert indicator.rsi(candles(source),2)==kernel.rsi_last(source,2)==37.5
    record('KNOWN_INITIAL_SEED_AND_ORIGINAL_WRAPPER',dict(input=source.tolist(),output_nullable=[None if np.isnan(x) else float(x) for x in actual]))
    observations={}
    for name,close,value in [('flat',np.full(8,100.),100.),('up',np.arange(100.,108.),100.),('down',np.arange(108.,100.,-1),0.)]:
        series=indicator.rsi_series(close,2);assert np.isnan(series[:2]).all() and np.all(series[2:]==value);assert indicator.rsi(candles(close),2)==value;observations[name]=value
    for n in (1,2):assert np.isnan(indicator.rsi(candles(np.full(n,100.)),2))
    assert indicator.rsi_series(np.array([],np.float64),2).shape==(0,)
    try:indicator.rsi(candles(np.array([],np.float64)),2)
    except IndexError:observations['empty_scalar']='OFFICIAL_INDEX_ERROR'
    else:raise AssertionError('Official empty scalar IndexError must be preserved')
    observations['length_1_2']='NaN';record('OFFICIAL_UNDEFINED_FLAT_AND_MONOTONE_BRANCHES',observations)
    close=np.concatenate([100.+np.arange(60)%2,np.full(240,100.)]).astype(np.float64);c=candles(close);saved=c.copy();scalar=indicator.rsi(c,2);window_scalar=kernel.rsi_last(close[-240:],2);full_scalar=kernel.rsi_last(close,2)
    assert scalar==window_scalar==100. and scalar!=full_scalar
    assert indicator.rsi(close,2)==full_scalar
    np.testing.assert_array_equal(indicator.rsi_series(close[-240:],2),kernel.rsi(close[-240:],2));np.testing.assert_array_equal(c,saved)
    record('EXACT_240_SCALAR_WINDOW_NOT_FULL_PREFIX',dict(two_dimensional_scalar=scalar,last_240_kernel_scalar=window_scalar,one_dimensional_full_prefix_scalar=full_scalar,window=240))
    close=np.array([100.,103.,101.,104.,99.,101.,98.,100.]);saved=close.copy();prefix=indicator.rsi_series(close,2);extended=indicator.rsi_series(np.concatenate([close,[999.,1.,120.]]),2)
    np.testing.assert_array_equal(prefix,extended[:len(close)]);np.testing.assert_array_equal(saved,close)
    assert indicator.rsi(candles(close)[:, :],2)==kernel.rsi_last(close,2)
    record('FUTURE_APPEND_AND_INPUT_IMMUTABILITY',dict(prefix_samples=len(close),future_added=3))
    for path,expected_sha in sources.items():assert sha(ROOT/path)==expected_sha
    assert sha(ROOT/'environments/v8/uv.lock')==binding['base_environment_lock_sha256']
    record('ALL_PREBOUND_SOURCES_AND_BASE_ENVIRONMENT_UNCHANGED',dict(source_files=len(sources),base_environment_mutated=False))
    report.update(status='PASS_OFFICIAL_RSI_KERNEL_SYNTHETIC_SEMANTICS',passed=6,failed=0)
except Exception as error:
    report.update(error_type=type(error).__name__,reason=str(error),passed=len(report['cases']),failed=1);raise
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=sum(p.stat().st_size for p in work.rglob('*') if p.is_file()),resources=resources.status())
    write(out,report);print(json.dumps(dict(status=report['status'],sha256=sha(out),output=str(out))))
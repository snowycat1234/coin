"""Two public, unauthenticated instrument reads; never a historic certification."""
import hashlib,json,os,resource,subprocess,sys,time,urllib.error,urllib.request
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/BYBIT_PUBLIC_SPEC_PROBE_SOURCE_20261003_V1.py'
RUN=STATE/'d048-bybit-public-spec-probe-20261003-v1'
OUT=ROOT/'reports/fast_research/BYBIT_PUBLIC_SPEC_PROBE_20261003_V1.json'
SYMBOLS=('BTCUSDT','ETHUSDT')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None
opener=urllib.request.build_opener(NoRedirect)
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE) and not RUN.exists() and not OUT.exists()
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
before=resources.status();assert before['ram_limit_bytes']<=5_000_000_000 and before['swap_bytes']==0
RUN.mkdir();start=time.monotonic()
binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),source_path=ARCHIVE,
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 source_hashes={ARCHIVE:sha(__file__)},sys_prefix=sys.prefix,
 exact_command=[sys.executable,*sys.argv],request_cap=2,per_URL_attempts=1,
 budgets=dict(wall_seconds=60,peak_RSS_bytes=128_000_000,new_owned_bytes=100_000))
save(RUN/'RUN_BINDING.json',binding)
report=dict(status='FAIL_D048_PUBLIC_SPEC_UNCONFIRMED',binding=binding,run_binding_sha256=sha(RUN/'RUN_BINDING.json'),
 requests=[],confirmed_current_profiles=[],historical_profile_certified=False,orders_sent=0,
 account_keys_used=False,locked_consumed=False,GPU=0,market_arrays_read=False,
 transport='DEFAULT_WSL_HTTPS_VERIFICATION_NO_ALTERNATIVE_HOST_PROXY_REGION_OR_AUTH',
 current_parameters_not_historical_or_native_execution=True)
caught=None
try:
    for symbol in SYMBOLS:
        url='https://api.bybit.com/v5/market/instruments-info?category=linear&symbol='+symbol
        attempt=dict(symbol=symbol,url=url,started_utc=datetime.now(UTC).isoformat(),attempt=1)
        report['requests'].append(attempt)
        request=urllib.request.Request(url,headers={'User-Agent':'coin-public-instrument-research'})
        try:
            with opener.open(request,timeout=20) as response:
                body=response.read(50_001);attempt.update(http_status=response.status,
                    final_URL=response.geturl(),headers={k:response.headers.get(k) for k in ('Date','Content-Type')})
                assert response.geturl()==url and len(body)<=50_000,'No redirects or oversized response'
        except urllib.error.HTTPError as error:
            body=error.read(50_001);attempt.update(http_status=error.code,reason=str(error.reason))
            if len(body)<=50_000:
                with (RUN/(symbol+'-HTTP-ERROR.txt')).open('xb') as f:f.write(body)
                attempt['error_payload_sha256']=sha(RUN/(symbol+'-HTTP-ERROR.txt'))
            report['status']='FAIL_D048_PUBLIC_SPEC_HTTP_STOP_NO_RETRY'
            raise
        assert sum(p.stat().st_size for p in RUN.iterdir() if p.is_file())+len(body)+5000<=100_000,'Reserved public metadata byte budget'
        raw=RUN/(symbol+'-RAW.json')
        with raw.open('xb') as f:f.write(body)
        attempt.update(raw_path=str(raw),raw_bytes=len(body),raw_sha256=sha(raw))
        value=json.loads(body);assert value['retCode']==0 and value['result']['category']=='linear'
        rows=value['result']['list'];assert len(rows)==1 and rows[0]['symbol']==symbol
        item=rows[0]
        assert item['contractType']=='LinearPerpetual' and item['quoteCoin']==item['settleCoin']=='USDT'
        report['confirmed_current_profiles'].append(dict(symbol=symbol,observed_utc=datetime.now(UTC).isoformat(),
            response_server_time_ms=value.get('time'),status=item['status'],baseCoin=item['baseCoin'],
            contractType=item['contractType'],settleCoin=item['settleCoin'],priceFilter=item['priceFilter'],
            lotSizeFilter=item['lotSizeFilter'],leverageFilter=item['leverageFilter'],
            fundingInterval=item['fundingInterval'],source_sha256=sha(raw)))
        assert time.monotonic()-start<=60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=128_000_000
    report['status']='PASS_D048_TWO_CURRENT_PUBLIC_INSTRUMENT_RESPONSES_NOT_HISTORICAL_OR_EXECUTION'
except Exception as error:
    caught=error;report['failure']=dict(type=type(error).__name__,reason=str(error))
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        owned_bytes=sum(p.stat().st_size for p in RUN.iterdir() if p.is_file()),resources_before=before,resources_after=resources.status())
    save(OUT,report)
    print(json.dumps(dict(status=report['status'],actual_requests=len(report['requests']),
        confirmed_profiles=len(report['confirmed_current_profiles']),report_sha256=sha(OUT))))
if caught is not None:raise caught

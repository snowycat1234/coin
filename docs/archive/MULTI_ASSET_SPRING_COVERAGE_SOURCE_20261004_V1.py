"""Small accepted-catalogue coverage only: no market rows or network."""
import hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p,h=None):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<2_000_000
    if h:assert sha(p)==h
    return json.loads(p.read_bytes())
assert os.environ['COIN_TASK_ID']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='a98ceb45178d445b78a2cac113956f0408ac07fe'
pool_path=ROOT/'reports/fast_research/MULTI_ASSET_POINT_IN_TIME_POOL_20261004_V2.json'
pool=small(pool_path,'9b8df895197e888bfb4a4dd2dec08915c5c3425659925408b289483e55e0acf7')
old_path=ROOT/'reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json'
old=small(old_path,'8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa')
assert pool['status']=='POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and pool['score_payloads_read']==0
assert old['status']=='PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
symbols=pool['symbols'];months=['2025-03','2025-04','2025-05','2025-06']
assert len(symbols)==len(set(symbols))==10
keys={(kind,s,interval,m) for s in symbols for m in months
      for kind,interval in [('klines','1m'),('markPriceKlines','1m'),('fundingRate',None)]}
catalog={(r['kind'],r['symbol'],r.get('interval'),r['month']):r for r in old['source_files'].values()}
reused=[];new=[]
for key in sorted(keys,key=str):
    if key not in catalog:new.append(list(key));continue
    r=catalog[key];p=Path(r['normalized_path'])
    assert key[1] in ('BTCUSDT','ETHUSDT') and p.is_file() and not p.is_symlink()
    assert p.stat().st_size==r['normalized_bytes']
    reused.append(dict(key=list(key),normalized_path=str(p),bytes=p.stat().st_size,
        accepted_normalized_sha256=r['normalized_sha256'],accepted_receipt=r.get('source_acceptance',r.get('independent_QA')),
        payload_read_or_hashed=False))
assert len(keys)==120 and len(reused)==24 and len(new)==96
warm_path=STATE/'d056-multiasset-winter-source-acceptance-20261004-v2/INPUT_MANIFEST.json'
warm=small(warm_path,'56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193')
assert warm['status']=='PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS'
assert warm['selected_symbols']==symbols and len(warm['daily_records'])==70 and len(warm['market_records'])==90
minute_warm=warm['warmup_minute_records']+[r for r in warm['market_records'] if r['kind']=='klines']
assert len(minute_warm)==60
for r in warm['daily_records']+minute_warm:
    p=Path(r['normalized_path']);assert p.is_file() and p.stat().st_size==r['normalized_bytes']
run=STATE/'d062-source-coverage-20261004-v1';run.mkdir()
r=dict(status='PASS_ACCEPTED_METADATA_COVERAGE_NOT_NEW_SOURCE_OR_ECONOMICS',task_id=os.environ['COIN_TASK_ID'],
    parent_commit=head,run_dir=str(run),symbols=symbols,score_months=months,days=122,required_minutes=175680,
    required_market_files=120,accepted_existing_files=24,new_source_files_required=96,
    reused_sources=reused,new_required_keys=new,warm_daily_aliases=70,warm_minute_aliases=60,
    expected_unique_scoring_and_warm_identities=250,new_data_availability='UNKNOWN_PENDING_OFFICIAL_FETCH_AND_QA',
    inspected_metadata={str(pool_path.relative_to(ROOT)):sha(pool_path),str(old_path.relative_to(ROOT)):sha(old_path),
                        str(warm_path):sha(warm_path)},market_payloads_read=0,old_source_QA_calls=0,
    new_downloads=0,market_accounts=0,models_fit=0,HPO=0,locked_body_read=False,
    created_utc=datetime.now(UTC).isoformat(),command=['python',*__import__('sys').argv],source_sha256=sha(Path(__file__)))
for p in (run/'COVERAGE.json',ROOT/'reports/fast_research/MULTI_ASSET_SPRING_COVERAGE_20261004_V1.json'):
    with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(status=r['status'],accepted_files=24,new_required=96,warm_aliases=130)),flush=True)

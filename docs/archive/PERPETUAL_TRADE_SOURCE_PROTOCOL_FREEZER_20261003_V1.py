import hashlib,json,os,resource,time
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
from scripts.investment import perpetual_trade_source as source
ROOT=source.ROOT
META='reports/fast_research/PERPETUAL_TRADE_SOURCE_METADATA_20261003_V1.json'
META_SHA='b03187a50bafe29df7e285a372547d44bf440f0be13b44a03a5f4ed0a2b4b400'
OWN='scripts/investment/perpetual_trade_source.py'
OWN_SHA='8c569bb1add310c230230cc9e2cd923adba7f4ac37776e48c1fdfc1ed0e9240c'
ARCHIVE='docs/archive/PERPETUAL_TRADE_SOURCE_PROTOCOL_FREEZER_20261003_V1.py'
started=time.monotonic();before=resources.status()
assert source.sha(ROOT/META)==META_SHA and source.sha(ROOT/OWN)==OWN_SHA
meta=json.loads((ROOT/META).read_bytes())
assert meta['status']==source.META_STATUS and meta['actual_files']==42 and meta['archive_bodies_downloaded']==0
assert [{k:e[k] for k in source.entries()[0]} for e in meta['objects']]==source.entries()
assert meta['maximum_announced_zip_bytes']<=16_000_000 and meta['announced_compressed_total_bytes']==26_453_768
assert source.sha(ROOT/ARCHIVE)==source.sha(__file__)
frozen={**source.PINS,OWN:OWN_SHA,META:META_SHA}
for p in [ARCHIVE,'environments/v8/uv.lock','state/dataset_lock.json','scripts/research_v7/oracle_flow_ceiling.py','scripts/research_v8/registry.py','src/quant/resources.py','src/quant/disk.py','src/quant/paths.py']:
    frozen[p]=source.sha(ROOT/p)
for p,h in frozen.items():assert source.sha(ROOT/p)==h,(p,h)
protocol=ROOT/'protocols/PERPETUAL_TRADE_SOURCE_20261003_V1.json'
spec=dict(contract_id='USD_M_TRADE_KLINE_SOURCE_20261003_V1',created_utc=datetime.now(UTC).isoformat(),freeze_task_id=os.environ['COIN_TASK_ID'],entries=source.entries(),budgets=source.BOUNDS,frozen_sources=frozen,metadata_path=META,metadata_sha256=META_SHA,metadata_task_id=meta['binding']['task_id'],source_sha256=OWN_SHA,
    run_dir='/home/xflops/coin-state/perpetual-trade-source-actual-20261003-v1',output_path='reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json',
    upstream_repo='https://github.com/binance/binance-public-data',upstream_commit=source.UPSTREAM,software_license='UPSTREAM_README_MIT_DECLARATION_DATA_TERMS_SEPARATE',
    environment=dict(sys_prefix='/home/xflops/coin-state/v8-clean-env-20261002-v2',lock_path='environments/v8/uv.lock',lock_sha256=frozen['environments/v8/uv.lock']),
    periods=[dict(id='122D',start='2025-08-01',end_exclusive='2025-12-01',days=122),dict(id='90D',start='2025-12-01',end_exclusive='2026-03-01',days=90)],
    daily_start='2025-01-01',daily_end_exclusive='2026-03-01',daily_rows_per_symbol=424,initial_completed_daily_warmup_days=212,
    minute_start='2025-08-01',minute_end_exclusive='2026-03-01',minute_rows_per_symbol=305280,symbols=source.SYMBOLS,
    price_definition='Official USD-M traded kline OHLCV; no BBO or executable fill certification',available_time='Exclusive closed-bar proxy, historical publication not certified',
    funding_rate_unit='UNCONFIRMED',funding_read_or_zero_filled=False,funding_unit_certified=False,native_margin_or_execution_certified=False,economic_scope='NOT_EVALUATED',
    old_mark_index_funding_source_QA_or_download_replayed=False,locked_consumed=False,models_fit=0,orders_sent=0,GPU=0,shared_RAM_limit_bytes=5000000000,swap_bytes=0)
with protocol.open('x') as stream:json.dump(spec,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
result=dict(status='COMPLETE_USDM_TRADE_SOURCE_PROTOCOL_FREEZE_METADATA_ONLY',task_id=os.environ['COIN_TASK_ID'],source_sha256=source.sha(__file__),protocol_path=str(protocol),protocol_sha256=source.sha(protocol),protocol_bytes=protocol.stat().st_size,frozen_source_count=len(frozen),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status(),market_arrays_read=False,network_requests=0)
out=Path(__file__).parent/'FREEZE.json'
with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result))
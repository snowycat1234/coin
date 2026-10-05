"""Single public-default Chandelier applicability probe, never filtered PnL."""
import json,hashlib,os,resource,time
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment import cta_classics as cta
from scripts.investment.chandelier_short_levels import levels,RULES,PACKAGE,runtime
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.run_cta_leaderboard import stamp
from scripts.research_v7.oracle_flow_ceiling import Progress

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
out=ROOT/'reports/SHORT_CHANDELIER_PROBE_20261006_V1.json';assert not out.exists();started=time.monotonic();progress=Progress()
p=ROOT/'reports/SHORT_REBOUND_TIMING_20261006_V1.json';prior=json.loads(p.read_bytes());raw=json.loads((ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json').read_bytes());spec=raw['protocol'];symbols=tuple(spec['symbols'])
assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256'];assert sha(spec['data_manifest']['path'])==spec['data_manifest']['sha256']
runtime();files={str(f.relative_to(PACKAGE)):sha(f) for f in PACKAGE.rglob('*') if f.is_file() and '__pycache__' not in f.parts};license_paths=[v for v in PACKAGE.glob('pandas_ta_classic-*.dist-info/licenses/LICENSE')];assert len(license_paths)==1 and 'MIT' in license_paths[0].read_text()
whole=load_portfolio_window(spec['data_manifest']['path'],symbols,stamp(spec['economics_start']),stamp(spec['economics_end_exclusive']));bars=whole['daily'];indicator=levels(bars,symbols);lookup={(v['available_us'],v['symbol']):v['short_exit_line'] for v in indicator.iter_rows(named=True)}
cut=stamp('2025-04-10');changed=bars.with_columns(*(pl.when(pl.col('close_us')>cut).then(pl.col(k)*1.8).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')));future=levels(changed,symbols);assert indicator.filter(pl.col('available_us')<=cut).equals(future.filter(pl.col('available_us')<=cut))
# A second, unmodified pinned Jesse kernel independently verifies the old exit line.
kernel=cta.channel_kernel();days=[]
for i,d in enumerate(prior['days']):
 begin=stamp(d['date']);end=begin+cta.DAY;record=[];block=next(whole['minute_blocks'](begin,end,trade_ranges=True));assert len(block['times'])==1440
 for v in d['assets']:
  s=v['symbol'];b=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=begin)).sort('close_us');c=b.select('open','close','high','low','volume').to_numpy();candles=__import__('numpy').column_stack((b['open_us'].to_numpy()/1000,c));native=float(kernel(candles,period=10).upperband);assert abs(native-v['prior10_day_high'])<=max(1e-12,abs(native)*1e-12)
  line=lookup[(begin,s)];assert line is not None and line>0
  crossed=__import__('numpy').flatnonzero(block['market'][s]['close']>line);trigger=int(block['times'][crossed[0]])+60000000 if len(crossed) else None
  record.append(dict(symbol=s,old_actual_day_short_net=v['net'],existing_exit_line=v['prior10_day_high'],public_CE_line=line,CE_first_closed_trade_minute_cross_us=trigger,old_line_cross_us=v['first_closed_minute_above_existing_short_exit_us'],full_account_improvement='NOT_RUN',stop_fill='NOT_SIMULATED; NEXT_ELIGIBLE_OPEN_WITH_FEES_AND_CAPACITY_REQUIRED'))
 days.append(dict(date=d['date'],assets=record));progress.update('默认Chandelier适用性与旧退出独立核对',i+1,5,'日期')
result=dict(status='PASS_PUBLIC_CHANDELIER_DEFAULT_CAUSAL_APPLICABILITY_NOT_ECONOMIC_BACKTEST',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),rules=RULES,source_sha256=sha(__file__),adapter_sha256=sha(ROOT/'scripts/investment/chandelier_short_levels.py'),prior_diagnostic_sha256=sha(p),manifest=spec['data_manifest'],supplementary_runtime=dict(path=str(PACKAGE),installed_file_sha256=files,wheel_sha256='e8e1ede0c13d5927d28c91dce3d5ab2c71a1fb7f2e62fb61fe95178d4ab768e0',repo='https://github.com/xgboosted/pandas-ta-classic',version='0.8.32',license='MIT',local_modifications='NONE',wheel_requirements_sha256=sha(ROOT/'environments/supplementary/pandas-ta-classic-0.8.32.txt')),independent_old_exit_line='PASS_PINNED_UNMODIFIED_JESSE_DONCHIAN_SCALAR_ALL40_ASSET_DAYS',future_perturbation='PASS_ALL_SYMBOL_LINES_BEFORE_CUTOFF_UNCHANGED',configurations=1,fits=0,new_account_replays=0,new_market_downloads=0,days=days,resources=dict(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),limitations=['POST_RESULT_WORST5_APPLICABILITY_ONLY','CE_LINE_CROSS_NOT_NET_ALPHA_OR_EXECUTABLE_STOP_PRICE','NO_REENTRY_TRAILING_RATCHET_OR_FULL_CAPITAL_ACCOUNT_EVALUATED','MMR_FUNDING_UNITS_AND_SOURCE_PROXY_UNCHANGED'])
out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n');progress.stop.set();progress.thread.join(timeout=3)
print(json.dumps([dict(date=d['date'],CE_cross_assets=[x['symbol'] for x in d['assets'] if x['CE_first_closed_trade_minute_cross_us'] is not None],old_cross_assets=[x['symbol'] for x in d['assets'] if x['old_line_cross_us'] is not None]) for d in days]))
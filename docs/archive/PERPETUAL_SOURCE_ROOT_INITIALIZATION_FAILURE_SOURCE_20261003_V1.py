"""Metadata closure of the new trade source; no repeat market QA or economics."""
import argparse, hashlib, importlib.util, json, os, resource, sys, time
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
EXPECTED={
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json':'2e067443a79cebcb7b304e451130fc7c14cc62903a335f9a5742c5de859f0615',
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_INDEPENDENT_QA_20261003_V2.json':'99d918102e825324d678037d39648081e6aa16fd2c1a1f89cf8a4c11660492fb',
 'reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json':'f7b3e8eb724b8196280ef872454b36297171b5f487bea94410dc547eb846d045',
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_INDEPENDENT_ACTUAL_EXIT_20261003_V2.json':'710fcbe03c836faa5fea811c2e9c8ff6162e40413f9214443896d3dbead46546',
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
 assert hashlib.sha256((ROOT/GUARD).read_bytes()).hexdigest()==GUARD_SHA
 s=importlib.util.spec_from_file_location('perpetual_source_root_guards',ROOT/GUARD);g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
 g.require(a.run_dir.parent==STATE and not a.run_dir.exists() and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'New metadata closure only')
 a.run_dir.mkdir();started=time.monotonic();before=g.resources.status();g.bounded(before)
 files={name:g.small(ROOT/name,digest)[0] for name,digest in EXPECTED.items()}
 actual,independent,manifest,exitproof=files.values()
 g.require(actual['status']=='PASS_USDM_TRADE_KLINE_FORMAT_CALENDAR_PENDING_INDEPENDENT_ACCEPTANCE' and actual['actual_files']==42,'Producer completed fixed42')
 g.require(independent['status']=='PASS_NEW_USDM_TRADE_SOURCE_RAW_NORMALIZED_CALENDAR_VOLUME_ONLY' and independent['completed_rows_verified']==611408 and independent['completed_files_verified']==42,'Independent raw/normalized source acceptance')
 g.require(independent['actual_report_sha256']==EXPECTED[next(iter(EXPECTED))] and actual['binding']['source_hashes'].items()<=independent['verified_source_hashes'].items(),'Independent source byte identity')
 tasks={role:g.closed(value['binding']['task_id']) for role,value in [('producer',actual),('independent',independent),('input_metadata',manifest)]}
 g.require([(w['id'],w['days']) for w in manifest['windows']]==[('122D',122),('90D',90)] and manifest['unique_data_files']==84 and not manifest['market_arrays_read'],'Two fixed complete prior-development windows')
 pins=dict(independent['verified_source_hashes']);pins.update(EXPECTED);pins['scripts/investment/accept_perpetual_source.py']=g.sha(__file__);pins[GUARD]=GUARD_SHA
 for name,digest in pins.items():g.small(g.project(name),digest,False)
 binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=pins,sys_prefix=sys.prefix)
 g.write(a.run_dir/'RUN_BINDING.json',binding)
 after=g.resources.status();g.bounded(after)
 report=dict(status='PASS_NEW_PERPETUAL_TRADE_SOURCE_ROOT_METADATA_CLOSURE',binding=binding,closed_prior_tasks=tasks,
  run_dir=str(a.run_dir),run_binding_sha256=g.sha(a.run_dir/'RUN_BINDING.json'),source_acceptance_granted=True,
  accepted_scope='42_NEW_USDM_TRADE_CSV_PARQUET_FORMAT_AND_COMPLETE_CALENDAR_ONLY',
  input_binding_path=list(EXPECTED)[2],input_binding_sha256=EXPECTED[list(EXPECTED)[2]],
  trade_daily_rows_per_symbol=424,trade_minute_rows_per_symbol=305280,
  prior_source_QA_repeated=False,market_arrays_read=False,economics='NOT_EVALUATED',
  funding_unit_certified=False,funding_rate_unit='UNCONFIRMED',native_Bybit_execution_certified=False,
  MMR_and_filters_certified=False,locked_consumed=False,orders_sent=0,models_fit=0,
  own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED',elapsed_seconds=time.monotonic()-started,
  peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=after,
  candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
 digest,size=g.write(a.output,report);print(json.dumps(dict(status=report['status'],sha256=digest,task_id=binding['task_id'],bytes=size)))
if __name__=='__main__':main()

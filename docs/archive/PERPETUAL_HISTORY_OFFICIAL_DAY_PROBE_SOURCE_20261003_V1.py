"""Check the sole missing UTC day via the same official daily archive; no fills."""
import argparse, ast, csv, hashlib, importlib.util, io, json, os, resource, sys, time, zipfile
from datetime import UTC, datetime
from pathlib import Path
import httpx
from quant import resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_trade_source as trade
from scripts.research_v8 import funding_price_source_v2 as original
from scripts.research_v8.registry import FIELDS, append_event

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();plan=json.loads(a.protocol.read_bytes());own=sha(__file__)
    assert plan['checker_sha256']==own and plan['day']=='2024-08-12'
    assert a.run_dir==STATE/'d042-official-mark-day-probe-20261003-v1' and not a.run_dir.exists()
    assert str(a.output.relative_to(ROOT))==plan['output'] and not a.output.exists()
    assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
    for name,digest in plan['source_hashes'].items():assert sha(ROOT/name)==digest
    gspec=importlib.util.spec_from_file_location('daily_probe_guard',ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py')
    g=importlib.util.module_from_spec(gspec);gspec.loader.exec_module(g)
    diagnostic=json.loads((ROOT/plan['diagnostic_path']).read_bytes())
    assert sha(ROOT/plan['diagnostic_path'])==plan['diagnostic_sha256']
    assert diagnostic['raw_clock_diagnostic']['missing_utc_days']==[plan['day']]
    g.closed(diagnostic['binding']['task_id']);g.bounded(resources.status())
    entry=dict(market='futures/um',partition='daily',kind='markPriceKlines',interval='1m',symbol='BTCUSDT',date=plan['day'])
    entry['url']='https://data.binance.vision/data/futures/um/daily/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-'+plan['day']+'.zip'
    entry['checksum_url']=entry['url']+'.CHECKSUM'
    assert entry['url']==plan['url']
    a.run_dir.mkdir();started=time.monotonic();progress=original.progress_writer(1)
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=own,protocol_sha256=sha(a.protocol),
        source_hashes=plan['source_hashes'],exact_command=[sys.executable,*sys.argv])
    original.write_new(a.run_dir/'RUN_BINDING.json',binding)
    report=dict(status='FAIL_D042_OFFICIAL_DAY_CLOCK_PROBE',binding=binding,run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),
        diagnostic_sha256=plan['diagnostic_sha256'],source_accepted=False,source_repaired=False,
        economics='NOT_COMPUTED',models_fit=0,orders_sent=0,locked_consumed=False,GPU=0)
    identity='D042-OFFICIAL-MARK-DAY-PROBE-20261003-V1'
    event=dict.fromkeys(FIELDS);event.update(experiment_id=identity,event_id=identity+':START',event_type='OPERATIONAL_SOURCE_DIAGNOSTIC_START',
        protocol_hash=sha(a.protocol),data_manifest_hash=plan['diagnostic_sha256'],feature_set='ONE_OFFICIAL_DAILY_MARK_CLOCK',
        labels='NONE',model_family='NONE',hyperparameters={'entry':entry},seed=None,thresholds=plan['budgets'],
        cost_assumptions='NOT_COMPUTED',all_folds='ONE_DATA_GAP_DAY',success_failure='START_BEFORE_NETWORK',
        reason_for_next_experiment='Check whether official daily source has the two missing raw records',result_influenced_later_choice=False,
        source_hashes=plan['source_hashes'],exact_command=' '.join(binding['exact_command']))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        progress.update('官方同日HEAD/CHECKSUM与原始时钟',0,1,'日档')
        with httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False) as client:
            resolved=trade.metadata_inspector(client)(entry)
        report['metadata']=resolved
        assert resolved['metadata_object_available'] and 0<resolved['announced_zip_bytes']<=2_000_000
        patch=trade.daily.private['exact_patch']();changes=[]
        nodes=[n for n in ast.parse((ROOT/'scripts/research_v8/funding_price_source_v2.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='download_archive']
        assert len(nodes)==1
        tree=patch(ast.Module(nodes,type_ignores=[]),changes,'Exact same-host single official daily URL',
            "require(url.startswith('https://data.binance.vision/data/futures/um/monthly/'),'Unexpected upstream URL')",
            "require(url == '"+entry['url']+"','Unexpected upstream URL')")
        namespace=dict(vars(original),LIMIT=8_000_000)
        exec(compile(ast.fix_missing_locations(tree),'<private-single-official-day-download>','exec'),namespace)
        component=json.loads((ROOT/trade.COMPONENT).read_bytes())
        with trade.file_deadline():archive,checksum,declared=namespace['download_archive'](resolved,a.run_dir,original.official_module(component))
        start=int(datetime(2024,8,12,tzinfo=UTC).timestamp())*1000;expected=set(range(start,start+86_400_000,60_000));clocks=[]
        with zipfile.ZipFile(archive) as z:
            with z.open(z.infolist()[0]) as binary,io.TextIOWrapper(binary,encoding='utf-8-sig',newline='') as text:
                for i,row in enumerate(csv.reader(text)):
                    if i==0 and row[0]=='open_time':assert row==trade.HEADER;continue
                    assert len(row)==12 and row[0].isdecimal() and row[6].isdecimal()
                    t=int(row[0]);assert int(row[6])==t+59999;clocks.append(t)
            assert z.testzip() is None
        missing=sorted(expected-set(clocks));assert len(clocks)==len(set(clocks)) and not (set(clocks)-expected)
        report.update(status='COMPLETE_D042_OFFICIAL_DAILY_MARK_CLOCK_PROBE_NOT_SOURCE_ACCEPTANCE',
            archive_path=str(archive),archive_sha256=sha(archive),checksum_path=str(checksum),checksum_sha256=sha(checksum),
            CSV_declared_bytes=declared,actual_rows=len(clocks),expected_rows=1440,
            missing_UTC_minutes=[datetime.fromtimestamp(t/1000,UTC).isoformat() for t in missing],
            complete_day=(not missing and len(clocks)==1440),
            monthly_missing_records_available=all(int(datetime.fromisoformat(t).timestamp()*1000) in set(clocks)
                for t in diagnostic['raw_clock_diagnostic']['missing_UTC_minutes']),
            full_EOF_CRC=True,price_values_parsed_or_analyzed=False,AST_changes=changes)
        progress.update('官方日档时钟已实测',1,1,'日档')
    except Exception as e:report.update(error_type=type(e).__name__,reason=str(e));raise
    finally:
        progress.stop.set();progress.thread.join(timeout=3)
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=original.owned_bytes(a.run_dir),resources=resources.status())
        assert report['owned_bytes']<=5_000_000 and report['elapsed_seconds']<=120 and report['peak_RSS_bytes']<=512_000_000
        original.write_new(a.output,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=identity+':RESULT',event_type='OPERATIONAL_SOURCE_DIAGNOSTIC_RESULT',
            success_failure=report['status'],artifact_path=str(a.output.relative_to(ROOT)),artifact_sha256=sha(a.output)))
    print(json.dumps(dict(status=report['status'],complete_day=report['complete_day'],monthly_missing_records_available=report['monthly_missing_records_available'],sha256=sha(a.output))))
if __name__=='__main__':main()

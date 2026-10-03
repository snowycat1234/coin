"""UNRUN D043 source-only draft: 51 complete parent files plus 21 new files.

The D042 parent remains FAILED. No old file/receipt is copied, relabelled or
edited. A new independent task must verify ALL72 original ZIP/Parquet pairs,
using each item's explicitly authorized source_owner_path. This adapter only
privately extends the pinned D042 orchestration; original download/conversion
bodies and their resource/calendar guards remain unchanged.
"""
from __future__ import annotations
import argparse, ast, importlib.util, json, os, time
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_history_source as base

CONTRACT='D043_FIXED_213D_MIXED_OWNER_OFFICIAL_SOURCE_V1'
STATUS='PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'
PARENT='reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json'
PARENT_SHA='82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427'
METADATA='reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json'
METADATA_SHA='cbfde5a12c27613666ef5d45a71963000a6b0b0e5e6f3fcef6cf0227e70101bf'
PARENT_SOURCE='scripts/investment/perpetual_history_source.py'
PARENT_SOURCE_SHA='c088f011b584c32fb3963ac1342482bba7d4eee24cd443f365338ba6ea437a79'
PARENT_ROOT=STATE/'d042-perpetual-history-source-20261003-v1'
PINS={**base.PINS,PARENT_SOURCE:PARENT_SOURCE_SHA,PARENT:PARENT_SHA,METADATA:METADATA_SHA,
    'protocols/PERPETUAL_HISTORY_SOURCE_20261003_V1.json':'7e21e39b24d979a87e2ca07ea6a5f0cf55aa8086c73723abb5290ac8129d7d98'}
BOUNDS=dict(base.BOUNDS)  # Root must explicitly freeze this inherited bound.
require,sha,write=base.require,base.sha,base.write


def identity(item):
    return item['kind'],item['symbol'],item.get('interval'),item['month']


def entries():
    # Select by product/month, never source order, availability or profit.
    selected=[]
    for item in base.entries():
        end='2024-07' if item.get('interval')!='2h' else '2023-12'
        if item['month']<=end:selected.append(item)
    require(len(selected)==72 and len({identity(e) for e in selected})==72,'Exact213-day source universe')
    return selected


def is_reused(entry):
    return entry['kind']=='klines' or (entry['kind']=='markPriceKlines' and entry['symbol']=='BTCUSDT')


def metadata_receipt(spec,hashes):
    metadata=base.small(ROOT/METADATA,METADATA_SHA)
    require(spec['metadata_path']==METADATA and spec['metadata_sha256']==METADATA_SHA
        and metadata['status']==base.META_STATUS
        and metadata['completed_files']==metadata['required_files']==148
        and metadata['archive_bodies_downloaded']==0
        and metadata['binding']['mode']=='metadata'
        and metadata['binding']['source_sha256']==PARENT_SOURCE_SHA,
        'Original complete metadata receipt retained as148, not forged as72')
    module_spec=importlib.util.spec_from_file_location('_d043_original_closed_guard',ROOT/base.GUARD)
    guard=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(guard)
    closed=guard.closed(metadata['binding']['task_id'])
    require(closed['task']['ended_at']<=time.time(),'Metadata genuine completed0 before new task')
    return metadata,closed


def selected_metadata_objects(metadata):
    by_id={identity(e):e for e in metadata['objects']}
    require(len(by_id)==len(metadata['objects'])==148,'No duplicated original metadata identity')
    result=[]
    for expected in entries():
        item=by_id[identity(expected)]
        require(all(item.get(k)==v for k,v in expected.items())
            and item['metadata_object_available'] is True
            and type(item['announced_zip_bytes']) is int
            and 0<item['announced_zip_bytes']<=BOUNDS['max_archive_bytes']
            and item['checksum']['format_and_filename_valid'] is True,
            'Exact72 previously inspected official URLs and announced checksums')
        result.append(item)
    return result


def validate(spec,mode,own):
    require(mode=='source' and spec['mode']=='source' and spec['ready_for_execution'] is True
        and spec['contract_id']==CONTRACT and spec['entries']==entries()
        and spec['required_files']==72 and spec['expected_reused_files']==51 and spec['expected_new_files']==21
        and spec['score_period_start']=='2024-01-01' and spec['score_period_end_exclusive']=='2024-08-01'
        and spec['score_days']==213 and spec['score_minutes_per_symbol']==306720,
        'One fixed213-day source-only universe,51 explicit prior files and21 new')
    require(spec['budgets']==BOUNDS and spec['combined_capacity_reservation_bytes']==2_000_000_000
        and spec['environment']['sys_prefix']==str(STATE/'v8-clean-env-20261002-v2'),
        'Explicit inherited1GB source/RSS,2GB capacity, CPU-only environment')
    require(spec['parent_source_path']==PARENT and spec['parent_source_sha256']==PARENT_SHA
        and spec['source_owner_paths']==[str(PARENT_ROOT),str(Path(spec['run_dir']).resolve())]
        and Path(spec['run_dir']).resolve()!=PARENT_ROOT,
        'Two exact owners; new task never writes failed parent directory')
    previous=base.small(ROOT/base.FORMAT,PINS[base.FORMAT])
    for key in ('funding_header','price_header','funding_nominal_interval_tolerance_ms'):
        require(spec[key]==previous[key],'Original format guard unchanged: '+key)
    require(spec['funding_rate_unit']=='UNCONFIRMED' and spec['funding_unit_certified'] is False
        and spec['economic_scope']=='NOT_EVALUATED','Source format cannot certify unit or investment')
    hashes=spec['frozen_sources']
    require(hashes.get(own)==sha(__file__) and all(hashes.get(p)==h for p,h in PINS.items()),'Own and exact reused source/proof map')
    for path,digest in hashes.items():
        candidate=(ROOT/path).resolve()
        require(not Path(path).is_absolute() and candidate.is_relative_to(ROOT)
            and not (ROOT/path).is_symlink() and sha(candidate)==digest,'Ordinary frozen source changed: '+path)
    return hashes


def prior_files(spec):
    parent=base.small(ROOT/PARENT,PARENT_SHA)
    require(parent['status']=='FAIL_D042_HISTORY_SOURCE' and parent['reason']=='Missing/shifted minute'
        and parent['completed_files']==len(parent['sources'])==83 and parent['required_files']==148
        and parent['binding']['source_sha256']==PARENT_SOURCE_SHA
        and Path(parent['binding']['spec']['run_dir'])==PARENT_ROOT,
        'Failed whole parent kept failed, only its explicitly completed per-file records may be reused')
    module_spec=importlib.util.spec_from_file_location('_d043_parent_failed_task_guard',ROOT/base.GUARD)
    guard=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(guard)
    failed=guard.closed(parent['binding']['task_id'],1)
    by_id={identity(e):e for e in parent['sources']}
    require(len(by_id)==83,'Unique completed parent records')
    reused={}
    for entry in entries():
        if not is_reused(entry):continue
        item=by_id[identity(entry)];job=PARENT_ROOT/(f"{entry['symbol']}-{entry['interval']}-{entry['month']}"
            if entry['kind']=='klines' else f"{entry['kind']}-{entry['symbol']}-{entry['month']}")
        require(Path(item['receipt_path'])==job/'receipt.json' and Path(item['normalized_path'])==job/'source.parquet',
            'Exact existing completed archive owner, not failed August partial')
        receipt,_=guard.small(job/'receipt.json',item['receipt_sha256'])
        require(all(receipt['entry'].get(k)==v for k,v in entry.items())
            and receipt['status']==('PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY' if entry['kind']=='klines'
                else 'SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA'), 'Original completed per-file status, no relabel')
        aliases={k:receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')} if entry['kind']=='klines' else dict(
            normalized_path=receipt['parquet_path'],normalized_sha256=receipt['parquet_sha256'],normalized_bytes=receipt['parquet_bytes'],
            rows=receipt['stats']['rows'],stats=receipt['stats'],normalized_schema=receipt['stats']['schema'])
        require(all(item[k]==value for k,value in aliases.items()) and item['entry']==receipt['entry'],
            'Unmodified parent receipt/PQ metadata; independent raw/PQ QA remains necessary')
        require(not (job/'source.parquet').is_symlink() and (job/'source.parquet').stat().st_size==item['normalized_bytes'],
            'Prior normalized file still exists at declared size; no payload read here')
        reused[identity(entry)]=dict(item,source_owner_path=str(PARENT_ROOT),source_role='REUSED_COMPLETED_FILE_FROM_FAILED_PARENT_PENDING_FULL_QA',
            parent_source_report_path=PARENT,parent_source_report_sha256=PARENT_SHA,parent_source_status=parent['status'])
    require(len(reused)==51 and sum(not is_reused(e) for e in entries())==21,'Exactly51/21 roles; no data availability selection')
    return reused,failed


def context(spec):
    """Private original main; no new source loop or shared globals mutation."""
    require(sha(ROOT/PARENT_SOURCE)==PARENT_SOURCE_SHA,'Frozen parent orchestration bytes')
    reused,failed=prior_files(spec);patch=base.trade.daily.private['exact_patch']();changes=[]
    nodes=[n for n in ast.parse((ROOT/PARENT_SOURCE).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main']
    require(len(nodes)==1,'One original source main');tree=ast.Module(nodes,type_ignores=[])
    literal=patch.__globals__['_ExactPatch'](ast.Constant(148),ast.Constant(72));tree=literal.visit(tree)
    require(literal.count==8,'Eight original148 count/progress constants; no broad date/format change')
    changes.append(dict(change='Explicit72 source/progress count',matches=8,before=148,after=72))
    for label,old,new in [
        ('Exact72 metadata projection',"objects=metadata['objects'] if metadata else entries()",'objects=selected_metadata_objects(metadata)'),
        ('Bind true failed parent and explicit reuse',"write(run/'RUN_BINDING.json',binding)",
         "binding['failed_parent_source_task']=FAILED_PARENT_TASK\nbinding['mixed_owner_source_derivation']=DERIVATION\nwrite(run/'RUN_BINDING.json',binding)"),
        ('Explicit reused51 branch without copying or old conversion',
         "guard(entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes'])",
         """if identity(entry) in REUSED:
    result['sources'].append(REUSED[identity(entry)])
    result['completed_files']=result['actual_files']=len(result['sources'])
    result['actual_source_rows']=sum(r['rows'] for r in result['sources'])
    guard()
    progress.update('原完整单档只读复用；父任务仍FAIL',result['completed_files'],72,'文件')
    continue
guard(entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes'])"""),
        ('New item explicit source owner',"result['sources'].append(item)",
         "item['source_owner_path']=str(run)\nitem['source_role']='NEW_OFFICIAL_CONVERSION_PENDING_FULL_QA'\nresult['sources'].append(item)"),
        ('Complete exact21 downloads and two genuine owners before producer PASS',
         "result.update(status=SOURCE_STATUS,declared_uncompressed_csv_bytes=declared,cumulative_declared_CSV_not_extracted=True,funding_events=sum(r['rows'] for r in result['sources'] if r['kind']=='fundingRate'))",
         """require(result['archive_bodies_downloaded']==21
    and sum(i['source_role']=='REUSED_COMPLETED_FILE_FROM_FAILED_PARENT_PENDING_FULL_QA' for i in result['sources'])==51
    and sum(i['source_role']=='NEW_OFFICIAL_CONVERSION_PENDING_FULL_QA' for i in result['sources'])==21,
    'Exactly51 reused/21 newly converted archive bodies before source PASS')
require(all(i['source_owner_path']==(str(PARENT_ROOT) if is_reused(i) else str(run))
    and Path(i['source_owner_path']).is_dir() and not Path(i['source_owner_path']).is_symlink()
    and Path(i['receipt_path']).parent.parent==Path(i['source_owner_path'])
    and Path(i['normalized_path']).parent.parent==Path(i['source_owner_path']) for i in result['sources']),
    'Each actual source belongs to its exact frozen original or new owner')
result.update(status=SOURCE_STATUS,declared_uncompressed_csv_bytes=declared,cumulative_declared_CSV_not_extracted=True,funding_events=sum(r['rows'] for r in result['sources'] if r['kind']=='fundingRate'))"""),
        ('Late byte/resource failure never retains producer PASS',
         "result.update(error_type=type(error).__name__,reason=str(error))",
         "result.update(status='FAIL_D043_213_HISTORY_SOURCE',error_type=type(error).__name__,reason=str(error))"),
        ('No false148 downloads or parent acceptance',"write(out,result)",
         "result['expected_reused_files']=51\nresult['expected_new_files']=21\nresult['reused_completed_files']=sum(i['source_role']=='REUSED_COMPLETED_FILE_FROM_FAILED_PARENT_PENDING_FULL_QA' for i in result['sources'])\nresult['new_completed_files']=sum(i['source_role']=='NEW_OFFICIAL_CONVERSION_PENDING_FULL_QA' for i in result['sources'])\nresult['failed_parent_source_status']='FAIL_D042_HISTORY_SOURCE'\nresult['failed_parent_source_report_sha256']=PARENT_SHA\nresult['all72_independent_QA_required']=True\nwrite(out,result)")]:
        tree=patch(tree,changes,label,old,new)
    for old,new in [('FAIL_D042_HISTORY_','FAIL_D043_213_HISTORY_'),
        ('D042_OFFICIAL_HISTORY_','D043_213_OFFICIAL_HISTORY_'),
        ('JAN2024_JUN2025_FIXED_SOURCE_ONLY','JAN2024_JUL2024_FIXED_SOURCE_ONLY'),
        ('Fixed547day same-product public directional comparison; no profit-based date selection',
         'Fixed213day complete source interval chosen before new account PnL; parent missing mark remains rejected'),
        ('D042 固定148档；新来源格式阶段，尚待独立验收','D043 固定72档；51完整单档复用+21新档，尚待全面独立QA')]:
        visitor=patch.__globals__['_ExactPatch'](ast.Constant(old),ast.Constant(new));tree=visitor.visit(tree)
        require(visitor.count==1,'Exact source-only label anchor: '+old)
        changes.append(dict(change='Source-only metadata label',old=old,new=new))
    environment=dict(vars(base),__file__=__file__,CONTRACT=CONTRACT,SOURCE_STATUS=STATUS,BOUNDS=BOUNDS,PINS=PINS,
        entries=entries,validate=validate,metadata_receipt=metadata_receipt,selected_metadata_objects=selected_metadata_objects,
        identity=identity,is_reused=is_reused,PARENT_ROOT=PARENT_ROOT,
        REUSED=reused,FAILED_PARENT_TASK=failed,DERIVATION=changes,PARENT_SHA=PARENT_SHA)
    exec(compile(ast.fix_missing_locations(tree),'<D043-private-original-source-main>','exec'),environment)
    require(base.CONTRACT=='D042_OFFICIAL_PERPETUAL_HISTORY_SOURCE_V1' and base.entries()[0]['month']=='2024-01',
        'Original module globals unchanged')
    return environment


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--mode',choices=['source'],required=True)
    args,_=parser.parse_known_args()
    spec=base.small(args.protocol);context(spec)['main']()


if __name__=='__main__':main()

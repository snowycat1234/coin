"""D045 fixed303 source selection; original transport/conversion main reused.

54 completed files keep their original owners; only40 missing mark/funding
files are downloaded. Prior metadata is projected, never relabelled as a new
94-file network task. Producer completion is not independent acceptance.
"""
from __future__ import annotations
import argparse,ast,importlib.util,time
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment import perpetual_history_source as base

CONTRACT='D045_FIXED_303D_MIXED_OWNER_OFFICIAL_SOURCE_V1'
STATUS='PASS_D045_94_HISTORY_FORMAT_54_REUSED_40_NEW_PENDING_INDEPENDENT_QA'
PARENT_SOURCE='scripts/investment/perpetual_history_source.py'
PARENT_SOURCE_SHA='c088f011b584c32fb3963ac1342482bba7d4eee24cd443f365338ba6ea437a79'
H42='reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json'
T40='reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json'
M42='reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json'
M40='reports/fast_research/PERPETUAL_TRADE_SOURCE_METADATA_20261003_V1.json'
PINS={**base.PINS,PARENT_SOURCE:PARENT_SOURCE_SHA,
 H42:'82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427',
 T40:'2e067443a79cebcb7b304e451130fc7c14cc62903a335f9a5742c5de859f0615',
 M42:'cbfde5a12c27613666ef5d45a71963000a6b0b0e5e6f3fcef6cf0227e70101bf',
 M40:'b03187a50bafe29df7e285a372547d44bf440f0be13b44a03a5f4ed0a2b4b400'}
BOUNDS=dict(base.BOUNDS)
require,sha,write=base.require,base.sha,base.write

def identity(e):return e.get('kind','klines'),e['symbol'],e.get('interval'),e['month']
def entries():
    result=[]
    for kind,interval,first in [('klines','1m','2024-09'),('klines','1d','2024-02'),('markPriceKlines','1m','2024-09'),('fundingRate',None,'2024-09')]:
        for symbol in base.SYMBOLS:
            for month in base.data.month_range(first,'2025-06'):
                suffix=f'{symbol}-fundingRate-{month}.zip' if interval is None else f'{interval}/{symbol}-{interval}-{month}.zip'
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
                e=dict(market='futures/um',partition='monthly',kind=kind,symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval is not None:e['interval']=interval
                result.append(e)
    require(len(result)==94 and len({identity(e) for e in result})==94,'Fixed94 official303-day source selectors')
    return result
def loader():
    spec=importlib.util.spec_from_file_location('_d045_closed_guard',ROOT/base.GUARD)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);return g
def validate(spec,mode,own):
    require(mode=='source' and spec['mode']==mode and spec['ready_for_execution'] is True and spec['contract_id']==CONTRACT
        and spec['entries']==entries() and spec['required_files']==94 and spec['expected_reused_files']==54 and spec['expected_new_files']==40
        and spec['score_period_start']=='2024-09-01' and spec['score_period_end_exclusive']=='2025-07-01'
        and spec['score_days']==303 and spec['score_minutes_per_symbol']==436320,'Frozen303/94/54/40 scope')
    require(spec['budgets']==BOUNDS and spec['combined_capacity_reservation_bytes']==2_000_000_000
        and spec['environment']['sys_prefix']==str(STATE/'v8-clean-env-20261002-v2'),'Original bounded resource budget')
    old=base.small(ROOT/base.FORMAT,PINS[base.FORMAT])
    require(all(spec[k]==old[k] for k in ('funding_header','price_header','funding_nominal_interval_tolerance_ms')),'Original format headers/tolerance')
    require(spec['funding_rate_unit']=='UNCONFIRMED' and spec['funding_unit_certified'] is False and spec['economic_scope']=='NOT_EVALUATED','No unit/economics promotion')
    h=spec['frozen_sources'];require(h.get(own)==sha(__file__) and all(h.get(p)==v for p,v in PINS.items()),'Exact original components and own source')
    for p,v in h.items():
        q=ROOT/p;require(not Path(p).is_absolute() and q.resolve().is_relative_to(ROOT) and not q.is_symlink() and sha(q)==v,'Frozen bytes: '+p)
    return h
def metadata_receipt(spec,hashes):
    g=loader();objects={};proofs=[]
    for name,count,status in [(M42,148,base.META_STATUS),(M40,42,'PASS_USDM_TRADE_KLINE_HEAD_CHECKSUM_METADATA_NOT_SOURCE_ACCEPTANCE')]:
        old=base.small(ROOT/name,PINS[name]);closed=g.closed(old['binding']['task_id'])
        require(old['status']==status and len(old['objects'])==count and old['archive_bodies_downloaded']==0,'Original closed metadata scope preserved')
        proofs.append(dict(path=name,sha256=PINS[name],closed_task=closed))
        for e in old['objects']:
            key=identity(e)
            # D040 overlapping months use D042 except its new2025 daily sources.
            if key not in objects:objects[key]=e
    selected=[]
    for template in entries():
        e=objects[identity(template)]
        require(all(e.get(k)==v for k,v in template.items()) and e['metadata_object_available'] is True
            and type(e['announced_zip_bytes']) is int and 0<e['announced_zip_bytes']<=BOUNDS['max_archive_bytes']
            and e['checksum']['format_and_filename_valid'] is True,'Original announced official URL/checksum')
        selected.append(e)
    return dict(objects=selected,owned_bytes=0,scope='PROJECTION_OF_TWO_PREVIOUS_CLOSED_METADATA_TASKS_NO_NEW_HEAD',prior_proofs=proofs),proofs
def prior_files(spec):
    g=loader();reused={};proofs=[];expected={identity(e):e for e in entries() if e['kind']=='klines'}
    for name,owner,code,status in [(H42,STATE/'d042-perpetual-history-source-20261003-v1',1,'FAIL_D042_HISTORY_SOURCE'),
        (T40,STATE/'perpetual-trade-source-actual-20261003-v1',0,'PASS_USDM_TRADE_KLINE_FORMAT_CALENDAR_PENDING_INDEPENDENT_ACCEPTANCE')]:
        old=base.small(ROOT/name,PINS[name]);closed=g.closed(old['binding']['task_id'],code)
        require(old['status']==status,'Original producer status retained')
        if code:require(old['completed_files']==len(old['sources'])==83 and old['required_files']==148,'Failed whole547 parent retained')
        proofs.append(dict(path=name,sha256=PINS[name],status=status,closed_task=closed))
        for item in old['sources']:
            key=identity(item)
            if key not in expected or (name==T40 and not (key[2]=='1d' and key[3]>='2025-01')):continue
            require(key not in reused,'Unique existing54 selected sources')
            template=expected[key];job=owner/f"{template['symbol']}-{template['interval']}-{template['month']}"
            require(Path(item['receipt_path'])==job/'receipt.json' and Path(item['normalized_path'])==job/'source.parquet','Exact original owner paths')
            receipt,_=g.small(job/'receipt.json',item['receipt_sha256'])
            require(receipt['status']=='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY' and all(receipt['entry'].get(k)==v for k,v in template.items()),'Original complete per-file receipt')
            require(all(item[k]==receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')),'Unmodified original aliases')
            require(not (job/'source.parquet').is_symlink() and (job/'source.parquet').stat().st_size==item['normalized_bytes'],'Existing declared payload size, no array read')
            reused[key]=dict(item,kind='klines',entry=receipt['entry'],source_owner_path=str(owner),source_role='REUSED_COMPLETE_PRODUCER_FILE_QA_SCOPE_SEPARATE',
                parent_source_report_path=name,parent_source_report_sha256=PINS[name],parent_source_status=status)
    require(len(reused)==54 and len(expected)==54,'Exactly54 original complete files;40 new price/fund files')
    return reused,proofs
def context(spec):
    validate(spec,'source',Path(__file__).resolve().relative_to(ROOT).as_posix())
    reused,parents=prior_files(spec);patch=base.trade.daily.private['exact_patch']();changes=[]
    nodes=[n for n in ast.parse((ROOT/PARENT_SOURCE).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main']
    require(len(nodes)==1,'One pinned original orchestration main');tree=ast.Module(nodes,type_ignores=[])
    visitor=patch.__globals__['_ExactPatch'](ast.Constant(148),ast.Constant(94));tree=visitor.visit(tree);require(visitor.count==8,'Exact8 count anchors')
    changes.append(dict(change='Fixed94 count',matches=8))
    edits=[('Bind actual previous producer proofs',"write(run/'RUN_BINDING.json',binding)","binding['prior_producer_tasks']=PARENTS\nbinding['mixed_owner_source_derivation']=DERIVATION\nwrite(run/'RUN_BINDING.json',binding)"),
      ('Reuse54 no old conversion',"guard(entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes'])","""if identity(entry) in REUSED:
    result['sources'].append(REUSED[identity(entry)])
    result['completed_files']=result['actual_files']=len(result['sources'])
    result['actual_source_rows']=sum(r['rows'] for r in result['sources'])
    guard();progress.update('原完整单档复用；QA资格独立记录',result['completed_files'],94,'文件')
    continue
guard(entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes'])"""),
      ('New original owner',"result['sources'].append(item)","item['source_owner_path']=str(run)\nitem['source_role']='NEW_OFFICIAL_CONVERSION_PENDING_FIRST_QA'\nresult['sources'].append(item)"),
      ('Reject late failures',"result.update(error_type=type(error).__name__,reason=str(error))","result.update(status='FAIL_D045_303_HISTORY_SOURCE',error_type=type(error).__name__,reason=str(error))"),
      ('Actual54/40 completion',"result.update(status=SOURCE_STATUS,declared_uncompressed_csv_bytes=declared,cumulative_declared_CSV_not_extracted=True,funding_events=sum(r['rows'] for r in result['sources'] if r['kind']=='fundingRate'))","""require(result['archive_bodies_downloaded']==40 and sum(i['source_role']=='REUSED_COMPLETE_PRODUCER_FILE_QA_SCOPE_SEPARATE' for i in result['sources'])==54,'Actual54 reuse40 downloads')
require(all(Path(i['receipt_path']).parent.parent==Path(i['source_owner_path']) and Path(i['normalized_path']).parent.parent==Path(i['source_owner_path']) for i in result['sources']),'Original mixed-owner paths')
result.update(status=SOURCE_STATUS,declared_uncompressed_csv_bytes=declared,cumulative_declared_CSV_not_extracted=True,funding_events=sum(r['rows'] for r in result['sources'] if r['kind']=='fundingRate'),reused_completed_files=54,new_completed_files=40,failed_parent_source_status='FAIL_D042_HISTORY_SOURCE',independent_first_QA_required=70,accepted_prior_QA_reuse_expected=24)""")]
    for label,old,new in edits:tree=patch(tree,changes,label,old,new)
    for old,new in [('FAIL_D042_HISTORY_','FAIL_D045_303_HISTORY_'),('D042_OFFICIAL_HISTORY_','D045_303_OFFICIAL_HISTORY_'),('JAN2024_JUN2025_FIXED_SOURCE_ONLY','SEP2024_JUN2025_FIXED_SOURCE_ONLY'),('Fixed547day same-product public directional comparison; no profit-based date selection','Fixed303day sources selected before new account PnL; no changed funding/cost/calendar'),('D042 固定148档；新来源格式阶段，尚待独立验收','D045 固定94档；54完整复用40新档，70首次QA待验收')]:
        v=patch.__globals__['_ExactPatch'](ast.Constant(old),ast.Constant(new));tree=v.visit(tree);require(v.count==1,'Exact metadata label '+old);changes.append(dict(label=old,matches=1))
    env=dict(vars(base),__file__=__file__,CONTRACT=CONTRACT,SOURCE_STATUS=STATUS,BOUNDS=BOUNDS,PINS=PINS,entries=entries,validate=validate,
        metadata_receipt=metadata_receipt,identity=identity,REUSED=reused,PARENTS=parents,DERIVATION=changes)
    exec(compile(ast.fix_missing_locations(tree),'<D045-private-original-source-main>','exec'),env)
    require(base.CONTRACT=='D042_OFFICIAL_PERPETUAL_HISTORY_SOURCE_V1' and len(base.entries())==148,'Original globals unchanged')
    return env
def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--protocol',type=Path,required=True);a,_=p.parse_known_args()
    context(base.small(a.protocol))['main']()
if __name__=='__main__':main()

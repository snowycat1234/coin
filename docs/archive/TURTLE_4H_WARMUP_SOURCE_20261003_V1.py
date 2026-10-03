"""D047: four official USD-M July/August2024 4h warmup files.

Thin private adaptation of the accepted D041 producer; transport, CHECKSUM,
ZIP CRC and numeric CSV parsing stay original. Importing performs no IO job.
"""
from __future__ import annotations
import ast, hashlib
from pathlib import Path
from scripts.investment import perpetual_2h_warmup_source as base

ROOT,STATE=base.ROOT,base.STATE
SYMBOLS=['BTCUSDT','ETHUSDT']
MONTHS=['2024-07','2024-08']
FOUR_HOUR_US=14_400_000_000
CONTRACT='D047_OFFICIAL_PERPETUAL_4H_JUL_AUG2024_SOURCE_V1'
STATUS='PASS_D047_OFFICIAL_PERPETUAL_4H_WARMUP_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA'
FAILURE='FAIL_D047_PERPETUAL_4H_WARMUP_SOURCE'
BOUNDS=dict(base.BOUNDS)
BASE_PATH='scripts/investment/perpetual_2h_warmup_source.py'
BASE_SHA='a41accdebc6ce84186d32a5f6c84e51bcb727b844706a63b1ebe37b664ac3b4c'
LOCAL_GUARD={'state/dataset_lock.json':base.PINS['state/dataset_lock.json']}
PINS={path:value for path,value in base.PINS.items() if path not in LOCAL_GUARD}
PINS[BASE_PATH]=BASE_SHA
require=base.require

def sha(path):
    """Stream all digests, including the local-only private LOCK guard."""
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def entries():
    result=[]
    for symbol in SYMBOLS:
        for month in MONTHS:
            url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/4h/{symbol}-4h-{month}.zip'
            result.append(dict(market='futures/um',partition='monthly',kind='klines',interval='4h',symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM'))
    return result

def validate(spec,own):
    require(spec['ready_for_execution'] is True and spec['contract_id']==CONTRACT
        and spec['entries']==entries() and spec['source_start']=='2024-07-01'
        and spec['source_end_exclusive']=='2024-09-01' and spec['symbols']==SYMBOLS
        and spec['interval']=='4h' and spec['expected_archives']==4
        and spec['expected_rows_per_archive']==186 and spec['expected_rows_per_symbol']==372
        and spec['expected_total_rows']==744 and spec['budgets']==BOUNDS,'Exact four monthly 4h archives and original hard budgets')
    require(spec['announced_zip_bytes_expected'] is None and spec['source_acceptance_before_actual'] is False
        and spec['publication_time_certified'] is False and spec['economic_scope']=='NOT_EVALUATED'
        and spec['environment']['sys_prefix']==str(STATE/'v8-clean-env-20261002-v2'),'Unknown sizes and source-only scope')
    require(spec['local_non_git_hash_guard']==LOCAL_GUARD,'Explicit private LOCK hash-only guard')
    for path,value in LOCAL_GUARD.items():require(sha(ROOT/path)==value,'Local private hash guard changed')
    hashes=spec['frozen_sources']
    require(not any(path in hashes for path in LOCAL_GUARD) and hashes.get(own)==sha(__file__)
        and all(hashes.get(path)==value for path,value in PINS.items()),'Ordinary source binding; private LOCK excluded from portable map')
    for path,value in hashes.items():
        candidate=(ROOT/path).resolve()
        require(candidate.is_relative_to(ROOT) and not (ROOT/path).is_symlink()
            and sha(candidate)==value,'Frozen ordinary source changed: '+path)
    return hashes

def context():
    """Compile original two functions with exact date/interval/count anchors."""
    require(sha(ROOT/BASE_PATH)==BASE_SHA,'Accepted D041 base bytes')
    nodes=[n for n in ast.parse((ROOT/BASE_PATH).read_bytes()).body
        if isinstance(n,ast.FunctionDef) and n.name in ('adapted_functions','main')]
    require(len(nodes)==2 and {n.name for n in nodes}=={'adapted_functions','main'},'Exact two accepted function bodies')
    tree=ast.Module(nodes,type_ignores=[]);changes=[]
    patch=base.trade.daily.private['exact_patch']()
    for label,old,new in [
        ('Per-file 4h month job',"job=run/f\"{entry['symbol']}-2h-2025-07\";job.mkdir();receipt=dict(status='FAIL_D041_2H_ARCHIVE',entry=entry)".split(';')[0],"job=run/f\"{entry['symbol']}-4h-{entry['month']}\""),
        ('4h rows per monthly archive',"require(frame.height==372 and target.stat().st_size<=BOUNDS['file_write_limit_bytes'],'372 exact July2h bars and bounded normalized file')","require(frame.height==186 and target.stat().st_size<=BOUNDS['file_write_limit_bytes'],'186 exact monthly4h bars and bounded normalized file')"),
        ('Four format files complete',"require(result['actual_files']==2 and result['actual_source_rows']==744 and all(sha(ROOT/p)==h for p,h in hashes.items()),'Both sources complete and frozen bytes preserved')","require(result['actual_files']==4 and result['archive_bodies_downloaded']==4 and result['actual_source_rows']==744 and all(sha(ROOT/p)==h for p,h in hashes.items()),'Four sources complete and frozen bytes preserved')"),
        ('62-day 4h source scope',"result.update(status=STATUS,rows_per_symbol=372,normalized_interval='2h',warmup_scope='31_FULL_UTC_DAYS_372_BARS_PER_ASSET')","result.update(status=STATUS,rows_per_symbol=372,normalized_interval='4h',warmup_scope='62_FULL_UTC_DAYS_372_BARS_PER_ASSET')"),
        ('Fail marker on any task failure',"result.update(error_type=type(error).__name__,reason=str(error))","result.update(status=FAILURE,error_type=type(error).__name__,reason=str(error))"),
    ]:tree=patch(tree,changes,label,old,new)
    literals={
        '2h':'4h',
        'pl.lit("2h")':'pl.lit("4h")',
        '2h UTC daily bucket':'4h UTC daily bucket',
        '2h twelve bars per complete UTC day':'4h six bars per complete UTC day',
        '2h interval label':'4h interval label',
        '2h unchanged trade format calendar duration':'4h unchanged trade format calendar duration',
        'duration=TWO_HOUR_US':'duration=FOUR_HOUR_US',
        '<D041-private-original-download>':'<D047-private-original-download>',
        '<D041-private-original-2h-parser>':'<D047-private-original-4h-parser>',
        '<D041-private-original-trade-convert>':'<D047-private-original-trade-convert>',
        'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 12]':'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 6]',
        'FAIL_D041_2H_ARCHIVE':'FAIL_D047_4H_ARCHIVE',
        'PASS_D041_2H_ARCHIVE_FORMAT_CALENDAR_ONLY':'PASS_D047_4H_ARCHIVE_FORMAT_CALENDAR_ONLY',
        'FAIL_D041_PERPETUAL_2H_JULY_SOURCE':FAILURE,
        'USD_M_TRADE_KLINE_2H_JULY_WARMUP_SOURCE':'USD_M_TRADE_KLINE_4H_JUL_AUG2024_WARMUP_SOURCE',
        'JUL2025_SOURCE_ONLY':'JUL_AUG2024_SOURCE_ONLY',
        'Original public2h benchmark needs400h warmup; source only':'Fixed Turtle4h benchmark needs official past240bar warmup; source only',
        'D041 官方7月2小时成交预热；来源格式阶段，尚待独立验收':'D047 官方2024年7/8月4小时预热；来源格式阶段，尚待独立验收',
        'coin-fixed-july-2h-source/1.0':'coin-fixed-jul-aug2024-4h-source/1.0',
        '官方两小时档下载/CRC/完整UTC格式':'官方4小时档下载/CRC/完整UTC格式',
    }
    counts={key:0 for key in literals}
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in literals:
            counts[node.value]+=1;node.value=literals[node.value]
        if isinstance(node,ast.Name) and node.id=='TWO_HOUR_US':node.id='FOUR_HOUR_US'
        if isinstance(node,ast.keyword) and node.arg=='TWO_HOUR_US':node.arg='FOUR_HOUR_US'
    require(all(counts[key]>=1 for key in literals),'Every explicit 4h source adaptation matched')
    for key,count in counts.items():changes.append(dict(label='D047 literal',old=key,new=literals[key],matches=count))
    months=[n for n in ast.walk(tree) if isinstance(n,ast.keyword) and n.arg=='month'
        and isinstance(n.value,ast.Constant) and n.value.value=='2025-07']
    require(len(months)==1,'Original per-file source month anchor')
    months[0].value=ast.parse("entry['month']",mode='eval').body
    main=[n for n in tree.body if n.name=='main'][0]
    progress_calls=0
    for node in ast.walk(main):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            if isinstance(node.func.value,ast.Name) and node.func.value.id=='original' and node.func.attr=='progress_writer':
                require(len(node.args)==1 and isinstance(node.args[0],ast.Constant) and node.args[0].value==2,'Original two-file progress');node.args[0].value=4;progress_calls+=1
            elif isinstance(node.func.value,ast.Name) and node.func.value.id=='progress' and node.func.attr=='update' and len(node.args)>=3:
                if isinstance(node.args[2],ast.Constant) and node.args[2].value==2:node.args[2].value=4;progress_calls+=1
        if isinstance(node,ast.keyword) and node.arg=='required_files':
            require(isinstance(node.value,ast.Constant) and node.value.value==2,'Original required files');node.value.value=4
    require(progress_calls==4,'Only original four file-progress total anchors')
    event=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name) and n.func.value.id=='event' and n.func.attr=='update']
    require(len(event)==1,'Single original compact registration')
    event_hashes=[k for k in event[0].keywords if k.arg=='source_hashes'];require(len(event_hashes)==1,'One event source binding')
    event_hashes[0].value=ast.parse("{protocol.relative_to(ROOT).as_posix():binding['protocol_sha256']}",mode='eval').body
    bindings=[n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='binding' for t in n.targets)]
    require(len(bindings)==1,'One run binding')
    bindings[0].value.keywords.append(ast.keyword(arg='local_non_git_hash_guard',value=ast.Name(id='LOCAL_GUARD',ctx=ast.Load())))
    ns=dict(vars(base),__file__=__file__,__name__='_d047_source_private',CONTRACT=CONTRACT,STATUS=STATUS,FAILURE=FAILURE,
        PINS=PINS,LOCAL_GUARD=LOCAL_GUARD,BOUNDS=BOUNDS,FOUR_HOUR_US=FOUR_HOUR_US,entries=entries,validate=validate,sha=sha)
    exec(compile(ast.fix_missing_locations(tree),'<D047-private-accepted-D041-source>','exec'),ns)
    core=ns['adapted_functions']
    def adapted():
        download,parsers,convert,inner_changes=core()
        return download,parsers,convert,changes+inner_changes
    ns['adapted_functions']=adapted
    require(base.TWO_HOUR_US==7_200_000_000 and base.entries()[0]['month']=='2025-07'
        and base.PINS['state/dataset_lock.json']==LOCAL_GUARD['state/dataset_lock.json'],'Frozen module globals unchanged')
    return ns

def main():context()['main']()

if __name__=='__main__':main()

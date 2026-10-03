"""D047 independent four-file raw/normalized QA; UNRUN until root binding.

Reuse the accepted D041 main and independent original audit_one, privately
changing only product dates, four-file counts and the actual 4h duration.
No HTTP, old source QA, trading account, private LOCK body or unit promotion.
"""
from __future__ import annotations
import ast
from pathlib import Path
from scripts.investment import audit_perpetual_2h_warmup_source as parent

ROOT,STATE=parent.ROOT,parent.STATE
PARENT='scripts/investment/audit_perpetual_2h_warmup_source.py'
PARENT_SHA='37509d2d539ccd6cb07c7e56c76a66d1c1008ad8bc35e78e5f0f6e694db1fb7b'
BASE,BASE_SHA=parent.BASE,parent.BASE_SHA
CONTRACT='D047_OFFICIAL_PERPETUAL_4H_JUL_AUG2024_SOURCE_V1'
ACTUAL_STATUS='PASS_D047_OFFICIAL_PERPETUAL_4H_WARMUP_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA'
STATUS='PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY'
FAIL='FAIL_D047_OFFICIAL_4H_WARMUP_INDEPENDENT_SOURCE_QA'
BUDGET=dict(wall_seconds=300,peak_RSS_bytes=512_000_000,new_owned_bytes=5_000_000)
OUTPUT='reports/fast_research/TURTLE_4H_WARMUP_SOURCE_INDEPENDENT_20261003_V1.json'
SOURCE_DIR='d047-turtle-4h-warmup-source-20261003-v1'
need,sha=parent.need,parent.sha

def entries():
    result=[]
    for symbol in ('BTCUSDT','ETHUSDT'):
        for month in ('2024-07','2024-08'):
            url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/4h/{symbol}-4h-{month}.zip'
            result.append(dict(market='futures/um',partition='monthly',kind='klines',interval='4h',symbol=symbol,
                month=month,url=url,checksum_url=url+'.CHECKSUM'))
    return result

def adapted_audit(b):
    """Original independent CSV/CRC/numeric body, without producer parser."""
    tree=ast.parse((ROOT/BASE).read_bytes())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit_one']
    need(len(nodes)==1,'Unique original independent raw/source audit_one')
    text=ast.unparse(nodes[0])
    replacements=[("'PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY'","'PASS_D047_4H_ARCHIVE_FORMAT_CALENDAR_ONLY'"),
        ("DAY if entry['interval'] == '1d' else MINUTE",'14400000000')]
    for old,new in replacements:
        need(text.count(old)==1,'Exact new4h independent substitution: '+old);text=text.replace(old,new,1)
    namespace=dict(vars(b));exec(compile(ast.parse(text),'<D047-independent-original-4h-audit-one>','exec'),namespace)
    core=namespace['audit_one']
    def audit(g,item,entry,source_root,spec):
        row=core(g,item,entry,source_root,spec)
        need(row['rows']==186,'Exactly31 UTC days times6 bars, each new archive')
        return dict(row,source_id=f"trade:4h:{entry['symbol']}:{entry['month']}",normalized_bytes=item['normalized_bytes'])
    return audit,dict(base_sha256=BASE_SHA,only_substitutions=replacements,
        derived_function_AST_sha256=parent.hashlib.sha256(ast.dump(ast.parse(text),include_attributes=False).encode()).hexdigest())

def context():
    need(sha(ROOT/PARENT)==PARENT_SHA,'Accepted D041 independent source unchanged')
    nodes=[n for n in ast.parse((ROOT/PARENT).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main']
    need(len(nodes)==1,'Single accepted independent orchestration')
    tree=ast.Module(nodes,type_ignores=[])
    # All changes are in the outer orchestration; raw numerical audit stays original.
    literals={
        'D041_OFFICIAL_PERPETUAL_2H_JULY_SOURCE_V1':CONTRACT,
        'd041-official-perpetual-2h-july-20261003-v1':SOURCE_DIR,
        'D041-JULY-2H-INDEPENDENT-20261003-V1':'D047-JUL-AUG2024-4H-INDEPENDENT-20261003-V1',
        'TWO_JULY_2025_USDM_2H_RAW_NORMALIZED':'FOUR_JUL_AUG2024_USDM_4H_RAW_NORMALIZED',
        'JULY2025_WARMUP_SOURCE_ONLY':'JUL_AUG2024_WARMUP_SOURCE_ONLY',
        'Only two new official2h signal warmup files require independent raw checks':'Only four new official4h warmup files require independent raw checks',
        'Only two completed fixed July2h archives':'Only four completed fixed Jul/Aug2024 4h archives',
        'Exact two archive identities':'Exact four archive identities',
        '仅July新增2h · 原CSV/UTC/量独立核对':'仅2024年7/8月新增4h · 原CSV/UTC/量独立核对',
        'Complete fixed372 and processbudget':'Complete fixed186 and processbudget',
    }
    counts={key:0 for key in literals}
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in literals:
            counts[node.value]+=1;node.value=literals[node.value]
    need(all(value==1 for value in counts.values()),'All exact four-file scope literals matched once')
    # Source counts, progress and per-file rows: never rewrite arbitrary numbers.
    count_matches=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and len(node.comparators)==1:
            last=node.comparators[0]
            if isinstance(last,ast.Constant) and last.value==2:
                is_source_count=isinstance(node.left,ast.Call) and isinstance(node.left.func,ast.Name) and node.left.func.id=='len'
                if is_source_count:last.value=4;count_matches+=1
            elif isinstance(last,ast.Constant) and last.value==372:
                need(isinstance(node.left,ast.Subscript) and isinstance(node.left.slice,ast.Constant)
                    and node.left.slice.value=='rows','Only per-file372 audit guard');last.value=186;count_matches+=1
        if isinstance(node,ast.Compare) and len(node.comparators)==2:
            last=node.comparators[-1]
            if isinstance(last,ast.Constant) and last.value==2:last.value=4;count_matches+=1
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='progress_writer':
            need(len(node.args)==1 and node.args[0].value==2,'Original two-file progress');node.args[0].value=4;count_matches+=1
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
            and node.func.value.id=='progress' and node.func.attr=='update'):
            need(len(node.args)>=3 and node.args[2].value==2,'Original per-file progress update');node.args[2].value=4;count_matches+=1
        if isinstance(node,ast.keyword) and node.arg=='completed_files_verified' and isinstance(node.value,ast.Constant):
            need(node.value.value==2,'Original completed file count');node.value.value=4;count_matches+=1
    need(count_matches==6,'Only six fixed count/progress/per-file anchors')
    checks=ast.parse("""
need(a.output==ROOT/OUTPUT,'Exact new independent result path')
need(plan['source_hashes'].get(PARENT)==PARENT_SHA,'Original independent main pinned')
need('state/dataset_lock.json' not in plan['source_hashes'],'Private LOCK excluded from portable independent map')
""").body
    main=tree.body[0]
    before_binding=[i for i,n in enumerate(main.body) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='binding' for t in n.targets)]
    need(len(before_binding)==1,'Original one run binding')
    main.body[before_binding[0]:before_binding[0]]=checks
    source_try=[n for n in main.body if isinstance(n,ast.Try) and any(isinstance(s,ast.Assign)
        and isinstance(s.value,ast.Call) and isinstance(s.value.func,ast.Attribute) and s.value.func.attr=='closed' for s in n.body)]
    need(len(source_try)==1,'Original actual producer closure guard')
    task_checks=source_try[0].body
    closed_index=[i for i,n in enumerate(task_checks) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
        and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='closed']
    need(len(closed_index)==1,'One actual producer closed task')
    additional=ast.parse("""
need(actual['archive_bodies_downloaded']==actual['metadata_files']==4 and actual['source_only'] is True
    and actual['old_source_QA_repeated'] is False and actual['locked_consumed'] is False
    and actual['funding_unit_certified'] is False and actual['funding_rate_unit']=='UNCONFIRMED'
    and actual['publication_time_certified'] is False and actual['native_market_certified'] is False
    and actual['models_fit']==actual['orders_sent']==actual['GPU']==0,'No source/unit/native/economic promotion')
need(spec['local_non_git_hash_guard']==actual['binding']['local_non_git_hash_guard']
    and spec['local_non_git_hash_guard']=={'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'},'Exact hash-only local LOCK guard')
for path,value in spec['local_non_git_hash_guard'].items():need(sha(ROOT/path)==value,'Private local guard; streaming SHA only')
""").body
    task_checks[closed_index[0]+1:closed_index[0]+1]=additional
    event=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name) and n.func.value.id=='event' and n.func.attr=='update']
    need(len(event)==1,'Original independent event')
    hashes=[k for k in event[0].keywords if k.arg=='source_hashes'];need(len(hashes)==1,'Original event source map')
    hashes[0].value=ast.parse("{str(a.protocol.relative_to(ROOT)):plan['protocol_sha256']}",mode='eval').body
    result_update=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name) and n.func.value.id=='report' and n.func.attr=='update'
        and any(k.arg=='status' for k in n.keywords)]
    need(len(result_update)==1,'Original completed QA report')
    result_update[0].keywords.append(ast.keyword(arg='files',value=ast.parse(
        "[{key:row[key] for key in ('source_id','symbol','month','normalized_path','normalized_sha256','normalized_bytes','rows')} for row in rows]",mode='eval').body))
    ns=dict(vars(parent),__name__='_d047_independent_private',__file__=__file__,PARENT=PARENT,PARENT_SHA=PARENT_SHA,
        CONTRACT=CONTRACT,ACTUAL_STATUS=ACTUAL_STATUS,STATUS=STATUS,FAIL=FAIL,BUDGET=BUDGET,OUTPUT=OUTPUT,
        entries=entries,adapted_audit=adapted_audit,sha=sha)
    exec(compile(ast.fix_missing_locations(tree),'<D047-private-accepted-independent-source-main>','exec'),ns)
    need(parent.BAR==7_200_000_000 and parent.entries()[0]['month']=='2025-07','Original independent globals unchanged')
    return ns

def main():context()['main']()

if __name__=='__main__':main()

"""UNRUN / INCOMPLETE D043 independent source and finance adapter interfaces.

Fixed213D: 2024-01-01 <= minute open < 2024-08-01. This calendar was chosen
after a source defect, before new PnL; it is seen development, not unseen.
No Python, HTTP, raw/Parquet read or economic replay prepared this draft.

Implemented static source helpers: exact72 universe, explicit mixed-owner
receipt membership, original per-file audits, 213 crossmonth checks.
Implemented finance hook: ONLY original window_reader date-map replacement;
original audit_case/financial helpers/HandLedger remain direct references.

NOT IMPLEMENTED / NOT READY: final producer protocol/actual schema bridge,
ACTUAL_BINDING validation, START/RESULT and failure receipt entrypoint;
new213 Donchian signal source selection plus20-case actual orchestration.
The CLI always rejects execution until a separately frozen complete entry
exists. No accepted source, target, financial PASS or future-poison PASS here.
"""
from __future__ import annotations
import ast, gc, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
FORMAT='scripts/investment/audit_perpetual_history_source.py'
FORMAT_SHA='7e333eb672978409bcd6a469ea14998e209edeefb3ced4562dc43cccfc87ee6b'
FINANCE='docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
FINANCE_SHA='1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
HAND='docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA='3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
DONCHIAN_REFERENCE='scripts/investment/audit_perpetual_public_benchmark.py'
DONCHIAN_REFERENCE_SHA='4e30e75cc5add4664bd02aa559af1f9ec31c7c2a3fba80ce7a732530dc5c0b91'
PERIOD=('213D','2024-01-01T00:00:00+00:00','2024-08-01T00:00:00+00:00',213,306720)
LEGACY_OWNER=STATE/'d042-perpetual-history-source-20261003-v1'
LEGACY_FAILED_TASK='c1f09725d84349068d0cfff9327c3033'
TOLERANCES=dict(cash_USDT=1e-7,ratio=1e-10)
READINESS=dict(static_draft=True,executed=False,source_entry_complete=False,financial_entry_complete=False,
    arrays_read=False,HTTP_requests=0,future_perturbation_independently_tested=False,
    full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
    candidate_status='NO_QUALIFIED_CANDIDATE',funding_unit_certified=False,economic_result=None)

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(path,digest,name):
    p=ROOT/path;need(not p.is_symlink() and sha(p)==digest,'Exact frozen independent helper '+path)
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def month_range(first,last):
    year,month=map(int,first.split('-'));end=tuple(map(int,last.split('-')));out=[]
    while (year,month)<=end:
        out.append(f'{year:04d}-{month:02d}');month+=1
        if month==13:year+=1;month=1
    return out

def source_entries():
    result=[]
    for kind,interval,first,last in [('klines','1m','2024-01','2024-07'),('klines','1d','2023-06','2024-07'),
        ('klines','2h','2023-12','2023-12'),('markPriceKlines','1m','2024-01','2024-07'),('fundingRate',None,'2024-01','2024-07')]:
        for symbol in ('BTCUSDT','ETHUSDT'):
            for month in month_range(first,last):
                suffix=f'{symbol}-fundingRate-{month}.zip' if interval is None else f'{interval}/{symbol}-{interval}-{month}.zip'
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
                row=dict(market='futures/um',partition='monthly',kind=kind,symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval is not None:row['interval']=interval
                result.append(row)
    need(len(result)==72,'Fixed14trade +28daily +2twohour +14mark +14fund archives')
    return result

def identity(row):return row['kind'],row['symbol'],row.get('interval'),row['month']

def owner_receipts(g,owner_bindings):
    """Proposed normalized interface: exact2 owners, report SHA and task/code.

    D042 owner remains failed/83, not promoted to a completed accepted source.
    The new213 producer report must really close0. Its sources catalogue may
    include reused paths; membership is filtered by exact bound owner ROOT.
    Each selected item must be byte-bound in both the 72 view and its owner.
    """
    need(len(owner_bindings)==2 and len({r['run_dir'] for r in owner_bindings})==2,'Exactly legacy and new explicit source owners')
    catalogs={};proofs=[]
    for owner in owner_bindings:
        root=Path(owner['run_dir']);need(root.parent==STATE and not root.is_symlink(),'Explicit D-hosted source owner')
        legacy=root==LEGACY_OWNER;code=1 if legacy else 0
        need(owner['exit_code']==code and (not legacy or owner['task_id']==LEGACY_FAILED_TASK),'Honest failed-parent/completed-child task roles')
        value,digest=g.small(g.project(owner['report_path']),owner['report_sha256']);closed=g.closed(owner['task_id'],code)
        need(value['binding']['task_id']==owner['task_id'] and value['status']==owner['required_status'],'Actual owner report/task identity')
        if legacy:need(value['status']=='FAIL_D042_HISTORY_SOURCE' and value['completed_files']==83,'Original full547 failure retained')
        published={}
        for item in value['sources']:
            p=Path(item['receipt_path'])
            if p.parent.parent==root:
                need(str(p) not in published,'No duplicate owner receipt path');published[str(p)]=item
        catalogs[str(root)]=published;proofs.append(dict(**owner,actual_task=closed,actual_report_sha256=digest))
    need(str(LEGACY_OWNER) in catalogs,'Preserved failed547 owner must be explicit')
    return catalogs,proofs

def qa_72(selected_items,owner_bindings,source_spec,results=None,progress=None,check_budget=None):
    """Callable only after future complete entry freezes all metadata/pins.

    There is no producer import/parser, old148 main, old83 replay or repaired
    failed-August file. Each of the selected51 reused +21 new files needs its
    first actual independent raw-to-normalized QA; reusing a failed overall
    report is identity evidence only, not independent acceptance.
    """
    q=load(FORMAT,FORMAT_SHA,'d043_213_original_format');b=q.load(q.TRADE);f=q.load(q.FUND);g=b.guards()
    audit,derivation=q.trade_audit(b);expected={identity(r):r for r in source_entries()}
    need(len(selected_items)==72 and len({identity(r) for r in selected_items})==72
        and {identity(r) for r in selected_items}==set(expected),'All72 exact month selectors without deleted rows/window selection')
    need(source_spec['funding_header']==['calc_time','funding_interval_hours','last_funding_rate']
        and source_spec['price_header']==b.HEADER and source_spec['funding_nominal_interval_tolerance_ms']==1000,
        'Frozen original headers/nominal jitter, no funding-unit upgrade')
    catalogs,owner_proofs=owner_receipts(g,owner_bindings)
    if results is None:results=[]
    need(not results,'Fresh partial-result list');ownership_count={k:0 for k in catalogs}
    for item in selected_items:
        root=Path(item['source_owner_path']);catalog=catalogs.get(str(root))
        need(Path(item['receipt_path']).parent.parent==root and isinstance(item['source_role'],str) and item['source_role'],
            'Explicit mixed-owner alias agrees with exact receipt ROOT and role')
        need(catalog is not None and item['receipt_path'] in catalog,'Only explicit owner-published receipt, no arbitrary data scan')
        origin=catalog[item['receipt_path']]
        for key in ('receipt_sha256','normalized_path','normalized_sha256','normalized_bytes','rows'):
            need(item[key]==origin[key],'View/owner normalized identity bridge '+key)
        entry=expected[identity(item)]
        if progress:progress.update('固定213日72档 · 两来源原值独立核验',len(results),72,'文件',symbol=entry['symbol'],kind=entry['kind'],month=entry['month'])
        result=audit(g,item,entry,root,source_spec) if entry['kind']=='klines' else q.proxy_audit(g,b,f,item,entry,root,source_spec)
        result.update(kind=entry['kind'],interval=entry.get('interval'),symbol=entry['symbol'],month=entry['month'],
            receipt_path=item['receipt_path'],receipt_sha256=item['receipt_sha256'],owner_run_dir=str(root))
        results.append(result);ownership_count[str(root)]+=1;gc.collect()
        if check_budget:check_budget()
    need(ownership_count[str(LEGACY_OWNER)]==51 and sum(ownership_count.values())==72,'Exactly51 preserved-complete files and21 newly needed files')
    cross,totals=crossmonth_213(results,source_spec['funding_nominal_interval_tolerance_ms'])
    return dict(sources=results,actual_archives=72,owner_proofs=owner_proofs,owner_file_counts=ownership_count,
        crossmonth=cross,row_totals=totals,audit_one_derivation=derivation,
        funding_event_count=sum(r['rows'] for r in results if r['kind']=='fundingRate'),
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,economics='NOT_EVALUATED')

def crossmonth_213(rows,tolerance):
    checks=[];totals={}
    for symbol in ('BTCUSDT','ETHUSDT'):
        for kind,interval,count in [('klines','1m',306720),('klines','1d',427),('klines','2h',372),('markPriceKlines','1m',306720)]:
            selected=sorted([r for r in rows if (r['symbol'],r['kind'],r['interval'])==(symbol,kind,interval)],key=lambda r:r['month'])
            need(sum(r['rows'] for r in selected)==count,'Full213 score/complete warmup price calendar')
            joined=all(a['last_close_us']==b['first_open_us'] for a,b in zip(selected,selected[1:])) if kind=='klines' else all(a['last_timestamp_ms']+60000==b['first_timestamp_ms'] for a,b in zip(selected,selected[1:]))
            need(joined,'No crossmonth price gap/overlap');totals[symbol+'_'+kind+'_'+interval]=count
            checks.append(dict(symbol=symbol,kind=kind,interval=interval,rows=count,month_joins=len(selected)-1,passed=True))
        fund=sorted([r for r in rows if r['symbol']==symbol and r['kind']=='fundingRate'],key=lambda r:r['month'])
        need(len(fund)==7,'Every original213 funding month')
        for a,b in zip(fund,fund[1:]):need(any(abs(b['first_timestamp_ms']-a['last_timestamp_ms']-h*3600000)<=tolerance
            for h in (a['last_interval_hours'],b['first_interval_hours'])),'Actual reported funding crossmonth gaps; no8h assumption')
        totals[symbol+'_funding_events']=sum(r['rows'] for r in fund)
        checks.append(dict(symbol=symbol,kind='fundingRate',interval=None,rows=totals[symbol+'_funding_events'],month_joins=6,passed=True))
    return checks,totals

def prepare_financial_adapter():
    """Compile ALL private anchors before any source array; no actual call now."""
    fin=load(FINANCE,FINANCE_SHA,'d043_213_financial_original')
    tree=ast.parse((ROOT/FINANCE).read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='window_reader']
    need(len(nodes)==1,'Unique original financial reader');node=nodes[0];assignments=[n for n in ast.walk(node)
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets)]
    need(len(assignments)==1 and isinstance(assignments[0].value,ast.Subscript) and isinstance(assignments[0].value.value,ast.Dict),'Exact date-map only anchor')
    old=assignments[0].value.value;need([k.value for k in old.keys]==['122D','90D'],'Original accepted date-map shape')
    replacement=ast.parse("{'213D':('2024-01-01T00:00:00+00:00','2024-08-01T00:00:00+00:00',213)}",mode='eval').body
    assignments[0].value.value=replacement;namespace=dict(vars(fin))
    exec(compile(ast.fix_missing_locations(ast.Module([node],type_ignores=[])),'<D043-private-213-financial-reader>','exec'),namespace)
    proof=dict(base_sha256=FINANCE_SHA,only_changed_anchor='window_reader.expected date-map',
        derived_reader_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        audit_case_unchanged_direct_reference=True,HandLedger_sha256=HAND_SHA,tolerances=TOLERANCES)
    return fin,namespace['window_reader'],proof

def financial_case_interface(fin,w,case,g,hand,run,target_expected,target_witness,maximum):
    """One newcase; original financial body handles full/ halted honesty.

    Caller must supply independently rebuilt SMA or Donchian target tables,
    not producer fixed_targets. SMA fin.target_reference is reusable as-is.
    Donchian scalar/reference is reusable; its old July/Aug signal_reader is
    NOT reusable unchanged for Dec2023+Jan-Jul2024 input. Future-poison scope
    belongs to one new true closed target/controller fixture, not this draft.
    """
    need(w['days']==213 and w['count']==306720 and case['period']=='213D','Only exact new213 account')
    need(fin.CASH_TOL==TOLERANCES['cash_USDT'] and fin.RATIO_TOL==TOLERANCES['ratio'],'Original money/ratio tolerance unchanged')
    result=fin.audit_case(w,case,g,hand,run,target_expected,target_witness,maximum)
    gc.collect();return result

if __name__=='__main__':
    raise SystemExit('UNRUN_INCOMPLETE_DRAFT: final source/finance bindings and execution entry have not been frozen; no payload was read')

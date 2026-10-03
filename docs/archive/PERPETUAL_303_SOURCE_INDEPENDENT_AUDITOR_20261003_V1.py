"""UNRUN D045 303D source QA draft: 70 first QA +24 accepted daily reuse.
CLI --protocol independent binding --actual source report --run-dir --output.
Plan: ready_to_execute/checker_sha256/source_spec/actual_source/owner_bindings,
accepted_capabilities[{qa,root}],frozen_sources,budgets. Ref keys:
path,sha256,task_id,required_status; owners also run_dir,exit_code.
No producer parser/main/account import. ROOT must freeze schema/bytes before run.
"""
from __future__ import annotations
import argparse,gc,hashlib,importlib.util,json,os,resource,shlex,subprocess,sys,time
from pathlib import Path
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
FORMAT='scripts/investment/audit_perpetual_history_source.py'
FORMAT_SHA='7e333eb672978409bcd6a469ea14998e209edeefb3ced4562dc43cccfc87ee6b'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
RUN=STATE/'d045-perpetual-303-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_303_SOURCE_INDEPENDENT_20261003_V1.json'
STATUS='PASS_D045_94_SOURCE_COVERAGE_70_FIRST_QA_24_ACCEPTED_REUSE_NOT_UNIT_OR_ECONOMICS'
FAIL='FAIL_D045_303_SOURCE_INDEPENDENT_QA'
BUDGET=dict(peak_RSS_bytes=1_000_000_000,wall_seconds=1200,new_owned_bytes=5_000_000)
CAPABILITIES={
 'reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json':('D043','dc193b2df35dda8dc011895bc9d973946321931f304ad112266b5ccf1f8090ef'),
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_INDEPENDENT_QA_20261003_V2.json':('D040','99d918102e825324d678037d39648081e6aa16fd2c1a1f89cf8a4c11660492fb')}
ROOT_CAPABILITIES={
 'D043':('reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json','795667026b7eb50ab08f1c5b07254eb2002591549b792aa4685439a2d82cc823'),
 'D040':('reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json','f8f6d2e49c320ecc5f61506ffd291ac1c94af0b80803baa6b8e4210741a1f95d')}
def need(ok,why):
    if not bool(ok):raise ValueError(why)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path,digest,name):
    p=ROOT/path;need(not p.is_symlink() and sha(p)==digest,'Exact existing independent helper '+path)
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def months(first,last):
    y,m=map(int,first.split('-'));end=tuple(map(int,last.split('-')));out=[]
    while (y,m)<=end:
        out.append(f'{y:04d}-{m:02d}');m+=1
        if m==13:y+=1;m=1
    return out
def entries():
    out=[]
    for kind,interval,first in [('klines','1m','2024-09'),('klines','1d','2024-02'),('markPriceKlines','1m','2024-09'),('fundingRate',None,'2024-09')]:
        for symbol in ('BTCUSDT','ETHUSDT'):
            for month in months(first,'2025-06'):
                tail=f'{symbol}-fundingRate-{month}.zip' if interval is None else f'{interval}/{symbol}-{interval}-{month}.zip'
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{tail}'
                r=dict(market='futures/um',partition='monthly',kind=kind,symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval:r['interval']=interval
                out.append(r)
    return out
def identity(r):return r.get('kind','klines'),r['symbol'],r.get('interval'),r['month']
def reused(e):return e['kind']=='klines' and e['interval']=='1d' and ('2024-02'<=e['month']<='2024-07' or '2025-01'<=e['month']<='2025-06')
def ref(g,r,code=0):
    v,d=g.small(g.project(r['path']),r['sha256']);need(v['status']==r['required_status'] and v['binding']['task_id']==r['task_id'],'Actual report/status/task')
    return v,d,g.closed(r['task_id'],code)
def capability_rows(g,refs):
    need(len(refs)==2 and {r['qa']['path'] for r in refs}==set(CAPABILITIES),'Only two actual accepted prior capabilities')
    selected={};proofs=[]
    for r in refs:
        tag,digest=CAPABILITIES[r['qa']['path']];need(r['qa']['sha256']==digest and (r['root']['path'],r['root']['sha256'])==ROOT_CAPABILITIES[tag],'Exact prior QA/root bytes')
        qa,_,qt=ref(g,r['qa']);root,_,rt=ref(g,r['root'])
        prior_id=root['roles']['INDEPENDENT']['task']['id'] if tag=='D043' else root['closed_prior_tasks']['independent']['task']['id']
        need(prior_id==r['qa']['task_id'],'Accepted root really binds this QA task')
        for row in qa['sources']:
            key=identity(row)
            eligible=key[0]=='klines' and key[2]=='1d' and ('2024-02'<=key[3]<='2024-07' if tag=='D043' else '2025-01'<=key[3]<='2025-06')
            if eligible:need(key not in selected,'Unique prior QA per selector');selected[key]=(row,r['qa'])
        proofs.append(dict(qa=r['qa'],root=r['root'],QA_task=qt,root_task=rt))
    need(len(selected)==24,'Exactly24 previously independently accepted daily files');return selected,proofs
def owners(g,refs,newroot):
    allowed={str(STATE/n) for n in ('d042-perpetual-history-source-20261003-v1','perpetual-trade-source-actual-20261003-v1')}|{str(newroot)}
    need(len(refs)==3 and {r['run_dir'] for r in refs}==allowed,'Three explicit physical source owners')
    catalogs={};proofs=[]
    for r in refs:
        legacy=r['run_dir']==str(STATE/'d042-perpetual-history-source-20261003-v1');code=1 if legacy else 0
        need(r['exit_code']==code,'Failed547 parent not promoted');v,d,t=ref(g,r,code)
        if legacy:need(v['status']=='FAIL_D042_HISTORY_SOURCE' and v['completed_files']==83,'Preserved actual failed547 scope')
        direct={}
        for row in v['sources']:
            p=Path(row['receipt_path'])
            if str(p.parent.parent)==r['run_dir']:need(str(p) not in direct,'Unique owner receipt');direct[str(p)]=row
        catalogs[r['run_dir']]=direct;proofs.append(dict(**r,actual_task=t))
    return catalogs,proofs
def reuse_one(g,b,item,entry,old,cap,spec,owner):
    job=owner/f"{entry['symbol']}-{entry['interval']}-{entry['month']}";p=Path(item['receipt_path'])
    need(p==job/'receipt.json' and Path(item['normalized_path'])==job/'source.parquet','Exact reused daily paths')
    receipt,_=g.small(p,item['receipt_sha256'])
    need(all(receipt['entry'].get(k)==v for k,v in entry.items()),'Exact prior official entry')
    for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema'):need(item[k]==receipt[k],'Reused receipt aliases '+k)
    for k in ('normalized_path','normalized_sha256','receipt_sha256','rows'):need(item[k]==old[k],'Exact same accepted file '+k)
    need(old['all_raw_normalized_values_equal'] is True and old['full_CSV_EOF_and_CRC_read'] is True
        and old['zip_sha256']==receipt['zip_sha256'] and old['checksum_sha256']==receipt['checksum_sha256'],'Prior exact raw/normalized/CRC capability')
    b.payload(item['normalized_path'],job,item['normalized_sha256'],spec['budgets']['file_write_limit_bytes'],item['normalized_bytes'])
    return dict(old,kind='klines',receipt_path=str(p),owner_run_dir=str(owner),QA_scope='REUSED_ACCEPTED_EXACT_BYTES_NO_ROWS_OR_CRC_REREAD',prior_QA=cap)
def crossmonth(rows,tol):
    checks=[]
    for symbol in ('BTCUSDT','ETHUSDT'):
        for kind,interval,count in [('klines','1m',436320),('klines','1d',516),('markPriceKlines','1m',436320)]:
            r=sorted((x for x in rows if identity(x)[:3]==(kind,symbol,interval)),key=lambda x:x['month'])
            need(sum(x['rows'] for x in r)==count,'Exact303 score or516 warmup+score days')
            joined=all(a['last_close_us']==b['first_open_us'] for a,b in zip(r,r[1:])) if kind=='klines' else all(a['last_timestamp_ms']+60000==b['first_timestamp_ms'] for a,b in zip(r,r[1:]))
            need(joined,'No price crossmonth gap/overlap');checks.append(dict(kind=kind,symbol=symbol,interval=interval,rows=count,month_joins=len(r)-1,passed=True))
        f=sorted((x for x in rows if identity(x)[:2]==('fundingRate',symbol)),key=lambda x:x['month']);need(len(f)==10,'All10 original funding months')
        need(all(any(abs(b['first_timestamp_ms']-a['last_timestamp_ms']-h*3600000)<=tol for h in (a['last_interval_hours'],b['first_interval_hours'])) for a,b in zip(f,f[1:])),'Funding actual reported interval continuity, not assumed8h')
        checks.append(dict(kind='fundingRate',symbol=symbol,interval=None,rows=sum(x['rows'] for x in f),month_joins=9,passed=True))
    return checks
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('protocol','actual','run-dir','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.protocol=a.protocol.absolute();a.actual=a.actual.absolute();a.run_dir=a.run_dir.absolute();a.output=a.output.absolute()
    g=load(GUARD,GUARD_SHA,'d045_guards');q=load(FORMAT,FORMAT_SHA,'d045_format');b=q.load(q.TRADE);f=q.load(q.FUND)
    need(a.protocol.parent==ROOT/'protocols' and a.actual.parent==ROOT/'reports/fast_research' and a.run_dir==RUN and RUN.is_dir() and not RUN.is_symlink() and {x.name for x in RUN.iterdir()}=={'ACTUAL_BINDING.json'} and a.output==OUT and not OUT.exists(),'Exclusive manifest-only audit paths')
    plan,ph=g.small(a.protocol);local,lh=g.small(RUN/'ACTUAL_BINDING.json');own=sha(__file__);task=os.environ.get('COIN_TASK_ID')
    need(plan==local and ph==lh and plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['budgets']==BUDGET,'Exact ready ROOT byte-binding')
    need(task and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean CPU2 actual task')
    binding=dict(task_id=task,checker_sha256=own,ACTUAL_BINDING_sha256=lh,protocol_sha256=ph,source_hashes=plan['frozen_sources'],actual_reports={str(a.actual):plan['actual_source']['sha256']},exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(RUN/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];progress=None;error=None;fresh=0;reused_count=0
    report=dict(status=FAIL,binding=binding,run_dir=str(RUN),run_binding_sha256=sha(RUN/'RUN_BINDING.json'),independent_source_sha256=own,sources=rows,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_time_certified=False,native_market_certified=False,economics='NOT_EVALUATED',candidate='NO_QUALIFIED_CANDIDATE',locked_consumed=False,old_QA_repeated=False)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D045-303-SOURCE-INDEPENDENT-V1',event_id=task+':START',event_type='INDEPENDENT_SOURCE_START',git_commit=binding['git_commit'],data_manifest_hash=plan['actual_source']['sha256'],protocol_hash=ph,feature_set='70_FIRST_QA_24_ACCEPTED_DAILY_REUSE',labels='NONE',model_family='NONE',success_failure='START_BEFORE_SOURCE_READ',thresholds=BUDGET,source_hashes=plan['frozen_sources'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    def budget():need(time.monotonic()-started<=1200 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Frozen1200s/RSS1GB')
    try:
        g.bounded(before)
        for name,digest in plan['frozen_sources'].items():
            path=g.project(name)
            if name=='state/dataset_lock.json':need(sha(path)==digest,'Private lock hash-only, no body')
            else:g.small(path,digest,False)
        need(plan['frozen_sources'].get(FORMAT)==FORMAT_SHA and plan['frozen_sources'].get(GUARD)==GUARD_SHA and plan['frozen_sources'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own and all(plan['frozen_sources'].get(k)==v for k,v in q.PINS.items()),'Own/guard/all original format imports pinned')
        sr=plan['source_spec'];spec,sph=g.small(g.project(sr['path']),sr['sha256']);need(spec['contract_id']==sr['required_contract'] and spec['score_period_start']=='2024-09-01' and spec['score_period_end_exclusive']=='2025-07-01' and spec['funding_rate_unit']=='UNCONFIRMED' and spec['funding_unit_certified'] is False and spec['economic_scope']=='NOT_EVALUATED','Exact303 source-only dates/unit scope')
        expected={identity(e):e for e in entries()};need(len(expected)==94 and len(spec['entries'])==94 and len({identity(e) for e in spec['entries']})==94 and all(identity(e) in expected and all(e.get(k)==v for k,v in expected[identity(e)].items()) for e in spec['entries']),'Exact94 official selectors, no2h/index/Aug score')
        need(spec['funding_header']==['calc_time','funding_interval_hours','last_funding_rate'] and spec['price_header']==b.HEADER and spec['funding_nominal_interval_tolerance_ms']==1000,'Original headers and interval tolerance')
        ar=plan['actual_source'];need(a.actual==ROOT/ar['path'],'Exact actual source report');actual,ah,at=ref(g,ar)
        need(actual['completed_files']==actual['required_files']==94 and len(actual['sources'])==94 and actual['binding']['protocol_sha256']==sph and actual['binding']['source_hashes']==spec['frozen_sources'],'True complete94 and immutable source dependencies')
        need(actual['funding_rate_unit']=='UNCONFIRMED' and actual['funding_unit_certified'] is False and not actual['locked_consumed'] and actual['models_fit']==actual['orders_sent']==actual['GPU']==0,'No research/unit promotion')
        newroot=Path(spec['run_dir']);need(newroot.parent==STATE and newroot.name.startswith('d045-'),'Dedicated new source owner')
        rb,rh=g.small(newroot/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual source RUN_BINDING')
        catalogs,op=owners(g,plan['owner_bindings'],newroot);accepted,cp=capability_rows(g,plan['accepted_capabilities'])
        need(len({identity(i) for i in actual['sources']})==94 and {identity(i) for i in actual['sources']}==set(expected),'All94 source aliases exactly once')
        need(all(plan['frozen_sources'].get(k)==v for k,v in spec['frozen_sources'].items()),'All producer source imports pinned in audit')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(94)
        for item in actual['sources']:
            key=identity(item);entry=expected[key];owner=Path(item['source_owner_path']);catalog=catalogs.get(str(owner));need(catalog is not None and item['receipt_path'] in catalog and Path(item['receipt_path']).parent.parent==owner and item['source_role'],'Explicit published mixed-owner membership')
            origin=catalog[item['receipt_path']]
            if 'entry' not in origin:
                need(owner==STATE/'perpetual-trade-source-actual-20261003-v1' and 'kind' not in origin,'Only exact legacy trade report omits entry/kind')
                receipt,_=g.small(Path(origin['receipt_path']),origin['receipt_sha256'])
                need(receipt['status']=='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY' and receipt['entry']['kind']=='klines'
                    and all(receipt['entry'][k]==origin[k] for k in ('symbol','interval','month')),'Legacy receipt exact trade identity')
                for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema'):need(receipt[k]==origin[k],'Legacy report/receipt exact alias '+k)
                origin=dict(origin,entry=receipt['entry'],kind='klines')
            for k in ('kind','symbol','interval','month','entry','receipt_sha256','normalized_path','normalized_sha256','normalized_bytes','rows'):need(item[k]==origin[k],'Exact view/owner alias '+k)
            progress.update('303日94档 · 首次QA与已接受能力复用',len(rows),94,'文件',kind=entry['kind'],symbol=entry['symbol'],month=entry['month'])
            if reused(entry):old,cap=accepted[key];result=reuse_one(g,b,item,entry,old,cap,spec,owner);reused_count+=1
            else:
                result=b.audit_one(g,item,entry,owner,spec) if entry['kind']=='klines' else q.proxy_audit(g,b,f,item,entry,owner,spec)
                result['QA_scope']='FIRST_INDEPENDENT_RAW_NORMALIZED_EOF_CRC';fresh+=1
            result.update(kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],interval=entry.get('interval'),receipt_path=item['receipt_path'],receipt_sha256=item['receipt_sha256'],owner_run_dir=str(owner));rows.append(result);gc.collect();budget()
        cross=crossmonth(rows,spec['funding_nominal_interval_tolerance_ms']);need(fresh==70 and reused_count==24 and sum(r['rows'] for r in rows)==actual['actual_source_rows'],'Exact70 first +24 accepted and actual counts')
        for name,digest in plan['frozen_sources'].items():need(sha(g.project(name))==digest,'Source bytes unchanged after QA')
        report.update(status=STATUS,actual_archives=94,completed_files_verified=94,first_independent_QA_files=fresh,reused_accepted_QA_files=reused_count,actual_report_sha256=ah,protocol_sha256=sph,independent_protocol_sha256=ph,actual_task=at,actual_run_binding_sha256=rh,owner_proofs=op,accepted_capability_proofs=cp,verified_source_hashes=plan['frozen_sources'],crossmonth=cross,funding_event_count=sum(r['rows'] for r in rows if r['kind']=='fundingRate'),price_rows=sum(r['rows'] for r in rows if r['kind']!='fundingRate'),completed_rows_verified=sum(r['rows'] for r in rows),current_reused_normalized_bytes_sha_verified=True,reused_raw_or_Parquet_rows_reread=False)
    except Exception as e:error=e;report['failure']=dict(type=type(e).__name__,reason=str(e))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_files_verified=len(rows),actual_archives=len(rows),first_independent_QA_files=fresh,reused_accepted_QA_files=reused_count,elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after']);budget()
        except Exception as e:error=error or e;report['budget_error']=str(e)
        if error:report['status']=FAIL
        digest,size=g.write(OUT,report);need(sum(p.stat().st_size for p in RUN.iterdir() if p.is_file())+size<=5_000_000,'Own metadata5MB')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='INDEPENDENT_SOURCE_RESULT',success_failure=report['status'],artifact_path=OUT.relative_to(ROOT).as_posix(),artifact_sha256=digest));print(json.dumps(dict(status=report['status'],sha256=digest,task_id=task)),flush=True)
    if error:raise error
if __name__=='__main__':main()

"""Two fixed settlement-correction accounts; reuse the frozen independent math.

No original thirty-account replay, account/controller finance import, new fee
band, strategy parameter, source QA or rate-unit certification. The original
false-halt prefixes remain evidence and are never spliced into the new accounts.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, importlib.util, json, os, resource, sys, time
from pathlib import Path
import polars as pl
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
BASE='docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
BASE_SHA='1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
ORIGINAL_ACCOUNT_SHA='2bae17b6351dec5c632e3af42fed2a6a5cf91293dba0a08c06a7aa81f4df58fb'
ORIGINAL_REPORT_SHA='c643c6ae5542dc049595a8c2e21b7281ef5ce46ac7f026a3c845126f05bfb445'
ORIGINAL_AUDIT_SHA='876fce2558757f797e1d0f9d5b923c5858427ecfd721926afe4926355ffef53d'
SELECTORS=['90D_SHORT_ONLY_BASE27_RAW_AS_PERCENT','90D_LONG_SHORT_BASE27_RAW_AS_PERCENT']
ACTUAL_STATUS='COMPLETE_TWO_EXACT_SETTLEMENT_CORRECTNESS_REPLAYS_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS='PASS_TWO_EXACT_SETTLEMENT_REPLAYS_INDEPENDENT_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def base_module():
    p=ROOT/BASE;need(sha(p)==BASE_SHA and not p.is_symlink(),'Frozen accepted independent math')
    spec=importlib.util.spec_from_file_location('perpetual_recovery_independent_math',p)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def account_patch(g,spec):
    old=spec['preserved_original_account'];need(old['sha256']==ORIGINAL_ACCOUNT_SHA,'Exact retained pre-fix account')
    old_path=g.project(old['path']);g.small(old_path,old['sha256'],False)
    new_path=g.project('src/quant/perpetual_account.py');g.small(new_path,spec['frozen_sources']['src/quant/perpetual_account.py'],False)
    need(sha(new_path)!=ORIGINAL_ACCOUNT_SHA,'Actual exact-settlement account source changed')
    trees=[ast.parse(p.read_bytes()) for p in (old_path,new_path)]
    for tree in trees:
        account=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='USDTLinearPerpetualAccount')
        masked=[]
        for n in account.body:
            if isinstance(n,ast.FunctionDef) and n.name in ('_debit','_leg'):
                masked.append(n.name);n.body=[ast.Pass()]
        need(sorted(masked)==['_debit','_leg'],'Both exact permitted settlement methods')
    need(ast.dump(trees[0],include_attributes=False)==ast.dump(trees[1],include_attributes=False),'Account AST unchanged outside two settlement methods')
    return dict(old_sha256=old['sha256'],new_sha256=sha(new_path),only_permitted_methods=['_debit','_leg'])

def prefix_proof(b,w,new,old,new_run,old_run):
    stop=int(old['summary']['stop_us']);proof=dict(original_stop_us=stop,scope='STRICTLY_BEFORE_ORIGINAL_FALSE_HALT_NO_PREFIX_SPLICING')
    money_keys={'fee_amount','fee_USDT_mid','realized_PnL','cash_delta','margin_allocated','margin_released',
        'free_cash_delta','isolated_balance_delta','execution_cost','signed_funding_USDT','unpaid_liability'}
    for name in ('trades.json','funding.json'):
        left=b.payload(old['artifacts'][name],old_run);right=b.payload(new['artifacts'][name],new_run)
        a=[r for r in json.loads(left.read_bytes()) if r['event_us']<stop]
        c=[r for r in json.loads(right.read_bytes()) if r['event_us']<stop]
        need(len(a)==len(c),'Same pre-stop journal row count '+name);largest=b.Z
        for before,after in zip(a,c,strict=True):
            need(before.keys()==after.keys(),'Same pre-stop journal schema '+name)
            for key in before:
                if key=='decimal_strings':
                    need(before[key].keys()==after[key].keys(),'Same pre-stop exact amount metadata')
                    for field in before[key]:
                        if field not in money_keys:need(b.dec(before[key][field])==b.dec(after[key][field]),'Exact pre-stop quantity/price/rate '+field)
                elif key in money_keys:
                    error=abs(b.exact(before,key)-b.exact(after,key));largest=max(largest,error)
                    need(error<=b.dec(b.CASH_TOL),'Original fixed money tolerance before correction '+key)
                else:need(before[key]==after[key],'Exact pre-stop time/side/quantity/price/ownership/policy '+key)
        proof[name]=dict(exact_policy_quantity_price_and_rate_values=True,money_tolerance_USDT=b.CASH_TOL,
            maximum_money_difference_USDT=float(largest),rows=len(a),original_sha256=sha(left),new_sha256=sha(right))
    for name,column in [('targets.parquet',None),('minute_nav_inventory.parquet','close_us')]:
        left=b.payload(old['artifacts'][name],old_run);right=b.payload(new['artifacts'][name],new_run)
        a=pl.read_parquet(left);c=pl.read_parquet(right)
        if column:a=a.filter(pl.col(column)<stop);c=c.filter(pl.col(column)<stop)
        need(a.schema==c.schema and a.height==c.height,'Same prefix calendar/schema '+name)
        if column:
            need(a['close_us'].equals(c['close_us']),'Exact minute prefix clock');errors=dict(cash=0.,ratio=0.)
            for field in a.columns:
                if field=='close_us':continue
                if field.endswith('_quantity'):need(a[field].equals(c[field]),'Exact prefix signed quantity')
                else:b.same(a[field],c[field],'Original prefix snapshot '+field,errors,b.RATIO_TOL if 'weight' in field else b.CASH_TOL)
            proof[name]=dict(exact_clock_and_quantity=True,maximum_errors=errors,tolerances=dict(cash_USDT=b.CASH_TOL,ratio=b.RATIO_TOL),
                rows=a.height,original_sha256=sha(left),new_sha256=sha(right))
        else:
            need(a.equals(c),'Exact original target signal values/calendar')
            proof[name]=dict(exact_logical_values=True,rows=a.height,original_sha256=sha(left),new_sha256=sha(right))
    return proof

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();b=base_module();g=b.module(b.GUARD,'perpetual_recovery_guards',b.GUARD_SHA)
    hand=b.module(b.REFERENCE,'perpetual_recovery_hand',b.REFERENCE_SHA)
    need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean CPU2 actual task')
    need(a.run_dir.parent==STATE and a.run_dir.is_dir() and not a.run_dir.is_symlink()
        and {n.name for n in a.run_dir.iterdir()}=={'ACTUAL_BINDING.json'} and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Fresh frozen two-case audit paths')
    plan,plan_sha=g.small(a.run_dir/'ACTUAL_BINDING.json');own=sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['protocol_path']==str(a.protocol.relative_to(ROOT))
        and plan['actual_report']==str(a.actual.relative_to(ROOT)),'Exact prebound invocation')
    need(plan['tolerances']==dict(cash_USDT=b.CASH_TOL,ratio=b.RATIO_TOL)
        and plan['budgets']==dict(wall_seconds=1200,peak_RSS_bytes=1500000000,new_owned_bytes=5000000),'Unchanged money/ratio tolerances and fixed audit budget')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(a.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'])
    g.write(a.run_dir/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];maximum=dict(cash=0.,ratio=0.)
    report=dict(status='FAIL_TWO_EXACT_SETTLEMENT_REPLAYS_INDEPENDENT_AUDIT',binding=binding,run_dir=str(a.run_dir),
        run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),independent_source_sha256=own,cases=rows,
        tolerances=plan['tolerances'],maximum_errors=maximum,original_other_thirty_financial_cases_replayed=False,
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,long_term_APR='NOT_EVALUABLE',
        candidate='NO_QUALIFIED_CANDIDATE',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
        financial_method='EXACT_FROZEN_1C4B_INDEPENDENT_DECIMAL_AND_NUMPY_FUNCTION_REUSE_TWO_NEW_ACCOUNTS_ONLY')
    error=None;progress=None
    try:
        g.bounded(before);spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']=='USDM_EXACT_SETTLEMENT_TWO_FALSE_HALTS_20261003_V1' and spec['selectors']==SELECTORS
            and actual['status']==ACTUAL_STATUS and actual['required_cases']==actual['completed_cases']==2
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'],'Only original two fixed false-halt selectors')
        report['actual_task']=g.closed(plan['actual_task_id']);run=Path(spec['run_dir'])
        rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual producer RUN_BINDING')
        hashes={str(a.protocol.relative_to(ROOT)):proto_sha,str(a.actual.relative_to(ROOT)):actual_sha}
        need(plan['source_hashes'].get(BASE)==BASE_SHA and plan['source_hashes'].get(b.GUARD)==b.GUARD_SHA
            and plan['source_hashes'].get(b.REFERENCE)==b.REFERENCE_SHA,'All frozen independent functions explicitly bound')
        for name,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(name not in hashes or hashes[name]==digest,'No conflicting source pins');g.small(b.project(g,name),digest,False);hashes[name]=digest
        original_ref=spec['original_report'];need(original_ref==spec['original_actual'] and original_ref['sha256']==ORIGINAL_REPORT_SHA,'Exact original report alias')
        original,_=g.small(g.project(original_ref['path']),original_ref['sha256']);report['original_actual_task']=g.closed(original['binding']['task_id'])
        original_audit_ref=spec['original_audit'];need(original_audit_ref==spec['original_independent'] and original_audit_ref['sha256']==ORIGINAL_AUDIT_SHA,'Exact original audit alias')
        old_audit,_=g.small(g.project(original_audit_ref['path']),original_audit_ref['sha256']);report['original_independent_task']=g.closed(old_audit['binding']['task_id'])
        need(old_audit['status']==b.STATUS and old_audit['completed_cases_verified']==32 and old_audit['completed_full_calendar_cases_verified']==30
            and spec['rules']==original['binding']['rules'] and spec['cost']==dict(id='BASE27',half_spread_bps=4,slippage_bps=4,roundtrip_bps=27)
            and spec['unit']==dict(id='RAW_AS_PERCENT',scale=.01),'No strategy/cost/unit or risk-parameter experiment')
        report['account_patch_scope']=account_patch(g,spec)
        old_cases={c['id']:c for c in original['cases'] if c['id'] in SELECTORS}
        need(len(old_cases)==2 and all(c['summary']['halt_witness']['decimal_strings']['unpaid_liability']=='1.000E-37'
            and c['summary']['free_cash']>9000 for c in old_cases.values()),'The exact two preserved numerical false halts')
        smoke_ref=spec['required_smoke_receipt'];need(smoke_ref==spec['required_settlement_test'],'Exact settlement-case receipt alias')
        smoke,_=g.small(g.project(smoke_ref['path']),smoke_ref['sha256']);need(smoke['status']==smoke_ref['required_status']
            and smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True,'New exact-settlement case completed successfully')
        report['synthetic_task']=g.closed(smoke['binding']['task_id'])
        mref=spec['input_manifest'];manifest,_=g.small(g.project(mref['path']),mref['sha256'])
        old_input_ref=ROOT/'protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json'
        old_spec,_=g.small(old_input_ref,original['binding']['protocol_sha256']);need(mref==old_spec['input_manifest'],'Same original immutable economic inputs')
        source_ref=spec['trade_source_acceptance'];need(source_ref==old_spec['trade_source_acceptance'],'Same accepted new trade source, no repeat QA')
        source,_=g.small(g.project(source_ref['path']),source_ref['sha256']);need(source['status']==source_ref['required_status'],'Retained source acceptance')
        need([c['id'] for c in actual['cases']]==SELECTORS and len(actual['input_windows'])==1,'Exactly two new accounts and one shared input window')
        w=b.window_reader(manifest,next(w for w in manifest['windows'] if w['id']=='90D'))
        need(actual['input_windows'][0]['id']=='90D' and actual['input_windows'][0]['input_proofs']==w['proofs'],'Exact once-read accepted economic inputs')
        old_window=next(x for x in original['input_windows'] if x['id']=='90D');need(actual['input_windows'][0]==old_window,'Old/new shared source calendars and hashes unchanged')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(2);old_run=Path(old_spec['run_dir'])
        for case in actual['cases']:
            progress.update('仅两项数值停止修复 · 独立资金与全分钟',len(rows),2,'账户',selector=case['id'])
            target,witness=b.target_reference(w,case['mode']);item=b.audit_case(w,case,g,hand,run,target,witness,maximum)
            need(item['complete_calendar_verified'] and item['completed_minutes_verified']==129600 and item['completed_days_verified']==90
                and item['completed_months_verified']==3 and b.exact(case['summary'],'unpaid_liability')==0
                and case['summary']['halt_witness'] is None and item['actual_terminal_marked_notional']==0
                and all(b.exact(v,'quantity')==0 for v in case['summary']['positions'].values()),'Genuine complete full calendar, exact zero debt/position and no halt')
            item['original_prefix_equivalence']=prefix_proof(b,w,case,old_cases[case['id']],run,old_run);rows.append(item);gc.collect()
        for name,digest in hashes.items():g.small(b.project(g,name),digest,False)
        report.update(status=STATUS,verified_source_hashes=hashes,actual_report_sha256=actual_sha,actual_run_binding_sha256=rb_sha,
            original_report_sha256=ORIGINAL_REPORT_SHA,original_independent_sha256=ORIGINAL_AUDIT_SHA,
            required_cases=2,completed_cases_verified=2,completed_full_calendar_cases_verified=2,incomplete_or_halted_cases_verified=0,
            original_other_thirty_verified_scope_referenced=30,NOT_SINGLE_FRESH_32_SUITE=True)
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_cases_verified=len(rows),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status(),
            own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if report['elapsed_seconds']>1200 or report['peak_RSS_bytes']>1500000000:error=error or RuntimeError('Fixed recovery audit process budget')
        if error:report['status']='FAIL_TWO_EXACT_SETTLEMENT_REPLAYS_INDEPENDENT_AUDIT'
        digest,size=g.write(a.output,report);need(sum(p.stat().st_size for p in a.run_dir.iterdir() if p.is_file())+size<=5000000,'Only small recovery metadata outputs')
        print(json.dumps(dict(status=report['status'],sha256=digest,completed_cases=len(rows))),flush=True)
    if error:raise error

if __name__=='__main__':main()

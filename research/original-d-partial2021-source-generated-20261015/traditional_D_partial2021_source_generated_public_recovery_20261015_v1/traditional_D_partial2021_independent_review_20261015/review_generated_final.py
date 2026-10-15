"""Independent clearly fake-origin same-input D/native financial equivalence."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{4})
import sys,json,time,resource,unittest,tempfile,ast
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from decimal import Decimal as Q
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
for directory in ('traditional_D_partial2021_20261015','traditional_three_tier_freeze_20261015','bounded_native_continuation_guard50_exit_expansion_20261015'):
    sys.path.insert(0,str(ROOT/directory))
import numpy as np
import partial_d as d
import partial_entry as entry
import run_partial as runner
import expansion as old
from test_native_runtime import fixture,BASE
from saved_native_reconciliation import reconcile_saved_native

def account(tier='MID'):
    plain=d.V2.grid.make_account(tier,'BASE27')
    return d.ExpansionAccount(plain.config,symbols=d.S,instrument_profiles=plain.instrument_profiles,
        generated_scope=d.GENERATED,tier_name=tier)
def marks(a,at,price=None):
    return a.update_marks(at,{s:dict(price=str(price if s=='BTCUSDT' and price is not None else BASE[j]),close_us=at,available_us=at) for j,s in enumerate(d.S)})
def fill(a,at=0):
    event=at+d.MINUTE+1;marks(a,event-1)
    return a.execute_fill('BTCUSDT','SELL','.02',event,at,'GENERATED_INITIAL',execution_mid_price='50000',quote_available_us=event-1,available_quantity='.02')
def financial_snapshot(a):
    snap=d.V2.OWNED.export_tree(a.snapshot())
    assert snap['version'] in (d.VERSION,old.VERSION,d.D.VERSION)
    snap.pop('version')
    assert snap['contract']['version'] in (d.VERSION,old.VERSION,d.D.VERSION)
    snap['contract'].pop('version')
    for key in ('continuation_policy','partial_DEV','partial_return_annualized','annual_wallets_compounded'):
        snap.pop(key,None)
    # Only declared new partial-calendar metadata is excluded, recursively in
    # the engine contract. All financial states, ledgers and no-op hashes stay.
    def scrub(v):
        if isinstance(v,dict):
            return {k:scrub(x) for k,x in v.items() if k not in ('integration_version','continuation_policy','partial_DEV','partial_return_annualized','annual_wallets_compounded')}
        if isinstance(v,list):return [scrub(x) for x in v]
        return v
    return scrub(snap)
def export(a):return d.V2.OWNED.export_tree(a.snapshot())
def run(sim):
    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()

class GeneratedReview(unittest.TestCase):
    def test_historical_genesis_and_whole_constructor_AST_equal_except_reviewed_entry_import(self):
        before=ast.parse((old.HERE/'expansion.py').read_text())
        after=ast.parse((d.HERE/'partial_d.py').read_text())
        class RenameEntry(ast.NodeTransformer):
            def visit_ImportFrom(self,node):
                if node.module=='expansion_entry':node.module='partial_entry'
                return node
        before=RenameEntry().visit(before)
        def method(tree):
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExpansionAccount')
            return next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        self.assertEqual(ast.dump(method(before)),ast.dump(method(after)))
        def constructor(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='construct_case')
        self.assertEqual(ast.dump(constructor(before)),ast.dump(constructor(after)))
    def test_new_adapter_preserves_frozen_D_code_objects(self):
        for method in ('monitor','_transfer','execute_fill','apply_funding','update_marks'):
            self.assertIs(getattr(d.ExpansionAccount,method),getattr(d.D.Guard50ExitAccount,method))
        self.assertIs(d.ExpansionAccount._leg,d.V2.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(d.ContinuationGuard.schedule.__code__,old.ContinuationGuard.schedule.__code__)
        self.assertIs(d.ContinuationGuard._frozen_attempt.__code__,old.ContinuationGuard._frozen_attempt.__code__)
        self.assertIs(d.ContinuationGuard.attempt,old.ContinuationGuard.attempt)
    def test_all_tiers_whole_same_input_D_financial_states_ledgers_and_minutes_exact(self):
        for tier in d.TIERS:
            with self.subTest(tier=tier):
                w,rows,decisions=fixture(1);weights=np.full((1,5),.03)
                baseline,bg=old.construct_case(w,rows,decisions,weights,tier_name=tier,generated_scope=old.GENERATED)
                new,ng=d.construct_case(w,rows,decisions,weights,tier_name=tier,generated_scope=d.GENERATED)
                for sim in (baseline,new):run(sim)
                self.assertEqual(financial_snapshot(baseline.account),financial_snapshot(new.account))
                self.assertEqual(baseline.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes())
                self.assertEqual(bg.receipts,ng.receipts)
                result=d.case_result(new,ng)
                self.assertTrue(result['economics']['paid_flat']);self.assertFalse(result['economics']['partial_return_annualized'])
                self.assertFalse(new.account.transfer_journal);self.assertFalse(new.account.settlement_journal)
                first=min(t['event_us'] for t in new.account.trades)
                self.assertGreaterEqual(first,new.start+d.MINUTE+1)
                terminal=[t for t in new.account.trades if t['signal_us']==new.end-61*d.MINUTE and t['leg']=='CLOSE']
                self.assertTrue(terminal)
                self.assertTrue(all(new.end-60*d.MINUTE+1<=t['event_us']<=new.end-d.MINUTE+1 for t in terminal))
                result.pop('minute');result['targets']=result['targets'].to_dicts()
                proof=reconcile_saved_native(export(new.account),d.V2.OWNED.export_tree(result),expected_continuation_version=d.VERSION)
                self.assertTrue(proof['passed']);self.assertFalse(proof['tolerance_or_epsilon_used'])
    def test_warning_and_unknown_quality_paths_match_frozen_D_in_all_tiers(self):
        for tier in d.TIERS:
            plain=d.V2.grid.make_account(tier,'BASE27')
            baseline=d.D.Guard50ExitAccount(plain.config,symbols=d.S,instrument_profiles=plain.instrument_profiles,generated_scope=d.GENERATED)
            new=account(tier)
            for a in (baseline,new):
                fill(a);at=2*d.MINUTE;a._quality_intervals=((at,at+d.MINUTE,d.S),)
                marks(a,at,75000);a.monitor('MONITOR:'+str(at),at)
                self.assertFalse(a.pending_exits);self.assertFalse(a.can_increase(at))
                marks(a,at+d.MINUTE,75000);a.monitor('MONITOR:'+str(at+d.MINUTE),at+d.MINUTE)
                self.assertIn('BTCUSDT',a.pending_exits);self.assertFalse(a.transfer_journal)
                with self.assertRaises(ValueError):a._transfer('BTCUSDT',Q(1),at,'GENERATED_FORBIDDEN')
                with self.assertRaises(NotImplementedError):a.from_snapshot({})
            # Frozen D has no nominal-tier metadata. Compare complete native
            # histories plus warning state directly, excluding only metadata.
            sa,sb=financial_snapshot(baseline),financial_snapshot(new)
            for value in (sa,sb):
                value.pop('bound_nominal_tier',None);value.pop('adaptive_DEV_only',None);value.pop('frozen_D_rule_SHA256',None)
                if isinstance(value.get('contract'),dict):
                    for key in ('bound_nominal_tier','adaptive_DEV_only','frozen_D_rule_SHA256','nominal_tier_is_not_exact_realized_risk_matching'):value['contract'].pop(key,None)
            # The new metadata can appear under contract_metadata; all core
            # financial fields, ledgers and warning actions must match.
            for key in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','financial_ledger','monitor_journal','settlement_journal','pending_exits','mode_journal','noop_rolling_SHA256'):
                self.assertEqual(sa[key],sb[key],(tier,key))
    def test_whole_sameclock_funding_batch_before_warning(self):
        w,rows,decisions=fixture(1);sim,guard=d.construct_case(w,rows,decisions,np.zeros((1,5)),tier_name='HIGH',generated_scope=d.GENERATED)
        a=sim.account;fill(a,sim.start);at=sim.start+2*d.MINUTE;marks(a,at,75000)
        sim.window['events']=[dict(symbol=s,event_us=at,raw_rate=.0001,reported_interval_hours=8.) for s in d.S]
        seen=[];original=a.apply_funding
        def funded(*args,**kwargs):seen.append((args[0],bool(a.pending_exits)));return original(*args,**kwargs)
        a.apply_funding=funded;sim.funding_through(at,True)
        self.assertEqual(len(seen),5);self.assertFalse(any(flag for _,flag in seen))
        self.assertEqual(sim.pending['BTCUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at)
    def test_all_32_corners_and_preview_callback_isolation(self):
        w,rows,decisions=fixture(1);signal=int(decisions[0]);binding=d.V2.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        for tier in d.TIERS:
            a=account(tier);marks(a,signal);before=a.preview_state_token()
            target={s:a._floor(s,Q(100)/Q(str(BASE[j]))) for j,s in enumerate(d.S)}
            oracle=d.fresh_preview(a,tier_name=tier,binding=binding,prices={s:Q(str(BASE[j])) for j,s in enumerate(d.S)},
                price_available_us=dict.fromkeys(d.S,signal+d.MINUTE),pending=target,capacity=dict.fromkeys(d.S,Q(100000)),
                event_us=signal+d.MINUTE+1,signal_us=signal,quote_available_us=signal+d.MINUTE)
            result=oracle.evaluate(target,Q(1));self.assertTrue(result['allowed']);self.assertEqual(len(result['corners_checked']),32)
            self.assertTrue(d.V2.native._exact_tree_equal(before,a.preview_state_token()))
            clone=a.fork_for_preview();self.assertIsNone(clone.liquidation_callback)
            clone.pending_exits['BTCUSDT']=dict(signal_us=signal,reason='GENERATED');self.assertFalse(a.pending_exits)
    def test_native40_raw100_residual_and_corrupted_finance_fail_closed(self):
        a=account()
        for k,(side,quantity,mid) in enumerate((('BUY','.003','10001'),('BUY','.002','10003'),('BUY','.002','10007'),('SELL','.001','10009'),('BUY','.015','10011'))):
            signal=k*3*d.MINUTE;event=signal+d.MINUTE+1;marks(a,event-1)
            a.execute_fill('BTCUSDT',side,quantity,event,signal,'GENERATED_ROUND:'+str(k),execution_mid_price=mid,quote_available_us=event-1,available_quantity=quantity)
        audit=export(a);proof=reconcile_saved_native(audit,expected_continuation_version=d.VERSION)
        self.assertTrue(proof['passed']);self.assertFalse(proof['tolerance_or_epsilon_used'])
        self.assertTrue(any(Q(x)!=0 for x in proof['raw_precision100_stored_delta_terminal_residuals']['isolated'].values()))
        for kind in ('cash','margin','sequence','leg'):
            bad=deepcopy(audit)
            if kind=='cash':bad['financial_ledger'][0]['free_cash_after']='9000'
            elif kind=='margin':bad['financial_ledger'][0]['isolated_delta']['BTCUSDT']='999.2000000000000000000000000000000001'
            elif kind=='sequence':bad['financial_ledger'][0]['sequence']=2
            else:bad['trades'][0]['leg']='CLOSE'
            with self.subTest(kind=kind),self.assertRaises(ValueError):reconcile_saved_native(bad)
    def test_false_paid_flat_rejected_and_generated_saved_risk_path_works(self):
        w,rows,decisions=fixture(1);sim,guard=d.construct_case(w,rows,decisions,np.full((1,5),.03),generated_scope=d.GENERATED)
        run(sim);result=d.case_result(sim,guard);audit=export(sim.account)
        self.assertEqual(runner.classify_terminal(audit,result,calendar=[sim.start,sim.end],completed_minutes=1440,stop_us=None),'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')
        bad=deepcopy(result);bad['economics']['paid_flat']=False
        with self.assertRaises(ValueError):runner.classify_terminal(audit,bad,calendar=[sim.start,sim.end],completed_minutes=1440,stop_us=None)
        values=result['minute'].to_numpy();columns=result['minute'].columns
        cov=np.asarray([np.eye(5)*.01]);targets=np.full((1,5),.03)
        risk=runner.held_risk_report(values,columns,decisions,cov,targets,'MID',guard.receipts)
        with tempfile.TemporaryDirectory(prefix='generated_risk_review_') as tmp:
            p=Path(tmp);(p/'1900').mkdir();np.savez_compressed(p/'MINUTE.npz',values=values,columns=np.asarray(columns))
            np.savez_compressed(p/'1900/TARGETS.npz',decision_us=decisions,annual_covariance=cov,STATIC50_MID=targets)
            raw=(p/'1900/TARGETS.npz').read_bytes();prep=runner.body(dict(artifacts={'1900/TARGETS.npz':{'SHA256':sha256(raw).hexdigest()}}))
            (p/'PREPARATION.json').write_bytes(prep);(p/'GUARD_RECEIPTS.json').write_bytes(runner.body(d.V2.OWNED.export_tree(guard.receipts)))
            (p/'ACTUAL_HELD_RISK_REPORT.json').write_bytes(runner.body(risk))
            saved=runner.validate_saved_risk_report(p,preparation_directory=p,preparation_raw=prep,
                cell=dict(calendar=[sim.start,sim.end],year=1900,config='STATIC50_MID',tier='MID'),
                receipt=dict(completed_minutes=1440,account_stop_us=None),result=result)
            self.assertEqual(saved,risk)

if __name__=='__main__':
    began=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(GeneratedReview)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(status='PASS_GENERATED_ONLY' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        fixture_scope=d.GENERATED,actual_2021_source_inputs_used=False,actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,
        historical_market_minutes_advanced=0,historical_scopes_created=0,real_GO_written=0,
        code_files={name:sha256((d.HERE/name).read_bytes()).hexdigest() for name in ('partial_source.py','partial_d.py','partial_entry.py','run_partial.py')},
        test_script_SHA256=sha256(Path(__file__).read_bytes()).hexdigest(),wall_seconds=time.monotonic()-began,CPU_affinity=sorted(os.sched_getaffinity(0)),
        observed_task_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},
        maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    with (HERE/'GENERATED_REVIEW_FINAL.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    raise SystemExit(not result.wasSuccessful())

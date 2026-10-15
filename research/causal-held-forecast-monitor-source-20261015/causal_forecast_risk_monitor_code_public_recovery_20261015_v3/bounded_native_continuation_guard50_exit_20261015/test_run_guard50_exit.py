"""Generated one-day saved evidence, never actual historical construction."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import guard50_exit as i
import run_guard50_exit as runner
import numpy as np
from test_native_runtime import fixture


def run_case():
    # Origin, rows, targets and market are generated fixtures only.
    window, rows, decisions = fixture(1)
    sim, guard = i.construct_case(window, rows, decisions, np.full((1, 5), .03),
        policy_variant=i.POLICY_VARIANT, generated_scope=i.GENERATED)
    while sim.cursor < sim.end and sim.stop is None:
        sim.advance_day()
    return sim, guard


def body(value):return (json.dumps(value,indent=2)+'\n').encode()


class Guard50ExitSavedTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sim,guard=run_case();cls.audit=sim.account.snapshot();cls.result=i.V2.OWNED.export_tree(i.case_result(sim,guard))
        cls.result.pop('minute');cls.result['targets']=cls.result['targets'].to_dicts()
        cls.calendar=[sim.start,sim.end]

    def fixture(self,path):
        audit=deepcopy(self.audit);result=deepcopy(self.result)
        prep=dict(config='STATIC50_MID',cost='BASE27',calendar=self.calendar,
            source_identity='generated_source_identity',code_identity={'guard50_exit.py':'generated_code'},policy_identity='generated_policy_identity')
        preparation=body(prep);go=body(dict(permitted_modes=['GUARD50_EXIT_ONLY']))
        go_sha=runner.sha(go);review_sha='a'*64
        audit['historical_execution_scope']=dict(preparation_SHA256=runner.sha(preparation),
            source_identity=prep['source_identity'],root_GO_SHA256=go_sha,independent_review_SHA256=review_sha,
            policy_identity=prep['policy_identity'],policy_variant='GUARD50_EXIT_ONLY',config=prep['config'],
            generated_fixture_scope_used=False,fresh_genesis_only=True)
        # This is a generated evidence-record fixture. The fields above only
        # exercise saved-file consistency and never mint a historical scope.
        receipt=dict(schema='FINITE_GUARD50_EXIT_ONLY_CASE_V1',status='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT',
            policy_variant='GUARD50_EXIT_ONLY',config=prep['config'],cost=prep['cost'],calendar=self.calendar,
            root_GO_SHA256=go_sha,independent_review_SHA256=review_sha,
            preparation_SHA256=runner.sha(preparation),source_identity=prep['source_identity'],
            code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],required_minutes=1440,
            limits=runner.LIMITS,no_halt_reset=True,snapshot_restart_certified=False,locked_source_reads=0,
            actual_trades_or_orders=0,venue_settlement_certified=False,primary_financial_reconciliation_passed=True,
            completed_minutes=1440,account_stop_us=None,full_calendar=True,actual_paid_market_flat=True,
            conditional_settled_flat=False,comparable_full_calendar_return=result['economics']['comparable_full_calendar_return'],
            total_wall_seconds=1.,max_RSS_bytes=100_000_000)
        files={'ACCOUNT_FINANCIAL_AUDIT.json':audit,'NATIVE_RESULT.json':result,
            'PRIMARY_FINANCIAL_RECONCILIATION.json':result['primary_financial_reconciliation'],'CASE_RECEIPT.json':receipt}
        for name,value in files.items():(path/name).write_bytes(body(value))
        self.checkpoint(path)
        return dict(preparation_raw=preparation,go_raw=go,expected_go_sha256=go_sha,
            expected_review_sha256=review_sha,policy_variant='GUARD50_EXIT_ONLY')

    def checkpoint(self,path):
        names={'CASE_RECEIPT.json':'case_receipt_SHA256','ACCOUNT_FINANCIAL_AUDIT.json':'account_financial_audit_SHA256',
            'NATIVE_RESULT.json':'native_result_SHA256','PRIMARY_FINANCIAL_RECONCILIATION.json':'primary_financial_reconciliation_SHA256'}
        cp={key:runner.sha((path/name).read_bytes()) for name,key in names.items()}
        cp.update(all_evidence_fsynced=True,restart_permission=False)
        (path/'TERMINAL_CHECKPOINT.json').write_bytes(body(cp))

    def test_saved_terminal_positive_generated_records(self):
        with tempfile.TemporaryDirectory(dir=i.HERE) as folder:
            path=Path(folder);kwargs=self.fixture(path)
            self.assertEqual(runner.validate_saved_terminal(path,**kwargs)['status'],'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')

    def test_every_referenced_file_tamper_and_missing_checkpoint_rejected(self):
        for name in ('CASE_RECEIPT.json','ACCOUNT_FINANCIAL_AUDIT.json','NATIVE_RESULT.json','PRIMARY_FINANCIAL_RECONCILIATION.json','TERMINAL_CHECKPOINT.json'):
            with self.subTest(file=name),tempfile.TemporaryDirectory(dir=i.HERE) as folder:
                path=Path(folder);kwargs=self.fixture(path)
                (path/name).unlink()
                with self.assertRaises((ValueError,FileNotFoundError)):runner.validate_saved_terminal(path,**kwargs)

    def test_self_consistent_hashes_cannot_hide_false_paid_or_balance(self):
        cases=(('NATIVE_RESULT.json','paid'),('ACCOUNT_FINANCIAL_AUDIT.json','cash'),
            ('CASE_RECEIPT.json','source'),('CASE_RECEIPT.json','calendar'),('CASE_RECEIPT.json','review'))
        for name,kind in cases:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=i.HERE) as folder:
                path=Path(folder);kwargs=self.fixture(path);record=json.loads((path/name).read_bytes())
                if kind=='paid':record['economics']['conditional_settled_flat']=True
                elif kind=='cash':record['free_cash']=str(float(record['free_cash'])+1)
                elif kind=='source':record['source_identity']='wrong'
                elif kind=='calendar':record['completed_minutes']=1439
                elif kind=='review':record['independent_review_SHA256']='b'*64
                (path/name).write_bytes(body(record));self.checkpoint(path)
                with self.assertRaises(ValueError):runner.validate_saved_terminal(path,**kwargs)

    def test_incomplete_active_is_not_native_economic_halt(self):
        with tempfile.TemporaryDirectory(dir=i.HERE) as folder:
            path=Path(folder);kwargs=self.fixture(path)
            receipt=json.loads((path/'CASE_RECEIPT.json').read_bytes())
            result=json.loads((path/'NATIVE_RESULT.json').read_bytes())
            receipt.update(status='NATIVE_HALT_PARTIAL_CALENDAR',completed_minutes=1439,
                full_calendar=False,actual_paid_market_flat=False,conditional_settled_flat=False,
                comparable_full_calendar_return=None)
            result['summary']['completed_minutes']=1439
            result['economics'].update(full_calendar=False,actual_paid_market_flat=False,paid_flat=False,
                conditional_settled_flat=False,paid_net_return=None,conditional_model_net_return=None,
                comparable_full_calendar_return=None)
            (path/'CASE_RECEIPT.json').write_bytes(body(receipt));(path/'NATIVE_RESULT.json').write_bytes(body(result))
            self.checkpoint(path)
            with self.assertRaisesRegex(ValueError,'INCOMPLETE_ACTIVE'):runner.validate_saved_terminal(path,**kwargs)

    def test_positive_flat_relabelled_bankrupt_halt_rejected(self):
        with tempfile.TemporaryDirectory(dir=i.HERE) as folder:
            path=Path(folder);kwargs=self.fixture(path)
            receipt=json.loads((path/'CASE_RECEIPT.json').read_bytes())
            audit=json.loads((path/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes())
            result=json.loads((path/'NATIVE_RESULT.json').read_bytes())
            stop=self.calendar[1]
            witness=dict(event_us=stop,NAV=float(audit['free_cash']),unpaid_liability=0,
                decimal_strings=dict(NAV=audit['free_cash'],unpaid_liability='0'))
            audit.update(status='BANKRUPT_HALT',halt_witness=witness,clock_us=stop)
            receipt.update(status='NATIVE_HALT_PARTIAL_CALENDAR',completed_minutes=1439,account_stop_us=stop,
                full_calendar=False,actual_paid_market_flat=False,conditional_settled_flat=False,comparable_full_calendar_return=None)
            result['summary'].update(account_status='BANKRUPT_HALT',halt_witness=witness,clock_us=stop,
                completed_minutes=1439,stop_us=stop)
            result['economics'].update(full_calendar=False,actual_paid_market_flat=False,paid_flat=False,
                conditional_settled_flat=False,paid_net_return=None,conditional_model_net_return=None,
                comparable_full_calendar_return=None)
            for name,record in (('CASE_RECEIPT.json',receipt),('ACCOUNT_FINANCIAL_AUDIT.json',audit),('NATIVE_RESULT.json',result)):
                (path/name).write_bytes(body(record))
            self.checkpoint(path)
            with self.assertRaisesRegex(ValueError,'BANKRUPTCY_PREDICATE'):runner.validate_saved_terminal(path,**kwargs)

    def test_safety_boolean_integer_substitution_rejected(self):
        for name,key in (('CASE_RECEIPT.json','no_halt_reset'),('CASE_RECEIPT.json','actual_trades_or_orders'),
                ('CASE_RECEIPT.json','actual_paid_market_flat'),('NATIVE_RESULT.json','paid_flat')):
            with self.subTest(key=key),tempfile.TemporaryDirectory(dir=i.HERE) as folder:
                path=Path(folder);kwargs=self.fixture(path);record=json.loads((path/name).read_bytes())
                if key=='paid_flat':record['economics'][key]=1
                elif key=='actual_trades_or_orders':record[key]=False
                else:record[key]=1
                (path/name).write_bytes(body(record));self.checkpoint(path)
                with self.assertRaises(ValueError):runner.validate_saved_terminal(path,**kwargs)

    def test_resealed_transfer_or_non_D_outward_policy_is_rejected(self):
        probes=(
            ('ACCOUNT_FINANCIAL_AUDIT.json',('transfer_journal',),[{'transferred':'1'}]),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('transfer_ids',),{'FORGED':'TRANSFER'}),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('automatic_topup',),True),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('policy_variant',),'TOPUP_THEN_CONTINUE'),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('continuation_policy',),'OLD_C_POLICY'),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('contract','policy_variant'),'TOPUP_THEN_CONTINUE'),
            ('ACCOUNT_FINANCIAL_AUDIT.json',('contract','topup_enabled'),True),
            ('NATIVE_RESULT.json',('common_execution_policy','automatic_topup'),True),
            ('NATIVE_RESULT.json',('common_execution_policy','automatic_topup'),0),
            ('NATIVE_RESULT.json',('common_execution_policy','policy_variant'),'CONTINUE_ONLY'),
            ('NATIVE_RESULT.json',('summary','contract','policy_variant'),'TOPUP_THEN_CONTINUE'),
            ('NATIVE_RESULT.json',('summary','contract','topup_enabled'),True),
            ('NATIVE_RESULT.json',('continuation_economic_report','policy_variant'),'TOPUP_THEN_CONTINUE'),
            ('NATIVE_RESULT.json',('continuation_economic_report','transfers'),[{'transferred':'1'}]),
            ('NATIVE_RESULT.json',('continuation_economic_report','contract','topup_enabled'),True),
            ('NATIVE_RESULT.json',('policy_variant',),'CONTINUE_ONLY'),
            ('NATIVE_RESULT.json',('automatic_topup',),True),
        )
        for name,keys,value in probes:
            with self.subTest(file=name,field=keys),tempfile.TemporaryDirectory(dir=i.HERE) as folder:
                path=Path(folder);kwargs=self.fixture(path)
                record=json.loads((path/name).read_bytes());target=record
                for key in keys[:-1]:target=target[key]
                target[keys[-1]]=value
                (path/name).write_bytes(body(record));self.checkpoint(path)
                with self.assertRaisesRegex(ValueError,'EXACT_D_ONLY_NO_TRANSFER'):
                    runner.validate_saved_terminal(path,**kwargs)

    def test_no_controller_scope_without_exact_go(self):
        class Args:pass
        with tempfile.TemporaryDirectory(dir=i.HERE) as folder:
            path=Path(folder);(path/'PREPARATION.json').write_bytes(b'{}')
            go=path/'GO.json';go.write_bytes(body(dict(permitted_modes=['CONTINUE_ONLY'],resource_limits=runner.LIMITS)))
            review=path/'REVIEW.json';review.write_bytes(b'{}')
            args=Args();args.preparation=str(path);args.go=str(go);args.review=str(review)
            args.go_sha=runner.sha(go.read_bytes());args.review_sha=runner.sha(review.read_bytes())
            with self.assertRaisesRegex(ValueError,'SINGLE_D_ONLY'):runner.validate_scope(args)

if __name__=='__main__':unittest.main()

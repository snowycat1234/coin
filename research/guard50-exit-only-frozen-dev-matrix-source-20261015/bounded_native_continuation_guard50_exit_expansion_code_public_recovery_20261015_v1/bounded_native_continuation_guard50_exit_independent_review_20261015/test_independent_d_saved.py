"""Generated D saved-record tests; synthetic scope metadata creates no scope."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import guard50_exit as d
import run_guard50_exit as runner
from test_native_runtime import fixture

def body(value):return (json.dumps(value,indent=2)+'\n').encode()


class IndependentDSaved(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        window,rows,decisions=fixture(1)
        sim,g=d.construct_case(window,rows,decisions,np.full((1,5),.03),generated_scope=d.GENERATED)
        while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        cls.audit=sim.account.snapshot();cls.result=d.V2.OWNED.export_tree(d.case_result(sim,g))
        cls.result.pop('minute');cls.result['targets']=cls.result['targets'].to_dicts()
        cls.calendar=[sim.start,sim.end]

    def checkpoint(self,path):
        names={'CASE_RECEIPT.json':'case_receipt_SHA256','ACCOUNT_FINANCIAL_AUDIT.json':'account_financial_audit_SHA256',
            'NATIVE_RESULT.json':'native_result_SHA256','PRIMARY_FINANCIAL_RECONCILIATION.json':'primary_financial_reconciliation_SHA256'}
        cp={key:runner.sha((path/name).read_bytes()) for name,key in names.items()}
        cp.update(all_evidence_fsynced=True,restart_permission=False)
        (path/'TERMINAL_CHECKPOINT.json').write_bytes(body(cp))

    def saved_fixture(self,path):
        audit=deepcopy(self.audit);result=deepcopy(self.result)
        prep=dict(config='STATIC50_MID',cost='BASE27',calendar=self.calendar,
            source_identity='generated_D_source',code_identity={'guard50_exit.py':'generated_D_code'},policy_identity='generated_D_policy')
        preparation=body(prep);go=body(dict(permitted_modes=[d.POLICY_VARIANT]));go_sha=runner.sha(go);review_sha='b'*64
        # Deliberately synthetic exported record fields exercise only the
        # saved-file checker. They never instantiate a historical scope.
        audit['historical_execution_scope']=dict(preparation_SHA256=runner.sha(preparation),
            source_identity=prep['source_identity'],root_GO_SHA256=go_sha,independent_review_SHA256=review_sha,
            policy_identity=prep['policy_identity'],policy_variant=d.POLICY_VARIANT,config=prep['config'],
            generated_fixture_scope_used=False,fresh_genesis_only=True)
        receipt=dict(schema='FINITE_GUARD50_EXIT_ONLY_CASE_V1',status='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT',
            policy_variant=d.POLICY_VARIANT,config=prep['config'],cost=prep['cost'],calendar=self.calendar,
            root_GO_SHA256=go_sha,independent_review_SHA256=review_sha,preparation_SHA256=runner.sha(preparation),
            source_identity=prep['source_identity'],code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],
            required_minutes=1440,limits=runner.LIMITS,no_halt_reset=True,snapshot_restart_certified=False,
            locked_source_reads=0,actual_trades_or_orders=0,venue_settlement_certified=False,
            primary_financial_reconciliation_passed=True,completed_minutes=1440,account_stop_us=None,
            full_calendar=True,actual_paid_market_flat=True,conditional_settled_flat=False,
            comparable_full_calendar_return=result['economics']['comparable_full_calendar_return'],
            total_wall_seconds=1.,max_RSS_bytes=100_000_000)
        for name,value in [('ACCOUNT_FINANCIAL_AUDIT.json',audit),('NATIVE_RESULT.json',result),
                ('PRIMARY_FINANCIAL_RECONCILIATION.json',result['primary_financial_reconciliation']),('CASE_RECEIPT.json',receipt)]:
            (path/name).write_bytes(body(value))
        self.checkpoint(path)
        return dict(preparation_raw=preparation,go_raw=go,expected_go_sha256=go_sha,
            expected_review_sha256=review_sha,policy_variant=d.POLICY_VARIANT)

    def test_generated_D_saved_positive(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);kwargs=self.saved_fixture(path)
            self.assertEqual(runner.validate_saved_terminal(path,**kwargs)['status'],'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')

    def test_resealed_impossible_transfer_or_wrong_D_policy_is_rejected(self):
        cases=(('ACCOUNT_FINANCIAL_AUDIT.json','transfer_journal'),('ACCOUNT_FINANCIAL_AUDIT.json','transfer_ids'),
            ('ACCOUNT_FINANCIAL_AUDIT.json','topup_enabled'),('NATIVE_RESULT.json','automatic_topup'),
            ('NATIVE_RESULT.json','policy_variant'))
        for name,field in cases:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as folder:
                path=Path(folder);kwargs=self.saved_fixture(path);record=json.loads((path/name).read_bytes())
                if field=='transfer_journal':record[field]=[dict(id='IMPOSSIBLE_D_TRANSFER')]
                elif field=='transfer_ids':record[field]={'IMPOSSIBLE_D_TRANSFER':{}}
                elif field=='topup_enabled':record['contract'][field]=True
                elif field=='automatic_topup':record['common_execution_policy'][field]=True
                else:record['common_execution_policy'][field]='TOPUP_THEN_CONTINUE'
                (path/name).write_bytes(body(record));self.checkpoint(path)
                with self.assertRaises(ValueError):runner.validate_saved_terminal(path,**kwargs)


if __name__=='__main__':unittest.main(verbosity=2)

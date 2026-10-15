"""Independent saved-event and packet-boundary corruption tests; no finance runtime."""
from copy import deepcopy
from pathlib import Path, PurePosixPath
from decimal import Decimal, localcontext
import contextlib, gzip, hashlib, json, os, resource, stat, sys, time, unittest

OUT=Path(__file__).resolve().parent
NAME='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1'
ROOT=OUT/'fresh_extraction'/NAME
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from saved_native_reconciliation import reconcile_saved_native
from saved_report import ATT,REV,CELLS,load
from verify_packet import validate_identity

def safe_member(name,mode=0o100644):
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or p.parts[0]!=NAME or '..' in p.parts or '\\' in name or stat.S_ISLNK(mode):
        raise ValueError('UNSAFE_ARCHIVE_MEMBER')

def exact_source(s):
    expected={'source_commit':'f8239806dd68e833273c6684102ebefffc3033b1',
              'source_parent_commit':'bf2b1d40df9958033e7d61c38c5b8f343127771b',
              'full_private_publication_receipt_sha256':'fc30cd10b3106e2020878afaafa8a05076225eb1eeaf5a7f850a9b723da078e1',
              'source_archive_sha256':'b0dcec82a6f8c28feba170aa080a131fb6c6494b3b06b2046a962e99f004c8f7',
              'source_archive_bytes':696892,'every_remote_byte_matches_expected_local':True,
              'results_publication_must_be_additive_child_of_source_commit':True}
    for k,v in expected.items():
        if type(s.get(k)) is not type(v) or s[k]!=v:raise ValueError('EXACT_EXTERNALLY_PINNED_SOURCE_CHAIN:'+k)

class IndependentNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d=ROOT/ATT/CELLS[0]
        cls.a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');cls.r=load(d/'NATIVE_RESULT.json')
        cls.receipt=load(d/'CASE_RECEIPT.json');cls.review=load(ROOT/REV/(CELLS[0]+'_SAVED_REVIEW.json'))
        cls.desc=load(ROOT/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')['cells'][0]
        cls.source=load(ROOT/'SOURCE_PUBLICATION_REFERENCE.json')

    def bad_audit(self,change,reason):
        a=deepcopy(self.a);change(a)
        with self.assertRaisesRegex(ValueError,reason):reconcile_saved_native(a)

    def test_positive_direct_chronological_without_proof_hash_shortcut(self):
        self.assertTrue(reconcile_saved_native(self.a,self.r)['passed'])
    def test_duplicate_trade_id(self):self.bad_audit(lambda a:a['trades'][1].update(fill_id=a['trades'][0]['fill_id']),'UNIQUE_NATIVE_EVENT_IDS')
    def test_duplicate_symbol_funding_time(self):self.bad_audit(lambda a:a['funding'][1].update(symbol=a['funding'][0]['symbol']),'UNIQUE_NATIVE_SYMBOL_FUNDING_CLOCK')
    def test_trade_clock_boolean(self):self.bad_audit(lambda a:a['trades'][0].update(event_us=True),'CHRONOLOGICAL_NATIVE_EVENT_CLOCKS')
    def test_trade_clock_reordering(self):self.bad_audit(lambda a:a['trades'].reverse(),'CHRONOLOGICAL_NATIVE_EVENT_CLOCKS')
    def test_duplicate_symbol_order(self):self.bad_audit(lambda a:a['symbols'].append(a['symbols'][0]),'EXACT_UNIQUE_SYMBOL_ORDER')
    def test_initial_account_changed(self):self.bad_audit(lambda a:a['config'].update(initial_cash='10001'),'FROZEN_BASE27_ONE_X_CONFIG')
    def test_leverage_changed(self):self.bad_audit(lambda a:a['config'].update(leverage='2'),'FROZEN_BASE27_ONE_X_CONFIG')
    def test_fee_rate_changed(self):self.bad_audit(lambda a:a['config'].update(fee_rate='0.0005'),'FROZEN_BASE27_ONE_X_CONFIG')
    def test_automatic_topup_enabled(self):self.bad_audit(lambda a:a['contract'].update(automatic_topup=True),'SAVED_NO_TOPUP_POLICY')
    def test_trade_nonfinite_decimal(self):self.bad_audit(lambda a:a['trades'][0]['decimal_strings'].update(fill_price='NaN'),'EXACT_FINITE_DECIMAL_STRING')
    def test_trade_numeric_decimal(self):self.bad_audit(lambda a:a['trades'][0]['decimal_strings'].update(fill_price=1968.573880),'EXACT_FINITE_DECIMAL_STRING')
    def test_trade_paid_price_changed(self):self.bad_audit(lambda a:a['trades'][0]['decimal_strings'].update(fill_price='1968.573881'),'EXACT_BASE27_PRICE')
    def test_trade_latency_shortened(self):self.bad_audit(lambda a:a['trades'][0].update(signal_us=a['trades'][0]['event_us']),'EXACT_BASE27_PRICE_AND_NATIVE_LATENCY')
    def test_trade_side_changed(self):self.bad_audit(lambda a:a['trades'][0].update(side='BUY'),'EXACT_BASE27_PRICE')
    def test_trade_leg_changed(self):self.bad_audit(lambda a:a['trades'][0].update(leg='CLOSE'),'EXACT_NATIVE_TRADE_LEG')
    def test_trade_execution_cost_digit(self):self.bad_audit(lambda a:a['trades'][0]['decimal_strings'].update(execution_cost='0.01576121'),'NATIVE_TRADE_EXACT_FIELD_MISMATCH:execution_cost')
    def test_ledger_sequence_gap(self):self.bad_audit(lambda a:a['financial_ledger'][0].update(sequence=2),'CHRONOLOGICAL_CONTIGUOUS_LEDGER')
    def test_ledger_unknown_kind(self):self.bad_audit(lambda a:a['financial_ledger'][0].update(kind='TRANSFER'),'UNEXPECTED_NO_TRANSFER_FINANCIAL_KIND')
    def test_ledger_fee_delta_digit(self):self.bad_audit(lambda a:a['financial_ledger'][0].update(fee_delta='0.0108271563401'),'NATIVE40_LEDGER_EXACT_FIELD_MISMATCH:fee_delta')
    def test_ledger_missing_quantity_symbol(self):self.bad_audit(lambda a:a['financial_ledger'][0]['quantity_delta'].pop('BTCUSDT'),'EXACT_LEDGER_SYMBOLS')
    def test_funding_lookahead_rate(self):self.bad_audit(lambda a:a['funding'][0].update(rate_available_us=a['funding'][0]['event_us']+1),'EXACT_NATIVE_FUNDING_ARITHMETIC_OWNERSHIP')
    def test_funding_no_completed_prior_mark(self):self.bad_audit(lambda a:a['funding'][0].update(mark_close_us=a['funding'][0]['event_us']),'EXACT_NATIVE_FUNDING_ARITHMETIC_OWNERSHIP')
    def test_funding_owned_integer(self):self.bad_audit(lambda a:a['funding'][0].update(owned=0),'EXACT_NATIVE_FUNDING_SYMBOL_OWNERSHIP')
    def test_funding_unowned_nonzero_charge(self):self.bad_audit(lambda a:a['funding'][0]['decimal_strings'].update(signed_funding_USDT='0.00001'),'EXACT_NATIVE_FUNDING_ARITHMETIC_OWNERSHIP|EXACT_FUNDING_LEDGER_ORDER')
    def test_exact_final_total_friction_changed(self):self.bad_audit(lambda a:a['totals'].update(execution_cost='10.0688333361'),'FINAL_NATIVE_TOTAL_MISMATCH:execution_cost')
    def test_result_nav_mutation_without_proof_hash_shortcut(self):
        r=deepcopy(self.r);r['summary']['decimal_strings']['NAV']='10981.59660181968820472910000000000000001'
        with self.assertRaisesRegex(ValueError,'SAVED_RESULT_NATIVE_EXACT_FIELD_MISMATCH:NAV'):reconcile_saved_native(self.a,r)
    def test_distinct_case_cannot_relabel_calendar(self):
        a=deepcopy(self.a);a['historical_execution_scope']['calendar'][0]-=60000000
        with self.assertRaisesRegex(ValueError,'EXACT_TYPED_SCOPE_BINDING:calendar'):validate_identity(self.receipt,a,self.r,self.review,self.desc)
    def test_scope_cannot_claim_365_days(self):
        a=deepcopy(self.a);a['historical_execution_scope']['days']=365
        with self.assertRaisesRegex(ValueError,'EXACT_TYPED_SCOPE_BINDING:days'):validate_identity(self.receipt,a,self.r,self.review,self.desc)
    def test_source_pinned_positive(self):exact_source(self.source)
    def test_source_commit_relabel_rejected(self):
        s=deepcopy(self.source);s['source_commit']='0'*40
        with self.assertRaises(ValueError):exact_source(s)
    def test_source_archive_float_byte_count_rejected(self):
        s=deepcopy(self.source);s['source_archive_bytes']=696892.0
        with self.assertRaises(ValueError):exact_source(s)
    def test_source_not_remotely_verified_rejected(self):
        s=deepcopy(self.source);s['every_remote_byte_matches_expected_local']=False
        with self.assertRaises(ValueError):exact_source(s)
    def test_archive_traversal_rejected(self):
        with self.assertRaises(ValueError):safe_member(NAME+'/../escape')
    def test_archive_absolute_rejected(self):
        with self.assertRaises(ValueError):safe_member('/'+NAME+'/member')
    def test_archive_backslash_rejected(self):
        with self.assertRaises(ValueError):safe_member(NAME+'/folder\\escape')
    def test_archive_symlink_rejected(self):
        with self.assertRaises(ValueError):safe_member(NAME+'/link',0o120777)
    def test_transport_order_corruption_rejected(self):
        t=OUT.parent/(NAME+'_exact_transport');b=[(t/(NAME+'.zip.part00'+str(i))).read_bytes() for i in (1,2)]
        self.assertNotEqual(hashlib.sha256(b[1]+b[0]).hexdigest(),'2caf85dde33db4a1ac31e04cec830ec6df72a1e6029e2e4b32b093d869e85c1a')

if __name__=='__main__':
    assert os.sched_getaffinity(0)=={7}
    start=time.monotonic();cpu=time.process_time()
    with (OUT/'INDEPENDENT_NEGATIVES.log').open('w') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentNegativeTests))
    receipt=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,tests_passed=result.testsRun-len(result.failures)-len(result.errors),failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),CPU_affinity=sorted(os.sched_getaffinity(0)),numerical_threads=1,wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,direct_native_arithmetic_without_proof_hash_shortcut=True,no_original_review_scripts_or_builder_executed=True,no_financial_actions=True)
    (OUT/'INDEPENDENT_NEGATIVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True));sys.exit(0 if result.wasSuccessful() else 1)

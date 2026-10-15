"""Independent generated tier transport and paid reduction boundaries."""
from copy import deepcopy
from decimal import Decimal as Q
import unittest
import numpy as np
import expansion as e
from test_expansion import account,marks,fill,finance
from test_native_runtime import fixture

class GeneralizedPolicy(unittest.TestCase):
    def test_gap_new_strategy_reductions_remain_paid_in_each_tier(self):
        for tier in e.TIERS:
            with self.subTest(tier=tier):
                w,r,d=fixture(2);decision=int(d[1]);intervals=((decision-2*e.MINUTE,decision+3*e.MINUTE,e.S),)
                weights=np.array([[.03]*5,[0.]*5])
                native,ng=e.V2.native.build_case(w,r,d,weights,tier_name=tier,generated_scope=e.GENERATED)
                interval=e.V2.quality_module.StaleMarkInterval(start_us=decision-2*e.MINUTE,end_us=decision+3*e.MINUTE,original_genuine_observation_us=decision-3*e.MINUTE,symbols=e.S)
                e.V2.quality_module.CausalMarkQualityGuard(ng,intervals=(interval,),source_sidecar_sha256='d'*64).install()
                bounded,bg=e.construct_case(w,r,d,weights,tier_name=tier,generated_scope=e.GENERATED,quality_intervals=intervals)
                for sim in (native,bounded):
                    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertEqual(finance(native.account),finance(bounded.account))
                paid=[t for t in bounded.account.trades if t['leg']=='CLOSE' and not t.get('liquidation_takeover')]
                self.assertEqual(len(paid),5)
                self.assertTrue(any(decision<=t['event_us']<decision+3*e.MINUTE for t in paid))
                self.assertFalse(bounded.account.transfer_journal)
                self.assertFalse(bounded.account.settlement_journal)
    def test_adverse_preview_does_not_mutate_live_inventory_or_warning_state(self):
        for tier in e.TIERS:
            with self.subTest(tier=tier):
                a=account(tier);fill(a);at=2*e.MINUTE;marks(a,at)
                before=a.preview_state_token();clone=a.fork_for_preview()
                marks(clone,at+e.MINUTE,100000)
                self.assertEqual(len(clone.settlement_journal),1)
                self.assertTrue(e.V2.native._exact_tree_equal(before,a.preview_state_token()))
                self.assertEqual(a.positions['BTCUSDT'].quantity,Q('-.02'))
                self.assertFalse(a.settlement_journal);self.assertFalse(a.pending_exits);self.assertFalse(a.transfer_journal)
    def test_funding_and_paid_close_reconstruct_at_every_nominal_tier(self):
        from saved_native_reconciliation import reconcile_saved_native
        for tier in e.TIERS:
            a=account(tier);fill(a);at=2*e.MINUTE;marks(a,at-1)
            a.apply_funding('BTCUSDT','OWNED_FUND',at,'.001',at)
            signal=3*e.MINUTE;event=signal+e.MINUTE+1;marks(a,event-1)
            a.execute_fill('BTCUSDT','BUY','.02',event,signal,'PAID_CLOSE',execution_mid_price='49000',quote_available_us=event-1,available_quantity='.02',reduce_only=True)
            proof=reconcile_saved_native(e.V2.OWNED.export_tree(a.snapshot()),expected_continuation_version=e.VERSION)
            self.assertTrue(proof['passed']);self.assertEqual(proof['funding_rows_checked'],1)
            self.assertEqual(proof['trade_rows_checked'],2);self.assertEqual(proof['conditional_settlement_rows_checked'],0)
            self.assertFalse(a.transfer_journal)

if __name__=='__main__':unittest.main(verbosity=2)

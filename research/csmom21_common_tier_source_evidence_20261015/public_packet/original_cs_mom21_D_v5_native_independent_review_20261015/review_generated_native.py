"""Independent generated-only review of the CS transport, never historical data."""
from copy import deepcopy
from decimal import Decimal as Q
from hashlib import sha256
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'original_cs_mom21_D_20261015_v5'))
import cs_generated as g
import cs_signal as signal
from cs_quality import original_quality
E = g.native_reference()
BASE = (50000, 2000, 20, .5, .05)


def account(tier='MID'):
    plain = E.V2.grid.make_account(tier, 'BASE27')
    return E.ExpansionAccount(plain.config, symbols=E.S, instrument_profiles=plain.instrument_profiles,
                              generated_scope=E.GENERATED, tier_name=tier)


def marks(a, at, btc=None, selected=None):
    selected = E.S if selected is None else selected
    return a.update_marks(at, {s: dict(price=str(btc if s == 'BTCUSDT' and btc is not None else BASE[j]),
                    close_us=at, available_us=at) for j, s in enumerate(E.S) if s in selected})


def initial(a, start=0):
    at = start + E.MINUTE + 1
    marks(a, at - 1)
    result = a.execute_fill('BTCUSDT', 'SELL', '.02', at, start, 'INDEPENDENT_FAKE_INITIAL',
            execution_mid_price='50000', quote_available_us=at - 1, available_quantity='.02')
    assert result['status'] == 'FILLED'
    return at


def finance(a):
    x = a.snapshot()
    return {k: x[k] for k in ('free_cash','unpaid_liability','positions','marks','totals','trades',
                              'funding','fill_requests','funding_events','funding_ids')}


def cell(symbol, opening, anchor):
    return original_quality().QualityCell(symbol, opening, opening + E.MINUTE, opening + E.MINUTE,
        str(BASE[E.S.index(symbol)]), anchor - E.MINUTE, anchor, anchor, anchor, anchor,
        'a' * 64, 'INDEPENDENT_FAKE_GENUINE_ANCHOR_' + symbol)


class NativeTransportReview(unittest.TestCase):
    def test_exact_source_graph_stays_byte_frozen(self):
        expected = {'CODE_MANIFEST.json':'21e13995b6be9482ee4e20d8e63be6d63396229035f69c963901331713342fce',
                    'FROZEN_FIFTEEN_CELL_MANIFEST.json':'9a5ef547d61272d5eb0bfb1b61fef8005a752d82f4e0007d18cbe65f06445a8a',
                    'SOURCE_CONTRACT_MAP.json':'9ead9f2aa1e2581f9bd200def5a3c5dbd21205dcacfc0048d7b820c15ec1f951'}
        for name, pin in expected.items():
            self.assertEqual(sha256((g.HERE/name).read_bytes()).hexdigest(),pin)

    def test_unchanged_finance_scheduler_and_quality_code_identities(self):
        a, d, v = E.ExpansionAccount, E.D.Guard50ExitAccount, E.V2
        for name in ('monitor','_transfer','execute_fill','apply_funding','fork_for_preview','preview_state_token'):
            self.assertIs(getattr(a,name),getattr(d,name),name)
        self.assertIs(a._leg,v.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(E.ContinuationGuard.attempt,E.D.ContinuationGuard.attempt)
        self.assertIs(E.ContinuationGuard.schedule.__code__,v.native.PartialTierGuard.schedule.__code__)
        self.assertIs(E.ContinuationGuard._frozen_attempt.__code__,v.native.PartialTierGuard.attempt.__code__)
        self.assertIs(E.ContinuationQualityGuard.attempt,v.quality_module.CausalMarkQualityGuard.attempt)

    def test_direct_generated_flag_cannot_admit_window_or_historical_shaped_inputs(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f);window,rows,decisions=g._synthetic_window(f)
            with self.assertRaisesRegex(ValueError,'INTERNALLY_SEALED_GENERATED_NATIVE_INPUTS_REQUIRED'):
                E._construct_case(window,rows,decisions,t.common_tier['MID'],tier_name='MID',generated_scope=E.GENERATED)
            with self.assertRaisesRegex(ValueError,'INTERNALLY_SEALED_GENERATED_NATIVE_INPUTS_REQUIRED'):
                E._construct_case({'start':1640995200000000,'end':1672531200000000},None,None,None,
                                  tier_name='MID',generated_scope=E.GENERATED)
            for intervals in (((0,1,E.S),),((int(f.decisions[0]),int(f.decisions[0])+E.MINUTE,list(E.S)),)):
                with self.assertRaisesRegex(ValueError,'BOUNDED_GENERATED_FIXTURE_ONLY_QUALITY_INTERVALS_REQUIRED'):
                    g.construct_generated_case(t,'MID',quality_intervals=intervals)
            self.assertFalse(g._LIVE_NATIVE_INPUTS)
            g.construct_generated_case(t,'MID')
            self.assertFalse(g._LIVE_NATIVE_INPUTS)

    def test_all_tier_native_configs_profiles_and_direct_transfers(self):
        for tier in E.TIERS:
            a = account(tier); plain=E.V2.grid.make_account(tier,'BASE27')
            self.assertEqual(a.config,plain.config);self.assertEqual(a.instrument_profiles,plain.instrument_profiles)
            self.assertEqual(a.free_cash,Q(10000)); self.assertFalse(a.topup_enabled)
            self.assertEqual(a.policy_variant,'GUARD50_EXIT_ONLY')
            token=a.preview_state_token()
            with self.assertRaisesRegex(ValueError,'TRANSFERS_FORBIDDEN'):
                a._transfer('BTCUSDT',Q(1),0,'FAKE_FORBIDDEN_TRANSFER')
            self.assertTrue(E.V2.native._exact_tree_equal(token,a.preview_state_token()))

    def test_fixture_target_identity_immutability_and_revocation(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f)
            with self.assertRaises(ValueError):t.common_tier['LOW'].setflags(write=True)
            with self.assertRaises(TypeError):t.common_tier['LOW']=t.raw_weekly
            self.assertIs(t.validate(),t)
        with self.assertRaisesRegex(ValueError,'LIVE_INTERNALLY'):t.validate()
        with self.assertRaisesRegex(ValueError,'LIVE_INTERNALLY'):g.construct_generated_case(t,'MID')
        self.assertFalse(g._LIVE_FIXTURES);self.assertFalse(g._LIVE_TARGETS)

    def test_generated_bounded_namespace_and_no_actual_inputs(self):
        for kwargs in ({'days':0},{'days':15},{'seed':-1},{'seed':65536},{'flat':1},{'future_spike':1}):
            with self.assertRaises(ValueError):
                with g.generated_fixture(**kwargs):pass
        with self.assertRaises(TypeError):
            with g.generated_fixture(close=[[1]*5]):pass

    def test_cash_floor_margin_ceiling_caps_are_charged_on_live_CS_account(self):
        for tier in E.TIERS:
            a=account(tier);at=E.MINUTE+1;marks(a,at-1)
            a.free_cash=Q(999);token=a.preview_state_token()
            result=E.capital_guard_fill(a,'BTCUSDT','BUY','.001',at,0,'FAKE_CASH_FLOOR',
                execution_mid_price='50000',quote_available_us=at-1,available_quantity='.001')
            self.assertEqual(result['reason'],'INITIAL_CASH_FLOOR_BREACHED')
            self.assertTrue(E.V2.native._exact_tree_equal(token,a.preview_state_token()))
        a=account('HIGH');at=E.MINUTE+1;marks(a,at-1)
        for j,s in enumerate(E.S[:3]):
            q=a._floor(s,Q(2800)/Q(str(BASE[j])))
            r=E.capital_guard_fill(a,s,'BUY',q,at+j,0,'FAKE_MARGIN_'+s,
                execution_mid_price=str(BASE[j]),quote_available_us=at-1,available_quantity=q)
            self.assertEqual(r['status'],'FILLED')
        token=a.preview_state_token()
        with self.assertRaisesRegex(ValueError,'CHARGED_POST_FILL_CAPITAL_GUARD_REJECTED'):
            E.capital_guard_fill(a,'XRPUSDT','BUY','400',at+4,0,'FAKE_MARGIN_OVERFLOW',
                execution_mid_price='.5',quote_available_us=at-1,available_quantity='400')
        self.assertTrue(E.V2.native._exact_tree_equal(token,a.preview_state_token()))

    def test_preview_fork_retains_new_quality_tier_state_and_isolates_callbacks(self):
        a=account('HIGH'); initial(a);at=2*E.MINUTE
        c=cell('BTCUSDT',at,at)
        a._source_quality_cells=(c,);a._quality_intervals=((at+E.MINUTE,at+2*E.MINUTE,('BTCUSDT',)),)
        a.pending_exits['BTCUSDT']={'signal_us':at,'reason':'INDEPENDENT_FAKE_PENDING'}
        a.liquidation_callback=lambda *args: self.fail('PREVIEW_CALLED_LIVE_CALLBACK')
        before=a.preview_state_token();clone=a.fork_for_preview()
        self.assertEqual(clone._source_quality_cells,a._source_quality_cells)
        self.assertEqual(clone._bound_tier_name,'HIGH');self.assertIsNone(clone.liquidation_callback)
        clone.pending_exits['BTCUSDT']['reason']='FAKE_CLONE_ONLY'
        clone._source_quality_cells=()
        self.assertTrue(E.V2.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertEqual(a.pending_exits['BTCUSDT']['reason'],'INDEPENDENT_FAKE_PENDING')
        token=a.preview_state_token();a._bound_tier_name='LOW'
        self.assertFalse(E.V2.native._exact_tree_equal(token,a.preview_state_token()))

    def test_hypothetical_open_settlement_rejected_and_actual_inventory_retained(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f);_,rows,d=g._synthetic_window(f)
            a=account();at=int(d[0]);initial(a,at)
            binding=E.V2.native.runtime()[5].CompletedBarSource(rows).bind(at)
            before=a.preview_state_token();real={s:a.positions[s].quantity for s in E.S}
            target=dict(real);target['ETHUSDT']=Q('.01')
            prices={s:Q(str(BASE[j])) for j,s in enumerate(E.S)};prices['BTCUSDT']=Q(100000)
            oracle=E.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
                price_available_us=dict.fromkeys(E.S,at+2*E.MINUTE),pending=target,
                capacity=dict.fromkeys(E.S,Q(100000)),event_us=at+2*E.MINUTE+1,
                signal_us=at,quote_available_us=at+2*E.MINUTE)
            proof=oracle.evaluate(target,Q(1))
            self.assertFalse(proof['allowed']);self.assertEqual(oracle.actual,real)
            self.assertTrue(E.V2.native._exact_tree_equal(before,a.preview_state_token()))
            self.assertFalse(a.settlement_journal);self.assertEqual(a.positions['BTCUSDT'].quantity,Q('-.02'))

    def test_noop_monotonic_ids_bounded_replay_and_financial_ids_survive(self):
        a=account();initial(a);at=2*E.MINUTE;marks(a,at,75000)
        receipt=a.monitor('MONITOR:'+str(at),at);token=a.preview_state_token()
        self.assertEqual(a.monitor('MONITOR:'+str(at),at),receipt)
        self.assertTrue(E.V2.native._exact_tree_equal(token,a.preview_state_token()))
        intent=deepcopy(a.pending_exits['BTCUSDT'])
        for k in range(1,81):
            clock=at+k*E.MINUTE;marks(a,clock,75000);a.monitor('MONITOR:'+str(clock),clock)
        self.assertEqual(a.pending_exits['BTCUSDT'],intent);self.assertLessEqual(len(a._noop_receipts),64)
        self.assertIn('MONITOR:'+str(at),a.operation_ids)
        with self.assertRaisesRegex(ValueError,'EXPIRED'):a.monitor('MONITOR:'+str(at+E.MINUTE),at+E.MINUTE)

    def test_paid_capacity_five_opens_renewal_latency_and_reductions_inside_unknown_gap(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f)
            for tier in E.TIERS:
                sim,guard=g.construct_generated_case(t,tier);a=sim.account;start=sim.start;initial(a,start)
                at=start+2*E.MINUTE;marks(a,at,75000);sim.risk_schedule(at)
                a._quality_intervals=((at+E.MINUTE,at+9*E.MINUTE,E.S),)
                sim.previous_quote={s:75000. if s=='BTCUSDT' else 1e10 for s in E.S}
                market={s:dict(open=75000. if j==0 else BASE[j],close=75000. if j==0 else BASE[j],
                    mark=75000. if j==0 else BASE[j],quote_volume=1e10) for j,s in enumerate(E.S)}
                for k in range(1,6):
                    now=at+k*E.MINUTE;marks(a,now,75000);sim.attempt(now,market)
                    paid=[r for r in a.trades if r['event_us']==now+1]
                    self.assertEqual(sum((Q(r['decimal_strings']['quantity']) for r in paid),Q(0)),Q('.001'))
                    self.assertTrue(all(r['leg']=='CLOSE' for r in paid))
                self.assertEqual(a.pending_exits['BTCUSDT']['renewals'],1)
                self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at+5*E.MINUTE+1)
                frozen=a.positions['BTCUSDT'].quantity
                marks(a,at+6*E.MINUTE,75000);sim.attempt(at+6*E.MINUTE,market)
                self.assertEqual(a.positions['BTCUSDT'].quantity,frozen)
                marks(a,at+7*E.MINUTE,75000);sim.attempt(at+7*E.MINUTE,market)
                self.assertEqual(a.positions['BTCUSDT'].quantity,frozen+Q('.001'))
                self.assertGreater(a.fees,Q(0));self.assertFalse(a.transfer_journal)

    def test_per_asset_quality_waits_for_every_installed_recovery_and_no_future_preblock(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f);sim,guard=g.construct_generated_case(t,'MID');a=sim.account
            at=sim.start+2*E.MINUTE;marks(a,at)
            cells=(cell('BTCUSDT',at,at),cell('ETHUSDT',at+E.MINUTE,at+E.MINUTE))
            a._source_quality_cells=cells
            a._quality_intervals=((at+E.MINUTE,at+2*E.MINUTE,('BTCUSDT',)),
                                  (at+2*E.MINUTE,at+3*E.MINUTE,('ETHUSDT',)))
            q=guard.causal_mark_quality_guard;q.source_quality_cells=cells
            self.assertIsNone(q.quality_witness(at))
            marks(a,at+E.MINUTE)
            self.assertEqual({r['symbol'] for r in q.quality_witness(at+E.MINUTE)['affected_source_cells']},{'BTCUSDT'})
            marks(a,at+2*E.MINUTE)
            self.assertEqual({r['symbol'] for r in q.quality_witness(at+2*E.MINUTE)['affected_source_cells']},{'ETHUSDT'})
            self.assertIsNotNone(q.quality_witness(at+5*E.MINUTE))
            marks(a,at+3*E.MINUTE,selected=('ETHUSDT',))
            self.assertIsNone(q.quality_witness(at+3*E.MINUTE))

    def test_unknown_quality_preserves_legitimate_pending_and_does_not_create_new_warning(self):
        a=account();initial(a);at=2*E.MINUTE;marks(a,at,75000);a.monitor('MONITOR:'+str(at),at)
        intent=deepcopy(a.pending_exits);self.assertIn('BTCUSDT',intent)
        a._quality_intervals=((at+E.MINUTE,at+3*E.MINUTE,E.S),)
        for k in (1,2):
            marks(a,at+k*E.MINUTE,75000);a.monitor('MONITOR:'+str(at+k*E.MINUTE),at+k*E.MINUTE)
            self.assertEqual(a.pending_exits,intent);self.assertFalse(a.can_increase(at+k*E.MINUTE))
        self.assertFalse(a.transfer_journal)

    def test_native_liquidation_cancels_only_affected_pending_and_new_signal_required(self):
        with g.generated_fixture(days=1) as f:
            t=g.project_generated(f);sim,guard=g.construct_generated_case(t,'MID');a=sim.account;start=sim.start
            initial(a,start);at=start+2*E.MINUTE
            guard.original_schedule(dict.fromkeys(E.S,Q('.001')),start,'DAILY',('BTCUSDT','ETHUSDT'))
            marks(a,at,100000)
            self.assertNotIn('BTCUSDT',sim.pending);self.assertIn('ETHUSDT',sim.pending)
            self.assertIn('BTCUSDT',a.blocked_signals);self.assertGreaterEqual(a.blocked_signals['BTCUSDT'],start)
            self.assertFalse(a.economic_report()['paid_flat']);self.assertEqual(len(a.settlement_journal),1)
            self.assertFalse(a.transfer_journal)

    def test_CS_daily_signal_inside_gap_preserves_exact_original_D_native_path(self):
        with g.generated_fixture(days=2) as f:
            t=g.project_generated(f);window,rows,decisions=g._synthetic_window(f)
            decision=int(decisions[1]);start,end=decision-2*E.MINUTE,decision+3*E.MINUTE
            intervals=((start,end,E.S),)
            old,og=E.D.construct_case(window,rows,decisions,t.common_tier['MID'],generated_scope=E.GENERATED,
                                     quality_intervals=intervals)
            new,ng=g.construct_generated_case(t,'MID',quality_intervals=intervals)
            for sim in (old,new):
                sim.pending_trace=[];original=sim.risk_schedule
                def observe(at,*,sim=sim,original=original):
                    result=original(at);sim.pending_trace.append((at,deepcopy(sim.pending)));return result
                sim.risk_schedule=observe
                while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
            self.assertEqual(finance(old.account),finance(new.account))
            self.assertEqual(old.pending_trace,new.pending_trace)
            self.assertFalse(any(start<=r['event_us']<end and r['leg']=='OPEN' for r in new.account.trades))
            self.assertTrue(any(r['signal_us']==decision and r['event_us']>=end for r in new.account.trades))
            self.assertTrue(any(r['leg']=='CLOSE' for r in new.account.trades));self.assertGreater(new.account.fees,Q(0))
            self.assertFalse(new.account.pending_exits);self.assertFalse(new.account.transfer_journal)

    def test_full_CS_generated_calendar_positive_paid_opens_reductions_and_saved_native40(self):
        path=ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
        sys.path.insert(0,str(path))
        from saved_native_reconciliation import reconcile_saved_native
        with g.generated_fixture(days=2) as f:
            t=g.project_generated(f)
            for tier in E.TIERS:
                sim,guard=g.construct_generated_case(t,tier)
                while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertIsNone(sim.stop);self.assertGreater(sim.account.fees,Q(0))
                self.assertTrue(any(r['leg']=='OPEN' for r in sim.account.trades))
                self.assertTrue(any(r['leg']=='CLOSE' for r in sim.account.trades))
                self.assertTrue(sim.terminal);self.assertTrue(any(r['signal_us']==sim.terminal_signal_us and r['leg']=='CLOSE' for r in sim.account.trades))
                result=E.case_result(sim,guard);result.pop('minute');result['targets']=result['targets'].to_dicts()
                result=E.V2.OWNED.export_tree(result);audit=E.V2.OWNED.export_tree(sim.account.snapshot())
                proof=reconcile_saved_native(audit,result)
                self.assertTrue(proof['passed']);self.assertFalse(proof['tolerance_or_epsilon_used'])
                bad=deepcopy(audit);bad['free_cash']='123'
                with self.assertRaisesRegex(ValueError,'FINAL_NATIVE_CASH_DEBT_MISMATCH'):
                    reconcile_saved_native(bad,result)
                self.assertFalse(sim.account.transfer_journal)
                self.assertFalse(result['economics']['actual_historical_liquidation_or_no_liquidation_certified'])
                self.assertEqual(result['economics']['source27_event_and_position_interval_impact'],'PENDING_ACTUAL_SAVED_EVIDENCE')

if __name__=='__main__':unittest.main(verbosity=2)

import unittest
import numpy as np
from decimal import localcontext
from generated_fixtures import new_sim,finish,make,original_csh,START
from native_adapter import D,ZERO,S,BTC,DAY,M,H,NATIVE


class NativeTests(unittest.TestCase):
 def test_control_adapter_native_exact_finance_parity(self):
  direct=finish(new_sim('CONTROL',direct=True));adapted=finish(new_sim('CONTROL'))
  self.assertEqual(direct.account.snapshot(),adapted.account.snapshot())
  self.assertEqual(direct.account.trades,adapted.account.trades)
  self.assertEqual(direct.funding_journal,adapted.funding_journal)
  np.testing.assert_array_equal(direct.minute_chunks[0],adapted.minute_chunks[0])

 def test_cash_controls_native_paid_and_equal_costs(self):
  direct=finish(new_sim('CASH',direct=True));adapted=finish(new_sim('CASH'))
  self.assertEqual(direct.account.nav(),adapted.account.nav())
  self.assertEqual(direct.account.fees,adapted.account.fees)
  self.assertEqual(direct.account.execution_cost,adapted.account.execution_cost)
  self.assertEqual(direct.account.funding_cash,adapted.account.funding_cash)
  self.assertTrue(adapted.result()['summary']['terminal_cash_realized'])

 def test_grid_one_shared_account_actual_paid_inventory(self):
  sim=finish(new_sim('GRID'))
  self.assertEqual(sim.account.config.initial_cash,D('10000'))
  self.assertEqual(tuple(sim.account.positions),S)
  self.assertTrue(any(a['owner']=='GRID' for a in sim.allocations))
  self.assertTrue(any(r['symbol']==S[-1] and r['side']=='SELL' and r['leg']=='OPEN' for r in sim.account.trades))
  self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
  self.assertEqual(sim.base_btc,ZERO)
  self.assertEqual(sim.grid.inventory() if sim.grid else ZERO,ZERO)

 def test_fee_friction_and_funding_attribution_native_exact(self):
  sim=finish(new_sim('GRID'))
  with localcontext() as ctx:
   ctx.prec=40
   self.assertEqual(sum((D(a['fee']) for a in sim.allocations),ZERO),sim.account.fees)
   self.assertEqual(sum((D(a['execution_cost']) for a in sim.allocations),ZERO),sim.account.execution_cost)
   self.assertEqual(sum((D(a['cash']) for a in sim.funding_allocations),ZERO),sim.account.funding_cash)
  self.assertLessEqual(abs(D(sim.account.summary()['decimal_strings']['accounting_bridge_error_USDT'])),D('1e-20'))

 def test_partial_fill_shared_capacity_and_ownership(self):
  sim=finish(new_sim('GRID','PARTIAL'))
  self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
  self.assertTrue(any(r.get('status')=='PARTIAL' for r in sim.rejections))
  gridq=H.FixedGrid(sim.daily_closes[START],START,H.CompletedMinute(START,D(100),START),D(198)).quantity
  self.assertTrue(any(a['owner']=='GRID' and ZERO<D(a['quantity'])<gridq for a in sim.allocations))
  self.assertTrue(any(e['kind']=='GRID_CAPACITY_ADMISSION_BLOCKED' for e in sim.policy_events))
  sim._reconcile()

 def test_sign_change_settles_grid_before_btc_short(self):
  sim=finish(new_sim('GRID','SIGN_FLIP'))
  self.assertTrue(any('SIGN_CHANGE' in e.get('reason','') for e in sim.policy_events))
  self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
  self.assertTrue(any(r['symbol']==BTC and r['side']=='SELL' and r['leg']=='OPEN' for r in sim.account.trades))
  sim._reconcile()

 def test_terminal_residual_never_free_clear(self):
  sim=finish(new_sim('GRID','TERMINAL_RESIDUAL'))
  self.assertFalse(sim.result()['summary']['terminal_cash_realized'])
  self.assertGreater(sim.account.summary()['gross_notional'],0)
  sim._reconcile()

 def test_original_csh_source_executes_only_generated_arrays(self):
  t,p,w,cov=original_csh(1)
  self.assertEqual(w.shape,(1,5));self.assertEqual(cov.shape,(1,5,5))
  sim=finish(new_sim('CONTROL','ORIGINAL_CSH'))
  self.assertIn('ORIGINAL_CSH_FUNCTIONS',sim.meta['source'])
  self.assertEqual(sim.account.config.leverage,D(1))

 def test_neutral_target_replacement_ineligible_preserves_original(self):
  candidate=finish(new_sim('GRID','NEUTRAL'));control=finish(new_sim('CONTROL','NEUTRAL',direct=True))
  self.assertFalse(any(a['owner']=='GRID' for a in candidate.allocations))
  self.assertEqual(candidate.account.snapshot(),control.account.snapshot())
  self.assertTrue(any('ABS_NET_ORIGINAL_TARGET' in e.get('reasons',[]) for e in candidate.policy_events))

 def test_unknown_covariance_and_bad_range_preserve_original(self):
  for name in ('UNKNOWN_COV','BAD_RANGE'):
   candidate=finish(new_sim('GRID',name));control=finish(new_sim('CONTROL',name,direct=True))
   self.assertFalse(any(a['owner']=='GRID' for a in candidate.allocations))
   self.assertEqual(candidate.account.snapshot(),control.account.snapshot())

 def test_unrelated_asset_exit_keeps_cash_trim(self):
  sim=new_sim('CASH');target={s:ZERO for s in S};target[BTC]=D('19.8')
  kinds=dict.fromkeys(S,'DAILY_TARGET');kinds[S[-1]]='POOL_EXIT'
  sim.schedule(target,START,kinds)
  self.assertEqual(sim.pending[BTC]['target'],D('17.82'))

 def test_vertex_reversal_cash_and_net_are_fail_closed(self):
  sim=new_sim('GRID');sim.original_target={s:ZERO for s in S};sim.original_target[BTC]=D('20');sim.original_target[S[-1]]=D('-20')
  sim.pending[S[-1]]=dict(target=D('20'),order_id='toy-reversal')
  good,witness=sim._reservation()
  self.assertFalse(good)
  self.assertIn('ABS_NET_ORIGINAL_TARGET',witness['reasons'])
  self.assertGreater(D(witness['cash_required']),0)

 def test_hard_risk_never_restores_obsolete_base(self):
  sim=finish(new_sim('GRID','RISK_GAP'))
  self.assertTrue(sim.breaches)
  first=sim.breaches[0]['signal_us']
  self.assertFalse(any(r['symbol']==BTC and r['leg']=='OPEN' and r['event_us']>first for r in sim.account.trades))
  self.assertFalse(sim.restore_base_after_settlement)
  sim._reconcile()

 def test_weekly_reset_uses_paid_old_session_settlement(self):
  sim=finish(new_sim('GRID','WEEK_RESET'))
  events=[e for e in sim.policy_events if e.get('reason') in ('SIGN_CHANGE_OR_WEEKLY_RESET','FIXED_WEEK_END')]
  self.assertTrue(any(e['event_us']==START+7*DAY for e in events))
  self.assertGreaterEqual(len({e['session_id'] for e in sim.policy_events if e['kind']=='GRID_SESSION_ACTIVATED'}),2)
  self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
  sim._reconcile()

 def test_paid_flat_weekly_expiry_clears_only_settled_session(self):
  sim=finish(new_sim('GRID','FLAT_WEEK_RESET'))
  bound=[e for e in sim.policy_events if e['kind']=='GRID_SESSION_ACTIVATED']
  self.assertGreaterEqual(len({e['session_id'] for e in bound}),2)
  self.assertTrue(any(e['event_us']>START+7*DAY for e in bound))
  expired=[e for e in sim.policy_events if e.get('reason')=='FIXED_WEEK_END']
  self.assertEqual(len(expired),1)
  self.assertEqual(D(expired[0]['owned']),ZERO)
  sim._reconcile()

 def test_binding_and_duplicate_attempt_reject_before_finance(self):
  sim=new_sim('GRID');closes=sim.daily_closes[START]
  sim.grid=H.FixedGrid(closes,START,H.CompletedMinute(START,D(100),START),D(198))
  intents=sim.grid.intents(START+M,H.CompletedMinute(START+M,D(100),START+M))
  target=sum((i.quantity for i in intents),ZERO)
  NATIVE.schedule(sim,{BTC:target},START+M,'DAILY_TARGET',only_symbols=(BTC,))
  sim.binding=dict(native_order=sim.pending[BTC]['order_id'],intents=intents,session_id='obsolete-session')
  before=sim.account.snapshot()
  with self.assertRaisesRegex(ValueError,'STALE_HELPER_BINDING_BEFORE_FINANCE'):
   sim.attempt(START+2*M,{s:dict(open=100.) for s in S})
  self.assertEqual(before,sim.account.snapshot())
  sim=new_sim('GRID');sim.attempt(START,{s:dict(open=100.) for s in S});before=sim.account.snapshot()
  with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_REWOUND_NATIVE_ATTEMPT'):
   sim.attempt(START,{s:dict(open=100.) for s in S})
  self.assertEqual(before,sim.account.snapshot())

 def test_initial_observation_missing_is_original_target_fallback(self):
  candidate=new_sim('GRID');candidate.initial_observations={};finish(candidate)
  control=finish(new_sim('CONTROL',direct=True))
  self.assertEqual(candidate.account.snapshot(),control.account.snapshot())
  self.assertFalse(any(a['owner']=='GRID' for a in candidate.allocations))

 def test_additional_serial_differential_controls(self):
  for name in ('PARTIAL','SIGN_FLIP','RISK_GAP','TERMINAL_RESIDUAL','ORIGINAL_CSH'):
   for arm in ('CONTROL','CASH'):
    direct=finish(new_sim(arm,name,direct=True));adapted=finish(new_sim(arm,name))
    self.assertEqual(direct.account.snapshot(),adapted.account.snapshot(),(name,arm))
    self.assertEqual(direct.account.trades,adapted.account.trades,(name,arm))

 def test_actual_point99_collar_minimum_failure_is_fallback(self):
  candidate=new_sim('GRID');control=new_sim('CONTROL',direct=True)
  for sim in (candidate,control):sim.weights[START]=dict(zip(S,[.0492,0.,0.,0.,0.]))
  finish(candidate);finish(control)
  self.assertEqual(candidate.account.snapshot(),control.account.snapshot())
  self.assertTrue(any(e.get('reason')=='opening minimum notional cannot be met' for e in candidate.policy_events))
  self.assertFalse(any(a['owner']=='GRID' for a in candidate.allocations))

 def test_restore_and_fork_explicit_blockers(self):
  sim=new_sim('GRID')
  with self.assertRaisesRegex(ValueError,'RESTORE_NOT_IMPLEMENTED'):sim.from_snapshot({})
  with self.assertRaisesRegex(ValueError,'FORK_NOT_IMPLEMENTED'):sim.fork()

if __name__=='__main__':unittest.main(verbosity=2)

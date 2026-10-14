import unittest
import importlib.util,os,py_compile,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from decimal import Decimal as D
from native_adapter import (PAIRED,LEGACY,ComparisonTape,S,M,DAY,NATIVE,PairedNativeAdapter,HALTS)
from generated_fixtures import new,finish,make,START,original_csh

class Tests(unittest.TestCase):
 def equal_finance(self,a,b):
  self.assertEqual(a.account.snapshot(),b.account.snapshot())
  for name in ('funding_journal','pending','rejections','breaches','target_rows','completion','stop','sequence','event_cursor'):
   self.assertEqual(getattr(a,name),getattr(b,name),name)
  for x,y in zip(a.minute_chunks,b.minute_chunks,strict=True):np.testing.assert_array_equal(x,y)
 def test_disabled_exact_original_terminal60(self):
  for fixture in ('FLAT','DISJOINT','TERMINAL_ZERO','TERMINAL_COMPLETE','HARD_RISK','HALT','ORIGINAL_CSH'):
   with self.subTest(fixture=fixture):self.equal_finance(finish(new('disabled',fixture)),finish(new('disabled',fixture,True)))
 def test_legacy_original_hook_finance_parity_without_collision(self):
  for fixture in ('FLAT','DISJOINT','COINCIDENT','MASKED','TERMINAL_ZERO','TERMINAL_LATE','TERMINAL_COMPLETE','HALT','HARD_RISK','SIGN_LOCK'):
   with self.subTest(fixture=fixture):
    a=finish(new('legacy_shared_priority_fixed',fixture));b=finish(new('legacy_shared_priority_fixed',fixture,True))
    self.equal_finance(a,b);self.assertEqual(a.protective_events,b.protective_events)
    self.assertEqual(a.protective_locks,b.protective_locks)
 def test_disjoint_extremes_coupling_changes_paid_wallet(self):
  sims={a:finish(new(a,'DISJOINT')) for a in ('legacy_shared_priority_fixed','aligned_independent','paired')}
  self.assertEqual(len(sims['legacy_shared_priority_fixed'].protective_locks),1)
  self.assertEqual(len(sims['aligned_independent'].protective_locks),1)
  self.assertEqual(sims['paired'].protective_locks,{})
  self.equal_finance(sims['legacy_shared_priority_fixed'],sims['aligned_independent'])
  legacy=sims['legacy_shared_priority_fixed'];event=legacy.protective_events[0]
  self.assertEqual(event['event_us'],START+2*M)
  self.assertEqual(legacy.account.trades[1]['event_us'],START+3*M+1)
  self.assertNotEqual(sims['paired'].account.trades[1]['event_us'],legacy.account.trades[1]['event_us'])
  self.assertGreater(legacy.account.fees,D(0));self.assertGreater(legacy.account.execution_cost,D(0))
 def test_coincident_extremes_both_trigger(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'COINCIDENT'));self.assertEqual(len(sim.protective_locks),1)
 def test_common_derived_mask_prevents_all_signals(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'MASKED'));self.assertFalse(sim.protective_locks)
   self.assertGreater(sim.headroom_coverage[S[0]]['not_ready_invested_hook_evaluations'],0)
 def test_terminal60_supersedes_protective_and_no_revive(self):
  sim=finish(new('legacy_shared_priority_fixed','TERMINAL_ZERO'))
  expiry=[r for r in sim.rejections if r.get('reason')=='SIXTY_TERMINAL_ATTEMPTS_EXPIRED' and r['symbol']==S[0]]
  self.assertEqual(len(expiry),1);self.assertEqual(expiry[0]['event_us'],sim.end-M+1)
  self.assertNotIn(S[0],sim.pending);self.assertNotEqual(sim.account.positions[S[0]].quantity,0)
  self.assertFalse(sim.result()['summary']['terminal_cash_realized'])
  self.assertGreater(sim.protective_locks[S[0]]['deferred_no_lot_minutes'],5)
 def test_terminal_late_partials_are_paid_and_capacity_limited(self):
  sim=finish(new('legacy_shared_priority_fixed','TERMINAL_LATE'))
  late=[r for r in sim.account.trades if r['event_us']>sim.end-12*M]
  self.assertGreater(len(late),5)
  self.assertTrue(all(D(r['decimal_strings']['quantity'])<=D('.1') for r in late))
  self.assertNotEqual(sim.account.positions[S[0]].quantity,0)
  self.assertFalse(sim.result()['summary']['terminal_cash_realized'])
 def test_generated_pending_cap_collision_witness_and_shared_fix(self):
  fixed=finish(new('legacy_shared_priority_fixed','CAP_COLLISION'))
  unfixed=finish(new('legacy_shared_priority_fixed','CAP_COLLISION',True))
  original=finish(new('disabled','CAP_COLLISION',True))
  self.assertEqual(fixed.stop,original.stop)
  self.assertEqual(len(fixed.breaches),1);self.assertEqual(len(unfixed.breaches),2)
  self.assertEqual(unfixed.stop-fixed.stop,2*M)
  self.assertEqual(fixed.completion,'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
  self.assertTrue(any(r.get('reason')=='SUPERSEDED_BY_PROTECTIVE_STOP' and r['event_us']==START+22*M for r in unfixed.rejections))
  self.assertFalse(any(r.get('reason')=='SUPERSEDED_BY_PROTECTIVE_STOP' and r['event_us']==START+22*M for r in fixed.rejections))
  for arm in ('aligned_independent','paired'):
   sim=finish(new(arm,'CAP_COLLISION'))
   self.equal_finance(sim,fixed)
   self.assertEqual(sim.protective_locks,fixed.protective_locks)
   keys=('kind','symbol','event_us','quantity','mark','isolated_balance','isolated_equity')
   self.assertEqual([{k:r.get(k) for k in keys} for r in sim.protective_events],[{k:r.get(k) for k in keys} for r in fixed.protective_events])
 def test_pending_cap_order_identity_signal_target_and_attempts_retained(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=new(arm,'CAP_COLLISION');captured=[];original=sim.risk_schedule
   def witness(stamp):
    order=sim.pending.get(S[0]);before=None
    if order and order['kind']=='RISK_REDUCTION':before=dict(order)
    original(stamp)
    if before is not None and any(r['kind']=='FULL_EXIT_SIGNAL' and r['event_us']==stamp for r in sim.protective_events):
     captured.append((order,dict(sim.pending[S[0]]),before,sim.pending[S[0]] is order))
   sim.risk_schedule=witness;sim.advance_day()
   self.assertEqual(len(captured),1)
   _,after,before,identity=captured[0];self.assertTrue(identity);self.assertEqual(after,before)
   self.assertEqual(after['signal_us'],START+21*M);self.assertEqual(after['attempts'],0)
   self.assertNotEqual(after['target'],0)
 def test_pending_cap_partial_capacity_paid_without_clock_reset(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'CAP_COLLISION_PARTIAL'));ref=finish(new('disabled','CAP_COLLISION_PARTIAL',True))
   self.equal_finance(sim,ref);self.assertEqual(sim.stop,START+26*M+1)
   self.assertEqual(len(sim.breaches),1)
   closes=[r for r in sim.account.trades if r['leg']=='CLOSE']
   self.assertEqual(len(closes),3)
   self.assertTrue(all(r['signal_us']==START+21*M for r in closes))
   self.assertTrue(all(D(r['decimal_strings']['quantity'])<=D(50)/D(121) for r in closes))
   self.assertTrue(all(D(r['decimal_strings']['fee_amount'])>0 for r in closes))
   self.assertNotEqual(sim.account.positions[S[0]].quantity,0)
   self.assertIsNone(sim.protective_locks[S[0]]['flat_us'])
   self.assertEqual(sim.completion,'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
 def test_cap_resolves_then_original_protection_paid_full_close(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'CAP_COLLISION_PAID'))
   self.assertIsNone(sim.stop);self.assertEqual(len(sim.breaches),1)
   self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
   self.assertIsNotNone(sim.protective_locks[S[0]]['flat_us'])
   self.assertLess(sim.protective_locks[S[0]]['flat_us'],sim.terminal_signal_us)
   closes=[r for r in sim.account.trades if r['leg']=='CLOSE']
   self.assertGreaterEqual(len(closes),2)
   self.assertEqual(closes[0]['signal_us'],START+21*M)
   self.assertEqual(closes[0]['event_us'],START+24*M+1)
   self.assertEqual(closes[1]['signal_us'],closes[0]['event_us'])
   self.assertEqual(closes[1]['event_us'],closes[0]['event_us']+2*M)
   self.assertTrue(all(D(r['decimal_strings']['fee_amount'])>0 for r in closes))
 def test_terminal_paid_close_records_flat_without_rescheduling(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent'):
   sim=finish(new(arm,'TERMINAL_COMPLETE'))
   self.assertTrue(sim.result()['summary']['terminal_cash_realized'])
   lock=sim.protective_locks[S[0]]
   self.assertIsNotNone(lock['flat_us']);self.assertGreater(lock['flat_us'],sim.terminal_signal_us)
   events=[r for r in sim.protective_events if r['kind']=='FULL_EXIT_FLAT']
   self.assertEqual(len(events),1);self.assertEqual(events[0]['event_us'],lock['flat_us'])
   self.assertFalse(sim.pending)
   terminal=[r for r in sim.account.trades if r['signal_us']==sim.terminal_signal_us]
   self.assertGreater(len(terminal),5)
   self.assertTrue(all(D(r['decimal_strings']['fee_amount'])>0 for r in terminal))
   self.assertEqual(sim.result()['protective_policy']['terminal_opens'],60)
 def test_original_hard_risk_five_attempt_stop_unchanged(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'HARD_RISK'));ref=finish(new('disabled','HARD_RISK',True))
   self.equal_finance(sim,ref)
   self.assertEqual(sim.completion,'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
   self.assertEqual(sim.stop,START+26*M+1)
   self.assertFalse(sim.protective_locks);self.assertEqual(len(sim.breaches),1)
   self.assertTrue(any(r.get('kind')=='RISK_REDUCTION' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for r in sim.rejections))
 def test_same_sign_daily_reentry_locked_and_neutral_resets(self):
  sim=new('legacy_shared_priority_fixed','SIGN_LOCK');sim.advance_day()
  self.assertEqual(sim.account.positions[S[0]].quantity,0)
  n=len(sim.account.trades);lock=sim.protective_locks[S[0]]
  self.assertIsNotNone(lock['flat_us'])
  sim.schedule({S[0]:D(-10)},START+DAY,'DAILY_TARGET',only_symbols=(S[0],))
  self.assertNotIn(S[0],sim.pending)
  sim.schedule({S[0]:D(0)},START+DAY,'RISK_REDUCTION',only_symbols=(S[0],))
  self.assertIn(S[0],sim.protective_locks)
  sim.schedule({S[0]:D(0)},START+DAY,'DAILY_TARGET',only_symbols=(S[0],))
  self.assertNotIn(S[0],sim.protective_locks)
  self.assertEqual(len(sim.account.trades),n)
  self.assertEqual(sim.protective_events[-1]['kind'],'RESET_BY_NEW_DAILY_DIRECTION')
 def test_own_asset_equity_mark_quantity_not_free_cash(self):
  for arm in ('aligned_independent','paired'):
   observed=[];original=PAIRED.assess
   def witness(q,e,mark,**features):
    observed.append((q,e,mark,dict(features)))
    return original(q,e,mark,**features)
   sim=new(arm,'DISJOINT')
   with patch.object(PAIRED,'assess',side_effect=witness):sim.advance_day()
   self.assertGreater(len(observed),0)
   q,e,mark,_=observed[0]
   entry=sim.account.trades[0]['decimal_strings']
   self.assertEqual(q,-float(D(entry['quantity'])))
   self.assertEqual(mark,100.)
   expected=D(entry['margin_allocated'])-D(entry['quantity'])*(D(100)-D(entry['fill_price']))
   # Positive short funding enters free cash; isolated collateral is unchanged.
   self.assertAlmostEqual(e,float(expected),places=10)
   self.assertNotEqual(e,float(sim.account.free_cash))
   self.assertEqual(sim.headroom_coverage[S[1]]['ready_invested_hook_evaluations'],0)
 def test_heterogeneous_ownership_and_later_same_clock_debit(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   observed=[];original=LEGACY.assess if arm=='legacy_shared_priority_fixed' else PAIRED.assess
   module=LEGACY if arm=='legacy_shared_priority_fixed' else PAIRED
   # Original HEADROOM imported assess by value; patch that exact hook alias.
   if arm=='legacy_shared_priority_fixed':
    module=LEGACY
   sim=new(arm,'OWNERSHIP')
   def witness(q,e,mark,**features):
    observed.append(dict(cursor=sim.event_cursor,q=q,e=e,mark=mark,features=dict(features)))
    return original(q,e,mark,**features)
   with patch.object(module,'assess',side_effect=witness):sim.advance_day()
   first=observed[:2];self.assertEqual([x['cursor'] for x in first],[2,2])
   self.assertEqual([x['mark'] for x in first],[100.,200.])
   self.assertLess(first[0]['q'],0);self.assertGreater(first[1]['q'],0)
   self.assertNotEqual(abs(first[0]['q']),abs(first[1]['q']))
   entries={r['symbol']:r['decimal_strings'] for r in sim.account.trades[:2]}
   funds=sim.funding_journal[:2]
   self.assertTrue(all(r['owned'] for r in funds))
   self.assertTrue(all(r['mark_close_us']==START+M for r in funds))
   self.assertEqual([r['event_us'] for r in funds],[START+2*M]*2)
   e0=entries[S[0]];e1=entries[S[1]]
   free=D(10000)-sum(D(x['margin_allocated'])+D(x['fee_amount']) for x in entries.values())
   credit=D(funds[0]['decimal_strings']['signed_funding_USDT']);debit=-D(funds[1]['decimal_strings']['signed_funding_USDT'])
   self.assertGreater(debit,free+credit)
   own_balance=D(e1['margin_allocated'])-(debit-free-credit)
   expected0=D(e0['margin_allocated'])+D(e0['position_delta'])*(D(100)-D(e0['fill_price']))
   expected1=own_balance+D(e1['position_delta'])*(D(200)-D(e1['fill_price']))
   self.assertEqual(first[0]['e'],float(expected0));self.assertEqual(first[1]['e'],float(expected1))
   self.assertEqual(first[0]['q'],float(D(e0['position_delta'])))
   self.assertEqual(first[1]['q'],float(D(e1['position_delta'])))
 def test_later_same_clock_funding_halt_prevents_every_headroom_signal(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'OWNERSHIP_HALT'))
   self.assertIn(sim.account.status,HALTS);self.assertEqual(sim.stop,START+2*M)
   self.assertEqual(sim.event_cursor,2);self.assertEqual(len(sim.funding_journal),2)
   self.assertTrue(all(r['owned'] for r in sim.funding_journal))
   self.assertTrue(all(r['mark_close_us']==START+M for r in sim.funding_journal))
   self.assertFalse(sim.protective_events);self.assertFalse(sim.protective_locks)
   self.assertEqual(sum(r['ready_invested_hook_evaluations'] for r in sim.headroom_coverage.values()),0)
 def test_original_fine_profile_and_paid_cost_constants(self):
  sim=finish(new('disabled','FLAT'))
  for p in sim.account.instrument_profiles.values():
   self.assertEqual(p.quantity_step,D('1e-8'));self.assertEqual(p.min_notional,D(10))
  self.assertEqual(sim.account.config.fee_rate,D('.00055'))
  for r in sim.account.trades:
   d=r['decimal_strings'];self.assertEqual(D(d['fee_amount']),D(d['quantity'])*D(d['fill_price'])*D('.00055'))
   self.assertEqual(D(d['quantity'])%D('1e-8'),0)
 def test_original_halt_dominates_no_rescue(self):
  for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
   sim=finish(new(arm,'HALT'));self.assertIn(sim.account.status,HALTS)
   self.assertFalse(sim.protective_locks);self.assertEqual(sim.stop,START+21*M)
 def test_same_clock_funding_all_consumed_before_signal(self):
  sim=finish(new('legacy_shared_priority_fixed','DISJOINT'))
  event=sim.protective_events[0];self.assertEqual(event['event_us'],START+2*M)
  funds=[r for r in sim.funding_journal if r['event_us']==event['event_us']]
  self.assertEqual(len(funds),2)
  # Short funding is credited to shared free cash, never mislabeled collateral.
  self.assertEqual(D(event['isolated_balance']),D(sim.account.trades[0]['decimal_strings']['margin_allocated']))
  self.assertEqual(funds[0]['mark_close_us'],START+M)
  self.assertGreater(D(funds[0]['decimal_strings']['signed_funding_USDT']),0)
  entry=sim.account.trades[0]['decimal_strings']
  self.assertEqual(D(event['isolated_equity']),D(event['isolated_balance'])+D(event['quantity'])*(D(event['mark'])-D(entry['fill_price'])))
 def test_original_target_covariance_and_caps(self):
  w,cov=original_csh();self.assertLessEqual(np.abs(w).sum(),.6+1e-12)
  self.assertLessEqual(np.abs(w).max(),.3+1e-12);self.assertLessEqual(np.sqrt(w@cov@w),.10+1e-12)
 def test_long_counterexample_no_universal_order(self):
  a=np.log([.5,1.]);g=np.log([1.,.0001])
  paired=float(np.max(PAIRED.pair_hurdles(a,g)['long']))
  independent=2-float(LEGACY.assess(1,2,1,float(min(a)),0,float(min(g)),0)['buffered_headroom'])
  self.assertGreater(paired,independent)
 def test_endpoint_alignment_is_separate(self):
  n=43201;t=np.arange(n,dtype=np.int64)*M;p=np.full(n,100.);o=p.copy();p[-1]=200.
  f=PAIRED.features(t,p,o)
  self.assertGreater(f['legacy_independent_short_hurdle'][-1],f['aligned_independent_short_hurdle'][-1])
  self.assertEqual(f['aligned_independent_short_hurdle'][-1],f['short_hurdle'][-1])
 def test_inclusive_boundary_and_nonfinite_refusal(self):
  k=PAIRED.pair_hurdles(0.,0.);e=100*float(k['short'])
  self.assertTrue(PAIRED.assess(-1,e,100,k['long'],k['short'])['trigger'])
  with self.assertRaises(ValueError):PAIRED.assess(1e308,1,10,k['long'],k['short'])
 def test_raw_source_compile_bypasses_timestamp_valid_stale_pyc(self):
  import bind_native
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as d:
   path=Path(d)/'generated_stale.py';source="def answer():\n return 'SOURCE'\n";poison=source.replace('SOURCE','POISON')
   path.write_text(poison);os.utime(path,(1_000_000_000,1_000_000_000));py_compile.compile(str(path),doraise=True)
   path.write_text(source);os.utime(path,(1_000_000_000,1_000_000_000))
   spec=importlib.util.spec_from_file_location('generated_stale_positive_control',path)
   cached=importlib.util.module_from_spec(spec);spec.loader.exec_module(cached)
   self.assertEqual(cached.answer(),'POISON')
   name='generated_raw_compile_negative_control'
   try:
    module=bind_native.exact(name,path);self.assertEqual(module.answer(),'SOURCE')
    self.assertEqual(bind_native.EXECUTED_SOURCE[name]['raw_source_SHA256'],bind_native.sha(path))
   finally:
    sys.modules.pop(name,None);bind_native.EXECUTED_SOURCE.pop(name,None)
 def test_legacy_assessment_alias_and_native_executed_closure(self):
  import bind_native
  from native_adapter import HEADROOM,ACCOUNT,TERMINAL
  self.assertIs(HEADROOM.assess,LEGACY.assess)
  self.assertEqual(ACCOUNT.__module__,'fine_account');self.assertEqual(TERMINAL.__module__,'terminal_adapter')
  for name in ('headroom_buffer','feature_tape','protective_policy','headroom_policy','vendor.headroom_buffer','paired_buffer'):
   r=bind_native.EXECUTED_SOURCE[name]
   self.assertEqual(r['mechanism'],'COMPILE_PINNED_RAW_SOURCE_NO_PYC')
   self.assertEqual(r['raw_source_SHA256'],bind_native.sha(bind_native.ROOT/r['path']))
 def test_generated_only_and_restore_refused(self):
  with self.assertRaises(ValueError):new('paired').snapshot()
  window,factory=make();bad=dict(window,fixture_scope='HISTORICAL')
  from native_adapter import PORT
  with self.assertRaises(ValueError):PairedNativeAdapter(bad,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],arm='paired',target_factory=factory)

if __name__=='__main__':unittest.main(verbosity=2)

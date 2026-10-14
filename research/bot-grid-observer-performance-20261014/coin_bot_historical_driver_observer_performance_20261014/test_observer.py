"""Pure exact Decimal prefix, composed immutability and transaction regressions."""
from decimal import Decimal as D,localcontext,InvalidOperation
from types import SimpleNamespace
from unittest import TestCase
from native_adapter import GridNativeAdapter,OwnerAuditLedger,BTC,ZERO

class ObserverTests(TestCase):
 def fake(self):
  sim=GridNativeAdapter.__new__(GridNativeAdapter);sim.allocations=OwnerAuditLedger();sim.funding_allocations=OwnerAuditLedger();sim._owner_allocation_ledger=sim.allocations;sim._owner_funding_ledger=sim.funding_allocations;sim._owner_allocation_count=sim._owner_funding_count=0;sim._owner_fee_total=sim._owner_cost_total=sim._owner_funding_total=ZERO;sim.grid=None;sim.base_btc=ZERO;sim.account=SimpleNamespace(fees=ZERO,execution_cost=ZERO,funding_cash=ZERO,positions={BTC:SimpleNamespace(quantity=ZERO)});return sim
 def test_prefix_matches_full_ctx40_fold_in_exact_order(self):
  sim=self.fake();fees=['1E40','1E-39','-1E40','1.234567890123456789012345678901234567890123'];costs=['.1234567890123456789012345678901234567890','.000000000000000000000000000000000000001','1E-39','.00001']
  for i,(f,c) in enumerate(zip(fees,costs)):
   sim._record_owner_fill(dict(native_leg=[i,'OPEN',1],fee=f,execution_cost=c))
   with localcontext() as ctx:
    ctx.prec=40
    self.assertEqual(sim._owner_fee_total,sum((D(x) for x in fees[:i+1]),ZERO));self.assertEqual(sim._owner_cost_total,sum((D(x) for x in costs[:i+1]),ZERO))
 def test_public_and_base_builtin_mutations_refused(self):
  sim=self.fake();sim._record_owner_fill(dict(native_leg=[1,'OPEN',1],fee='0',execution_cost='0'));row=sim.allocations[0]
  for action in (lambda:dict.__setitem__(row,'fee','1'),lambda:list.__setitem__(sim.allocations,0,{}),lambda:list.__setitem__(row['native_leg'],0,99),lambda:sim.allocations.clear()):
   with self.assertRaises((TypeError,ValueError)):action()
 def test_fill_parse_failure_commits_nothing(self):
  sim=self.fake()
  with self.assertRaises(InvalidOperation):sim._record_owner_fill(dict(fee='1',execution_cost='bad'))
  self.assertEqual((len(sim.allocations),sim._owner_allocation_count,sim._owner_fee_total,sim._owner_cost_total),(0,0,ZERO,ZERO))
 def test_second_funding_parse_failure_commits_nothing(self):
  sim=self.fake()
  with self.assertRaises(InvalidOperation):sim._record_owner_funding([dict(cash='1'),dict(cash='bad')])
  self.assertEqual((len(sim.funding_allocations),sim._owner_funding_count,sim._owner_funding_total),(0,0,ZERO))
 def test_replaced_or_private_appended_ledger_refused(self):
  sim=self.fake();original=sim.allocations;sim.allocations=list(original)
  with self.assertRaisesRegex(ValueError,'IDENTITY_OR_LENGTH'):sim._reconcile()
  sim.allocations=original;sim.allocations._append(dict(fee='0',execution_cost='0'))
  with self.assertRaisesRegex(ValueError,'IDENTITY_OR_LENGTH'):sim._reconcile()
 def test_final_full_fold_and_native_totals_agree(self):
  sim=self.fake();sim._record_owner_fill(dict(fee='.000000123456789',execution_cost='.00000002'));sim._record_owner_funding([dict(cash='-.123'),dict(cash='.122')]);sim.account.fees=sim._owner_fee_total;sim.account.execution_cost=sim._owner_cost_total;sim.account.funding_cash=sim._owner_funding_total;sim.audit_owner_totals()

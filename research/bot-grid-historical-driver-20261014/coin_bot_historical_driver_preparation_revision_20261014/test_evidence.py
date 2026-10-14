from pathlib import Path
import gzip,json,os,sys,tempfile,unittest
from decimal import Decimal as D,localcontext
import bindings as B
PORTABLE=B.ROOT/'coin_bot_native_adapter_portable_synthetic_20261014'
sys.path.insert(0,str(PORTABLE))
from generated_fixtures import new_sim,finish
from evidence import export_final,safe

class EvidenceTests(unittest.TestCase):
 def exported(self,fixture='RANGE',arm='GRID'):
  sim=finish(new_sim(arm,fixture));temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  out=Path(temporary.name)/'fresh';result=export_final(sim,out,dict(generated_only=True),[],[10000,float(sim.account.nav())])
  return sim,out,result

 def test_full_account_and_owner_roundtrip_no_second_capital(self):
  sim,out,r=self.exported();account=json.loads(gzip.decompress((out/'ACCOUNT_FINAL.json.gz').read_bytes()))
  self.assertEqual(account,safe(sim.account.snapshot()));self.assertEqual(account['config']['initial_cash'],'10000')
  owner=json.loads(gzip.decompress((out/'OWNER_FINAL.json.gz').read_bytes()))
  self.assertEqual(owner['native_pending'],safe(sim.pending));self.assertFalse(owner['restore_supported'])
  allocations=[json.loads(line) for line in gzip.decompress((out/'OWNER_FILLS.jsonl.gz').read_bytes()).splitlines()]
  with localcontext() as ctx:
   ctx.prec=40
   self.assertEqual(sum((D(a['fee']) for a in allocations),D(0)),sim.account.fees)
   self.assertEqual(sum((D(a['execution_cost']) for a in allocations),D(0)),sim.account.execution_cost)
  self.assertEqual(r['status'],'PAID_FLAT')

 def test_residual_is_marked_never_paid_or_risk_certified(self):
  _,out,r=self.exported('TERMINAL_RESIDUAL')
  summary=json.loads((out/'SUMMARY.json').read_text());metrics=json.loads((out/'ACTUAL_RISK_METRICS.json').read_text())
  self.assertEqual(r['status'],'FULL_MARKED_WITH_RESIDUAL');self.assertIsNone(summary['paid_NAV_decimal'])
  self.assertGreater(D(metrics['terminal_residual_notional_decimal']),0);self.assertFalse(metrics['risk_parity_certified'])

 def test_actual_notional_metrics_and_insufficient_tail_scope(self):
  sim,out,_=self.exported();metrics=json.loads((out/'ACTUAL_RISK_METRICS.json').read_text())
  minute=sim.result()['minute'];expected=float((minute['gross_notional']/minute['nav']).mean())
  self.assertAlmostEqual(metrics['actual_close_mean_gross'],expected)
  self.assertIsNone(metrics['daily_ES95_loss']);self.assertIsNone(metrics['worst_complete30d_loss'])
  self.assertTrue(metrics['insufficient_tail_observations'])

 def test_no_output_overwrite_or_snapshot_recovery_claim(self):
  sim,out,_=self.exported()
  with self.assertRaises(FileExistsError):export_final(sim,out,{},[],[10000])
  self.assertFalse(any('checkpoint' in p.name for p in out.iterdir()))
  self.assertFalse(json.loads((out/'EVIDENCE_MANIFEST.json').read_text())['restore_supported'])

if __name__=='__main__':unittest.main()

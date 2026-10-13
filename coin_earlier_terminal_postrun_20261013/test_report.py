"""Synthetic report classification and units; zero historical file reads."""
import unittest,copy,tempfile
from pathlib import Path
from build_report import validate_result,validate_summary,validate_daily_chunks,metrics,SYMS,sha
class Tests(unittest.TestCase):
 def result(self,paid=True):
  return dict(case_id='Y2025_STATIC50_FINE_ORIGINAL',year=2025,mode='ORIGINAL',required_minutes=525600,completed_minutes=525600,full_calendar=True,paid_flat=paid,completion='COMPLETE_CONDITIONAL_ACCOUNT',terminal_residual_quantity={s:('0' if paid or s!='XRPUSDT' else '-10') for s in SYMS},marked_PnL_USDT=100.,paid_cash_PnL_USDT=100. if paid else None,daily_observed_days=2)
 def test_paid_vs_residual(self):
  self.assertEqual(validate_result(self.result(),self.result()['case_id']),(True,True));self.assertEqual(validate_result(self.result(False),self.result()['case_id']),(True,False))
  r=self.result(False);r['paid_flat']=True;r['paid_cash_PnL_USDT']=100.
  with self.assertRaises(ValueError):validate_result(r,r['case_id'])
 def test_halt_no_annual_cash(self):
  r=self.result(False);r.update(completed_minutes=100,full_calendar=False,completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED')
  self.assertEqual(validate_result(r,r['case_id']),(False,False))
 def test_flat_partial_is_not_paid(self):
  r=self.result();r.update(completed_minutes=1440,full_calendar=False,paid_flat=False,paid_cash_PnL_USDT=None,completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED')
  self.assertEqual(validate_result(r,r['case_id']),(False,False))
  validate_summary(r,{'summary':dict(net_PnL=100.,terminal_cash_realized=True)})
  with self.assertRaises(ValueError):validate_summary(r,{'summary':dict(net_PnL=100.,terminal_cash_realized=False)})
  del r['terminal_residual_quantity']['DOGEUSDT']
  with self.assertRaises(ValueError):validate_result(r,r['case_id'])
 def test_daily_audited_NAV_clock_and_hash(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'recovery').mkdir();x=np.zeros((1440,36));x[-1,0]=10100.
   chunk=p/'recovery/DAY_0000.npz';np.savez(chunk,minute_chunk=x);(p/'DAILY.csv').write_text('close_us,nav\n1735776000000000,10100.0\n')
   pointer={'chunks':[dict(path=chunk.name,rows=1440,columns=36,SHA256=sha(chunk))]};r=self.result();r.update(completed_minutes=1440,daily_observed_days=1)
   rows=[dict(close_us='1735776000000000',nav='10100.0')]
   self.assertEqual(validate_daily_chunks(p,rows,r,pointer)['audited_chunk_count'],1)
   for bad in ([dict(close_us='1735776060000000',nav='10100.0')],[dict(close_us='1735776000000000',nav='10200.0')]):
    with self.assertRaises(ValueError):validate_daily_chunks(p,bad,r,pointer)
   pointer['chunks'][0]['SHA256']='0'*64
   with self.assertRaises(ValueError):validate_daily_chunks(p,rows,r,pointer)
 def test_case_population_and_units(self):
  r=self.result();r['year']=2024
  with self.assertRaises(ValueError):validate_result(r,r['case_id'])
  a={'summary':{k:v for k,v in zip(('gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT','risk_reduction_signal_count','minimum_actual_free_cash_all_observations_USDT'),(100.,1.,2.,-3.,4,9000.))}}
  r=self.result();m=metrics(r,a,[{'nav':'10100','close_us':'1735776000000000'},{'nav':'10200','close_us':'1735862400000000'}]);self.assertEqual(m['funding_USDT'],-3.);self.assertEqual(m['fees_USDT'],1.);self.assertEqual(m['month_end_cumulative_PnL_USDT']['2025-01'],200.)
if __name__=='__main__':unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Independent read-only calculations from approved saved outputs and daily evidence.
Uses no author functions, account runtime, provider, targets, raw prices, or holdout.
"""
from pathlib import Path
from decimal import Decimal, localcontext
import argparse,hashlib,json
import numpy as np
R=Path(__file__).resolve().parent.parent
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
CAL={2023:(1672531200000000,1704067200000000),2024:(1704067200000000,1735689600000000)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def raw(a):return hashlib.sha256(a.tobytes(order='C')).hexdigest()
def read(p):return json.loads(p.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
def near(a,b):assert np.isfinite(a) and np.isfinite(b) and abs(a-b)<=2e-12*max(1,abs(a),abs(b)),(a,b)
def exact_ratio(a,b):
 with localcontext() as ctx:
  ctx.prec=100;return Decimal(str(a))/Decimal(str(b))
def main(directory,out):
 report=read(directory/'RISK_EVIDENCE.json');assert report['analysis_cell_count']==12 and report['matched_pair_count']==6 and report['cohort_cell_count']==18
 expected={(y,f,t) for y in CAL for f in ('STATIC50','VOL_MANAGED_HOLD') for t in ('LOW','MID','HIGH')}
 assert {(c['year'],c['strategy'],c['tier']) for c in report['cells']}==expected and len(report['cells'])==12
 manifest=read(directory/'COMPACT_ARTIFACT_MANIFEST.json')
 for name,pin in manifest['files'].items():
  p=(directory/name).resolve();assert p.is_relative_to(directory) and sha(p)==pin['SHA256'] and p.stat().st_size==pin['bytes']
 checked=[]
 for cell in report['cells']:
  cid=cell['cell_id'];info=cell['MINUTE_original'];p=(R/info['path']).resolve();assert p.is_relative_to(R)
  assert sha(p)==info['SHA256'] and p.stat().st_size==info['bytes']
  with np.load(p,allow_pickle=False) as z:
   order=list(z.files);assert set(order)=={'values','columns'};a=z['values'];columns=z['columns']
  names=columns.tolist();ix={n:i for i,n in enumerate(names)};n=len(a);start,stop=CAL[cell['year']]
  assert a.dtype==np.dtype('float64') and a.shape==(n,37) and n==(stop-start)//60_000_000
  assert len(names)==len(ix)==37 and np.isfinite(a).all()
  assert np.array_equal(a[:,ix['close_us']],(start+np.arange(1,n+1,dtype=np.int64)*60_000_000).astype(float))
  nav=a[:,ix['nav']];assert (nav>0).all();returns=nav/np.r_[10000.,nav[:-1]]-1
  sig=info['signature'];assert raw(np.asarray(a,dtype='<f8',order='C'))==sig['values_C_order_SHA256']
  for d in sig['original_archive_array_descriptors']:
   value=a if d['key']=='values' else columns
   assert d['dtype']==value.dtype.str and d['shape']==list(value.shape) and d['raw_C_order_SHA256']==raw(value)
  assert [d['key'] for d in sig['original_archive_array_descriptors']]==order
  rs=cell['minute_NAV_simple_return_evidence'];assert rs['count']==n and rs['canonical_C_order_SHA256']==raw(np.asarray(returns,dtype='<f8'))
  for key,val in {'minimum':returns.min(),'maximum':returns.max(),'mean':returns.mean(),'sample_std_ddof1':returns.std(ddof=1)}.items():assert rs[key]==float(val)
  curve=np.r_[10000.,nav];minute_mdd=float(np.max(1-curve/np.maximum.accumulate(curve)));assert cell['minute_close_MDD_fraction']==minute_mdd
  assert cell['all_observation_native_MDD_fraction']+1e-12>=minute_mdd
  dp=directory/'cells'/cid/'DAILY.npz';assert sha(dp)==cell['DAILY']['SHA256']
  with np.load(dp,allow_pickle=False) as z:daily=z['values'];dailycolumns=z['columns']
  dnames=dailycolumns.tolist();dix={name:i for i,name in enumerate(dnames)};assert len(daily)==n//1440
  # Build daily evidence independently using original per-day slices.
  blocks=a.reshape(-1,1440,37);made=np.empty_like(daily)
  for day,block in enumerate(blocks):
   x={'day_close_us':block[-1,ix['close_us']],'minute_observation_count':1440.,'nav_close':block[-1,ix['nav']],'daily_simple_return':block[-1,ix['nav']]/(10000. if day==0 else blocks[day-1,-1,ix['nav']])-1}
   for key in ('gross_weight','net_signed_weight'):
    v=block[:,ix[key]];x.update({key+'_sum':v.sum(),key+'_min':v.min(),key+'_max':v.max(),'absolute_'+key+'_sum':np.abs(v).sum(),'absolute_'+key+'_max':np.abs(v).max()})
   x['flat_actual_quantity_minutes']=np.all(block[:,[ix[s+'_quantity'] for s in S]]==0,axis=1).sum()
   for s in S:
    w=block[:,ix[s+'_signed_weight']];x.update({s+'_signed_weight_sum':w.sum(),s+'_signed_weight_min':w.min(),s+'_signed_weight_max':w.max(),s+'_absolute_weight_sum':np.abs(w).sum(),s+'_absolute_weight_max':np.abs(w).max()})
   x.update(minimum_free_cash_USDT=block[:,ix['free_cash']].min(),maximum_isolated_margin_USDT=block[:,ix['isolated_balance']].max(),free_cash_below1000_minutes=(block[:,ix['free_cash']]<1000-1e-8).sum(),isolated_margin_above8500_minutes=(block[:,ix['isolated_balance']]>8500+1e-8).sum())
   for key,source in [('fees_USDT','cumulative_fees'),('execution_cost_USDT','cumulative_execution_costs'),('signed_funding_USDT','cumulative_funding'),('turnover_USDT','cumulative_turnover')]:
    v=block[-1,ix[source]];x['cumulative_'+key]=v;x['daily_change_'+key]=v-(0 if day==0 else blocks[day-1,-1,ix[source]])
   assert set(x)==set(dnames);made[day]=[x[name] for name in dnames]
  # The sum reduction may follow a different NumPy accumulation stride; compare
  # sums at strict dimensionless reporting tolerance, endpoints/counts exactly.
  assert np.allclose(made,daily,rtol=2e-15,atol=2e-13,equal_nan=False),(cid,np.max(np.abs(made-daily)))
  for name in dnames:
   if not name.endswith('_sum'):assert np.array_equal(made[:,dix[name]],daily[:,dix[name]]),(cid,name)
  agg=cell['saved_float64_aggregate'];dn=nav[1439::1440];dr=dn/np.r_[10000.,dn[:-1]]-1;dc=np.r_[10000.,dn]
  assert agg['daily_realized_annual_volatility']==float(np.std(dr,ddof=1)*np.sqrt(365))
  assert agg['daily_close_MDD_fraction']==float(np.max(1-dc/np.maximum.accumulate(dc)))
  weights=a[:,[ix[s+'_signed_weight'] for s in S]];gross=np.abs(weights).sum(1);net=weights.sum(1)
  assert np.max(np.abs(gross-a[:,ix['gross_weight']]))<=1e-12 and np.max(np.abs(net-a[:,ix['net_signed_weight']]))<=1e-12
  for field,val in {'gross_weight_mean':a[:,ix['gross_weight']].mean(),'gross_weight_min':a[:,ix['gross_weight']].min(),'gross_weight_max':a[:,ix['gross_weight']].max(),'net_signed_weight_mean':a[:,ix['net_signed_weight']].mean(),'net_signed_weight_min':a[:,ix['net_signed_weight']].min(),'net_signed_weight_max':a[:,ix['net_signed_weight']].max(),'net_absolute_weight_mean':np.abs(a[:,ix['net_signed_weight']]).mean(),'net_absolute_weight_max':np.abs(a[:,ix['net_signed_weight']]).max(),'minimum_free_cash_minute_close_USDT':a[:,ix['free_cash']].min(),'maximum_isolated_margin_minute_close_USDT':a[:,ix['isolated_balance']].max()}.items():near(agg[field],float(val))
  flat=int(np.all(a[:,[ix[s+'_quantity'] for s in S]]==0,axis=1).sum());assert agg['flat_actual_quantity_minutes']==flat;assert agg['flat_actual_quantity_fraction']==flat/n
  for i,s in enumerate(S):
   w=weights[:,i]
   for key,val in {'signed_mean':w.mean(),'signed_min':w.min(),'signed_max':w.max(),'absolute_mean':np.abs(w).mean(),'absolute_max':np.abs(w).max()}.items():near(agg['asset_weights'][s][key],float(val))
  row=cell['authoritative_reviewed_matrix_row'];nativecost=cell['native_costs'];f=Decimal(row['fees_USDT']);e=Decimal(row['execution_cost_USDT']);u=Decimal(row['signed_funding_USDT'])
  with localcontext() as ctx:
   ctx.prec=100;assert Decimal(nativecost['same_quantity_fee_execution_less_signed_funding_USDT'])==f+e-u
  for native,field in [('fees_USDT','fees_USDT'),('execution_price_cost_USDT','execution_cost_USDT'),('signed_funding_USDT','signed_funding_USDT')]:assert nativecost[native]==str(Decimal(row[field]))
  ratios=cell['future_informed_descriptive_ratios'];assert ratios['denominators_include_future_observations'] is True and ratios['executed_scaled_trades_or_costs'] is False and ratios['OOS_or_alpha_or_executable_advantage_claim'] is False
  if cell['native_exact_paid_annual_return_fraction'] is not None:
   for key,denom in [('paid_return_div_full_sample_daily_realized_annual_volatility',agg['daily_realized_annual_volatility']),('paid_return_div_full_sample_mean_gross_weight',agg['gross_weight_mean'])]:assert Decimal(ratios[key])==exact_ratio(cell['native_exact_paid_annual_return_fraction'],denom)
  finref=row['bindings']['saved_JSON_references_rehashed']['finance_review'];finance=read(R/finref['path']);assert sha(R/finref['path'])==finref['SHA256']
  residual_keys=('native40_secondary_PnL_bridge_residual','raw_precision100_stored_delta_terminal_residuals','native_secondary_residual','exact100_stored_delta_terminal_errors','exact100_stored_cash_debt_delta_terminal_errors')
  assert cell['native40_financial_residuals']=={k:finance[k] for k in residual_keys if k in finance}
  refs=cell['reviewed_JSON_references_rehashed'];native=read(R/refs['native_result']['path'])['summary']['decimal_strings'];assert sha(R/refs['native_result']['path'])==refs['native_result']['SHA256']
  bridge=cell['native_same_quantity_accounting_bridge'];assert bridge['gross_mid_price_PnL_same_executed_quantities_USDT']==native.get('gross_PnL_same_quantities') and bridge['native_net_PnL_USDT']==native.get('net_PnL') and bridge['native_accounting_bridge_error_USDT']==native.get('accounting_bridge_error_USDT')
  checked.append({'cell_id':cid,'minute_archive_SHA256':info['SHA256'],'minute_values_raw_C_SHA256':raw(a),'minute_return_raw_C_SHA256':rs['canonical_C_order_SHA256'],'daily_archive_SHA256':cell['DAILY']['SHA256'],'all_daily_columns_verified':True,'native_decimal_cost_and_residual_fields_preserved':True})
  print(json.dumps({'cell':cid,'status':'PASS_INDEPENDENT_SAVED_ARRAY_AND_DAILY_ARITHMETIC'}),flush=True)
 lookup={c['cell_id']:c for c in report['cells']}
 assert len(report['paired_comparisons'])==6
 for p in report['paired_comparisons']:
  s=lookup[p['STATIC50_cell_id']];h=lookup[p['VOL_MANAGED_HOLD_cell_id']]
  with localcontext() as ctx:
   ctx.prec=100;assert Decimal(p['HOLD_minus_STATIC_paid_return_fraction'])==Decimal(h['native_exact_paid_annual_return_fraction'])-Decimal(s['native_exact_paid_annual_return_fraction'])
 result={'schema':'INDEPENDENT_SAVED_FAMILY_ARRAY_ARITHMETIC_REVIEW_V1','status':'PASS_ALL12_SAVED_ARRAYS_DAILY_AND_AGGREGATE_ARITHMETIC','cells_checked':checked,'paid_pairs_checked':6,'RISK_EVIDENCE_SHA256':sha(directory/'RISK_EVIDENCE.json'),'COMPACT_ARTIFACT_MANIFEST_SHA256':sha(directory/'COMPACT_ARTIFACT_MANIFEST.json'),'review_code_SHA256':sha(Path(__file__)),'actions':{'original_saved_MINUTE_archives_read':12,'market_source_reads':0,'covariance_reads':0,'new_accounts':0,'financial_replays':0,'holdout_reads':0,'publication_actions':0},'tolerance':'No monetary epsilon; exact native strings and hashes preserved. Independent daily sum reductions compared at2e-15relative/2e-13absolute; endpoints/counts and minute-return hashes exact. Dimensionless exposure summaries compared at2e-12relative with1floor.'}
 assert not out.exists();out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'receipt':str(out),'SHA256':sha(out),'status':result['status']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.directory.resolve(),a.output.resolve())

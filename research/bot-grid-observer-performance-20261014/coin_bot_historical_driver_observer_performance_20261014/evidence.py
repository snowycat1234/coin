"""Complete final evidence, lossless compression and actual-account metrics.

No restore checkpoint, repeated all-minute snapshot or independently funded
sleeve is written. The simulator and account own every economic computation.
"""
from pathlib import Path
from decimal import Decimal
import dataclasses,gzip,hashlib,json,math
from collections.abc import Mapping,Sequence

def safe(v):
 if isinstance(v,Decimal):return str(v)
 if dataclasses.is_dataclass(v):return {k:safe(getattr(v,k)) for k in v.__dataclass_fields__}
 if isinstance(v,Mapping):return {str(k):safe(x) for k,x in v.items()}
 if isinstance(v,set):return [safe(x) for x in sorted(v,key=repr)]
 if isinstance(v,Sequence) and not isinstance(v,(str,bytes,bytearray)):return [safe(x) for x in v]
 if hasattr(v,'tolist'):return v.tolist()
 if hasattr(v,'item'):return v.item()
 return v

def json_file(path,value,compressed=False):
 path=Path(path)
 if path.exists():raise ValueError('EVIDENCE_NO_OVERWRITE:'+path.name)
 opener=gzip.open if compressed else open
 with opener(path,'xt',encoding='utf-8') as f:
  for chunk in json.JSONEncoder(sort_keys=True,allow_nan=False,separators=(',',':')).iterencode(safe(value)):f.write(chunk)
  f.write('\n')

def json_lines(path,rows):
 if Path(path).exists():raise ValueError('EVIDENCE_NO_OVERWRITE')
 with gzip.open(path,'xt',encoding='utf-8') as f:
  for row in rows:f.write(json.dumps(safe(row),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')

def metrics(sim,minute,daily_nav):
 import numpy as np
 nav=np.asarray(daily_nav,float);returns=nav[1:]/nav[:-1]-1 if len(nav)>1 and np.all(nav[:-1]>0) else np.asarray([])
 minute_nav=minute['nav'].to_numpy();valid=minute_nav>0
 if not np.all(valid):ratios=None
 else:
  notional=np.column_stack([minute[s+'_signed_marked_notional'].to_numpy() for s in sim.symbols])
  ratios=notional/minute_nav[:,None]
 tail=max(0.,float(np.sort(-returns)[-max(1,math.ceil(len(returns)*.05)):].mean())) if len(returns)>=20 else None
 worst30=max(0.,float(np.max(1-nav[30:]/nav[:-30]))) if len(nav)>=31 and np.all(nav[:-30]>0) else None
 return dict(all_event_MDD=sim.mdd,daily_annualized_vol=float(np.std(returns,ddof=1)*np.sqrt(365)) if len(returns)>=2 else None,
  daily_ES95_loss=tail,worst_complete30d_loss=worst30,complete_daily_return_observations=len(returns),
  actual_all_event_max_gross=sim.max_gross,actual_all_event_max_per_asset=sim.max_asset,
  actual_close_mean_gross=float(np.abs(ratios).sum(1).mean()) if ratios is not None and len(ratios) else None,
  actual_close_max_abs_net=float(np.abs(ratios.sum(1)).max()) if ratios is not None and len(ratios) else None,
  actual_close_max_per_asset={s:float(np.abs(ratios[:,i]).max()) for i,s in enumerate(sim.symbols)} if ratios is not None and len(ratios) else None,
  halt_count=int(sim.stop is not None),ruin_count=int(sim.account.nav()<=0 or sim.account.unpaid_liability>0),
  risk_exit_first_fill_missing_count=sum('first_reduction_fill_us' not in r for r in sim.breaches),
  terminal_residual_notional_decimal=str(sum((abs(p.quantity)*sim.account.marks[s][-1]['price'] for s,p in sim.account.positions.items() if p.quantity),Decimal(0))),
  risk_parity_certified=False,insufficient_tail_observations=len(returns)<30)

def export_final(sim,out,binding,daily,daily_nav,transport_stop=None,origin='GENERATED_ONLY'):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 # The original summary and terminal/cost convention come from the unchanged
 # native result method; no observer fabricates closure, fills or account NAV.
 result=sim.result();summary=result['summary']
 full=summary['completed_minutes']==summary['required_minutes'];flat=summary['terminal_cash_realized'];halt=sim.stop is not None
 status='PAID_FLAT' if full and flat and not halt else 'HALTED_MARKED' if halt else 'FULL_MARKED_WITH_RESIDUAL' if full else 'PARTIAL_MARKED'
 summary.update(dispatch_status=status,transport_stop_reason=transport_stop,evidence_origin=origin,
  paid_NAV_decimal=str(sim.account.nav()) if status=='PAID_FLAT' else None,marked_NAV_decimal=str(sim.account.nav()),
  complete_calendar=bool(full),no_resumability_claim=True,risk_parity_certified=False)
 json_file(out/'SUMMARY.json',summary);json_file(out/'BINDING.json',binding)
 json_file(out/'ACCOUNT_FINAL.json.gz',sim.account.snapshot(),True)
 journals={'NATIVE_SCHEDULER_FUNDING':sim.funding_journal,'OWNER_FILLS':sim.allocations,
  'OWNER_FUNDING':sim.funding_allocations,'POLICY_EVENTS':sim.policy_events,
  'REJECTIONS':sim.rejections,'BREACHES':sim.breaches,'ORIGINAL_TARGET_ROWS':sim.target_rows}
 for name,rows in journals.items():json_lines(out/(name+'.jsonl.gz'),rows)
 # Direct final observer state avoids the inherited full minute snapshot and
 # its duplicated economic journals. Every omitted list exists losslessly in
 # the named journal above. This is evidence, never a restart payload.
 state=dict(arm=sim.arm,base_btc=sim.base_btc,base_desired=sim.base_desired,original_desired=sim.original_desired,original_target=sim.original_target,native_pending=sim.pending,
  grid=vars(sim.grid) if sim.grid else None,prepared=vars(sim.prepared) if sim.prepared else None,binding=sim.binding,
  settling=sim.settling,seen_native_legs=sim.seen_native_legs,seen_native_funding=sim.seen_native_funding,
  expired_sessions=sim.expired_sessions,restore_base_after_settlement=sim.restore_base_after_settlement,
  last_attempt=sim._last_attempt_open,journal_files={k:k+'.jsonl.gz' for k in journals},restore_supported=False)
 json_file(out/'OWNER_FINAL.json.gz',state,True);json_file(out/'DAILY.json',daily)
 result['minute'].write_parquet(out/'MINUTE_FINANCE.parquet');result['targets'].write_parquet(out/'ORIGINAL_TARGETS.parquet')
 json_file(out/'AUDIT.json.gz',dict(breaches=result['breaches'],extrema=result['extrema']),True)
 json_file(out/'ACTUAL_RISK_METRICS.json',metrics(sim,result['minute'],daily_nav))
 files={p.name:dict(bytes=p.stat().st_size,SHA256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file()}
 json_file(out/'EVIDENCE_MANIFEST.json',dict(schema='COMPLETE_FINAL_NATIVE_OWNER_EVIDENCE_V1',status=status,
  files=files,completed_minutes=sim.rows_written,native_fill_legs=len(sim.account.trades),native_funding_events=len(sim.account.funding),
  economic_account_count=1,capital_accounts=1,restore_supported=False,risk_parity_certified=False,evidence_origin=origin))
 return dict(status=status,output_bytes=sum(p.stat().st_size for p in out.iterdir() if p.is_file()),completed_minutes=sim.rows_written)

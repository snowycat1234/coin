"""Final observer export only; unchanged native account owns every money value."""
from pathlib import Path
from decimal import Decimal
import hashlib,time
from grid_evidence import safe,json_file,json_lines,metrics

def export_final(sim,out,binding,daily,daily_nav,transport_stop=None,origin='GENERATED_BRIDGE_ONLY'):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);result=sim.result();summary=dict(result['summary'])
 full=summary['completed_minutes']==summary['required_minutes'];flat=summary['terminal_cash_realized'];halt=sim.stop is not None
 status='PAID_FLAT' if full and flat and not halt else 'HALTED_MARKED' if halt else 'FULL_MARKED_WITH_RESIDUAL' if full else 'PARTIAL_MARKED'
 summary.update(dispatch_status=status,transport_stop_reason=transport_stop,evidence_origin=origin,
  bridge_source_scope=sim.bridge_source_scope,bridge_source_identity=sim.source_registry.identity(),
  constructor_admission='EXPLICIT_ORIGINAL_SOURCE_SEAM_NO_GENERATED_RELABEL',
  inherited_generated_freeze_labels='UNCHANGED_FINANCIAL_RESULT_METADATA; EXPLICIT_BRIDGE_SOURCE_SCOPE_GOVERNS_THIS_CASE',
  paid_NAV_decimal=str(sim.account.nav()) if status=='PAID_FLAT' else None,marked_NAV_decimal=str(sim.account.nav()),
  complete_calendar=bool(full),no_resumability_claim=True,risk_parity_certified=False)
 json_file(out/'SUMMARY.json',summary);json_file(out/'BINDING.json',binding)
 json_file(out/'ACCOUNT_FINAL.json.gz',sim.account.snapshot(),True)
 journals={'NATIVE_FILLS':sim.account.trades,'NATIVE_ACCOUNT_FUNDING':sim.account.funding,
  'NATIVE_SCHEDULER_FUNDING':sim.funding_journal,'POLICY_EVENTS':sim.policy_events,
  'REJECTIONS':sim.rejections,'BREACHES':sim.breaches,'TARGET_ROWS':sim.target_rows}
 if sim.bridge_arm=='FINITE':
  journals.update(OWNER_FILLS=result['owner_fill_allocations'],OWNER_FUNDING=result['owner_funding_allocations'],OWNER_EVENTS=result['owner_events'])
 for name,rows in journals.items():json_lines(out/(name+'.jsonl.gz'),rows)
 # Preserve full source/risk/owner/program witnesses without a minute restart
 # snapshot. Native and owner money records remain exact in named journals.
 state=dict(bridge_arm=sim.bridge_arm,source_identity=sim.source_registry.identity(),source_scope=sim.bridge_source_scope,
  h090_descriptor=vars(sim.descriptor),original_weights=sim.original_weights,risk_contexts={str(t):{k:v for k,v in r.items() if k!='covariance'} for t,r in sim.risk_contexts.items()},
  reservations={o:str(v) for o,v in sim.reservations.reservations.items()},pending=sim.pending,
  processed_native_receipts=sim.processed_native_receipts,restore_supported=False)
 if sim.bridge_arm=='FINITE':
  state.update(owner_ledger=sim.owners.snapshot(),owner_reconciliation=sim.owners.reconcile(sim.account.engine),
   program_activated=sim.program_activated,program_activation_signal=sim.program_activation_signal,
   program_state=dict(completed_opening_orders=sim.program.completed_opening_orders,terminal=sim.program.terminal,current_order_filled_margin=str(sim.program.current_order_filled_margin),processed_fill_receipts=sim.program.processed_fill_receipts),
   program_pending=sim.program_pending,consumed_fee_funding_reserve=str(sim.program_budget.consumed_fee_funding_reserve),
   retired_reservations={o:str(v) for o,v in sim.reservations.retired_reservations.items()},
   fill_owner_bindings=sim._fill_owner,program_order_authorizations=sim._program_order_authorizations,
   program_signal_mark_evidence=sim._program_signal_mark_evidence,program_cost_events=sim.program_budget.cost_events)
 json_file(out/'OWNER_AND_POLICY_FINAL.json.gz',state,True);json_file(out/'DAILY.json',daily)
 result['minute'].write_parquet(out/'MINUTE_FINANCE.parquet');result['targets'].write_parquet(out/'ADMITTED_TARGETS.parquet')
 json_file(out/'AUDIT.json.gz',dict(breaches=result['breaches'],extrema=result['extrema']),True)
 json_file(out/'ACTUAL_RISK_METRICS.json',metrics(sim,result['minute'],daily_nav))
 files={p.name:dict(bytes=p.stat().st_size,SHA256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file()}
 manifest=dict(schema='COMPLETE_FINAL_H090_NATIVE_OWNER_EVIDENCE_V1',status=status,year=binding.get('year'),arm=sim.bridge_arm,
  preparation_manifest_SHA256=binding.get('preparation_manifest_SHA256'),source_receipt_SHA256=binding.get('source_receipt_SHA256'),
  files=files,binding_SHA256=files['BINDING.json']['SHA256'],completed_minutes=sim.rows_written,required_minutes=summary['required_minutes'],complete_calendar=bool(full),
  native_fill_legs=len(sim.account.trades),native_funding_events=len(sim.account.funding),economic_account_count=1,capital_accounts=1,
  owner_cash_wallet_count=0,restore_supported=False,risk_parity_certified=False,evidence_origin=origin)
 json_file(out/'EVIDENCE_MANIFEST.json',manifest)
 return dict(status=status,output_bytes=sum(p.stat().st_size for p in out.iterdir() if p.is_file()),completed_minutes=sim.rows_written)

def run_calendar(sim,output,binding,deadline,origin):
 daily=[];nav=[float(sim.account.nav())];reason=None
 while sim.cursor<sim.end and sim.stop is None:
  if time.monotonic()>=deadline-20:reason='RESOURCE_STOP_COMPLETE_DAY_BOUNDARY_NOT_PAID';break
  row=sim.advance_day();daily.append(row)
  if row['completed']:nav.append(float(sim.account.nav()))
 return export_final(sim,output,binding,daily,nav,reason,origin)

#!/usr/bin/env python3
"""Compact saved-only checks. No financial accounts, history advancement, providers or run authority."""
from pathlib import Path
import hashlib,json,gzip,argparse,math,subprocess,tempfile,sys
from decimal import Decimal
from saved_native_reconciliation import reconcile_saved_native,canonical_sha256
CELLS=[f'{y}_{s}_{t}' for y in [2023,2024] for s in ['H090','VOL_MANAGED_HOLD'] for t in ['LOW','MID','HIGH']]
ATT='bounded_native_continuation_guard50_exit_expansion_20261015/actual_remaining12_attempt001'
R='bounded_native_continuation_guard50_exit_expansion_independent_review_20261015'
M='bounded_native_continuation_saved_matrix_comparison_20261015'
GO='4d5b4c393cf472dd283a48c1e9bb4cf98ea0da57b17694d26d491e9dfb5339c0';PREP='635e58d9d2f6672ef382d4fa3c828224f107127093226530594a03014fbf4266';SOURCE_REVIEW='1c4281f73b5db73852ab2286b90c62cb5b9c46ef38e7b79766540c0e774eeb90';CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def require(x,message):
 if not x:raise ValueError(message)
def raw(p):return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
def read(p):return json.loads(raw(p))
def load_case(root,cell,name):
 p=Path(root)/ATT/cell/name;return read(p if p.exists() else p.with_name(p.name+'.gz'))
def numeric_equal(a,b):
 if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(numeric_equal(v,b[k]) for k,v in a.items())
 if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(numeric_equal(x,y) for x,y in zip(a,b))
 if isinstance(a,float):return type(b) in (int,float) and math.isclose(a,b,rel_tol=2e-13,abs_tol=2e-13)
 return a==b

def validate_financial(audit,result,proof):
 got=reconcile_saved_native(audit,result);require(got==proof,'EXACT_NATIVE40_PROOF_OR_RAW100_RESIDUAL_CHANGED')
 require(proof['checker_SHA256']==CHECKER,'CHECKER_IDENTITY')
 require(proof['account_objects_constructed']==proof['financial_clocks_advanced']==0,'SAVED_ONLY_BOUNDARY')
 require(audit['transfer_journal']==[] and audit['settlement_journal']==[] and audit['unpaid_liability']=='0','NO_TRANSFER_SETTLEMENT_DEBT')
 require(all(Decimal(p['quantity'])==Decimal(p['isolated_balance'])==0 for p in audit['positions'].values()),'PAID_FLAT_POSITIONS')
 require(all(not t.get('liquidation_takeover') for t in audit['trades']),'NO_CONDITIONAL_TAKEOVER')
 require(result['economics']['actual_paid_market_flat'] is True and result['economics']['conditional_settled_flat'] is False,'PAID_FLAT_TAXONOMY')
 require(result['summary']['funding_rate_unit']=='UNCONFIRMED' and result['summary']['unit_certified'] is False and result['summary']['publication_certified'] is False,'FUNDING_UNIT_QUALIFICATION');return got

def warning_rows(a):
 rows=[];seen=set();minute=60_000_000
 for m in a['monitor_journal']:
  for action in m['actions']:
   if action.get('reason')!='GUARD50_PAID_EXIT_NO_TOPUP':continue
   s=action['symbol'];signal=m['pending_exits'][s]['signal_us'];key=(s,signal)
   if key in seen:continue
   seen.add(key);require(action['transferred']=='0','WARNING_TRANSFER')
   first=next((t for t in a['trades'] if t['symbol']==s and t['event_us']>signal and t['leg']=='CLOSE'),None);earliest=((signal+minute-1)//minute+1)*minute+1
   require(first is not None and first['event_us']==earliest and first['signal_us']==signal and not first.get('liquidation_takeover'),'EXACT_FIRST_NATIVE_ELIGIBLE_WARNING_CLOSE')
   require(Decimal(first['decimal_strings']['quantity_after'])==0 and Decimal(first['decimal_strings']['fee_amount'])>0,'FULL_PAID_WARNING_EXIT')
   rows.append(dict(symbol=s,warning_signal_us=signal,native_earliest_paid_execution_us=earliest,first_subsequent_close_us=first['event_us'],first_subsequent_close_signal_us=first['signal_us'],first_subsequent_close_is_conditional_takeover=False,first_subsequent_close_quantity=first['decimal_strings']['quantity'],first_subsequent_close_quantity_after=first['decimal_strings']['quantity_after'],first_subsequent_close_fee=first['decimal_strings']['fee_amount']))
 return rows

def validate_risk_saved(report,review):
 require(report['adaptive_DEV_only'] is True and report['nominal_tier_equality_is_not_exact_realized_risk_matching'] is True,'RISK_QUALIFICATION')
 for k,v in review['recomputed_saved_fields'].items():
  # Currency/cash/margin projections bind exactly; floating tolerance only for scientific risk/exposure fields.
  equal=report.get(k)==v if any(w in k for w in ['cash','margin','USDT']) else numeric_equal(v,report.get(k))
  require(equal,'INDEPENDENT_SAVED_RISK_BINDING:'+k)
 require(review['covariance_is_strictly_past_at_every_observation'] is True and review['covariance_recomputed_from_raw_daily_prices_in_this_review'] is False,'COVARIANCE_SCOPE');return True

def validate_prefix(audit,cell,root):
 row=read(Path(root)/R/f'actual_remaining12_saved_review/{cell}_NATIVE_BASELINE_PREFIX.json');stop=row['comparison_stop_us']
 trades=[t for t in audit['trades'] if stop is None or t['event_us']<=stop];funding=[f for f in audit['funding'] if stop is None or f['event_us']<=stop];fills={k:v for k,v in audit['fill_requests'].items() if stop is None or v['identity']['event_us']<=stop}
 for value,count,name in [(trades,'trade_rows_exact','trade_prefix_canonical_SHA256'),(funding,'funding_rows_exact','funding_prefix_canonical_SHA256'),(fills,'fill_request_records_exact','fill_request_prefix_canonical_SHA256')]:require(len(value)==row[count] and canonical_sha256(value)==row[name],'D_SIDE_CAUSAL_EVENT_PREFIX:'+name)
 if 'VOL_MANAGED_HOLD' in cell:require(stop is None and row['status']=='PASS_EXACT_ENTIRE_YEAR_NO_D_INTERVENTION' and not warning_rows(audit),'HOLD_ENTIRE_YEAR_EXACT_BASELINE')
 return row

def validate_report(report,terminal=None):
 require(report['annual_accounts_are_separate_not_compounded'] is True and report['continuous_two_year_CAGR'] is None and report['equal_nominal_tiers_are_not_actual_risk_matching'] is True,'ANNUAL_RISK_SCOPE')
 require(report['all_minute_risk_regeneration_is_self_contained'] is False,'FALSE_ALL_MINUTE_COLD_RECOVERY')
 require(report['final_matrix_rows']==18 and report['duplicate_paths_are_not_independent_confirmation'] is True and report['H090_all_six_exact_STATIC50_realized_financial_paths'] is True,'DUPLICATE_SCOPE')
 require(report['native40_every_event_authoritative'] is True and report['raw_precision100_residuals_preserved_without_epsilon_or_repair'] is True,'MONETARY_AUTHORITY')

def verify_matrix(root):
 helper=root/M/'comparison.py';require(sha(helper)=='837f0c50d1a1f534b8f79cfdda4e0da597c696b2ce63d8434e25fe4b4304b2f1','FROZEN_MATRIX_HELPER')
 require(sha(root/M/'FINAL_SAVED_EVIDENCE_INDEX.json')=='06f4b20cc3e065895dba4d24d0a3795467bd8307fe346a826613faaafcc5f730','FROZEN_MATRIX_INDEX')
 with tempfile.TemporaryDirectory(prefix='saved_matrix_recheck_') as td:
  out=Path(td)/'render';subprocess.run([sys.executable,str(helper),'--workspace',str(root),'--index',str(root/M/'FINAL_SAVED_EVIDENCE_INDEX.json'),'--output',str(out),'--authorize-saved-final'],check=True,capture_output=True,text=True)
  for name in ['MATRIX_COMPARISON.json','MATRIX_COMPARISON.csv','REPORT.txt']:require((out/name).read_bytes()==(root/M/'final_saved_comparison_attempt001'/name).read_bytes(),'EXACT_MATRIX_RERENDER:'+name)
 matrix=read(root/M/'final_saved_comparison_attempt001/MATRIX_COMPARISON.json');require(matrix['review_approved_terminal_rows']==18 and matrix['pending_rows']==0 and matrix['continuous_two_year_CAGR'] is None,'FINAL18_SCOPE');return True

def verify(root):
 root=Path(root).resolve();manifest=read(root/'MANIFEST.json');require(manifest['ordered_cells']==CELLS and manifest['packet_kind']=='SAVED_RESULTS_ONLY','SCOPE')
 files=manifest['files'];actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts};require(actual==set(files)|{'MANIFEST.json'},'MANIFEST_MEMBER_ALLOWLIST')
 for rel,pin in files.items():
  p=root/rel;require(p.is_file() and sha(p)==pin['sha256'] and p.stat().st_size==pin['bytes'],'MEMBER_PIN:'+rel)
 require(sha(root/'saved_native_reconciliation.py')==CHECKER,'FROZEN_PURE_CHECKER')
 for name,pin in {'REMAINING12_TERMINAL_INDEPENDENT_REVIEW.json':'6bf43d5fc61ee82355ae6678c88e140c5db2a9407cf6c994af73b4b6da8de550','OVERALL18_D_MATRIX_INDEPENDENT_REVIEW.json':'4bd7a741c1ad2ccb87a30882697a04c607b258aa95d8a5d1e197f2243b2d653c','ALL_SIX_H090_STATIC50_CANONICAL_EQUIVALENCE.json':'de4568b56cc0b7b124eebc204c92d306bc1def1f6595de30fff2632fe5134dd9'}.items():require(sha(root/R/'actual_remaining12_saved_review'/name)==pin,'INDEPENDENT_REVIEW_PIN:'+name)
 for name,pin in {'SAVED_MATRIX_COMPARISON_HELPER_REVIEW.json':'6cc90c38887031af0e08cb55798a39e01894e159e3b147e7a47669fa68dd35bc','EXACT_SIGNATURE_ADDENDUM_REVIEW.json':'74b043cf4dbb0e9ef46dc02a1ae1aaba4e53078923c8c7e13126b430e658aeec'}.items():require(sha(root/'saved_distinct_family_risk_independent_review_20261015'/name)==pin,'INDEPENDENT_HELPER_REVIEW_PIN:'+name)
 pins=read(root/'FULL_SAVED_OUTPUT_HASH_PINS.json')['files'];pairs=read(root/'EXACT_COPY_SOURCE_MAP.json');compressed=read(root/'LOSSLESS_GZIP_SOURCE_MAP.json')
 for dest,src in pairs.items():require(sha(root/dest)==pins[src]['sha256'] and (root/dest).stat().st_size==pins[src]['bytes'],'EXACT_SOURCE_COPY:'+dest)
 for dest,binding in compressed.items():
  b=raw(root/dest);require(hashlib.sha256(b).hexdigest()==binding['uncompressed_sha256']==pins[binding['source']]['sha256'] and len(b)==binding['uncompressed_bytes']==pins[binding['source']]['bytes'],'LOSSLESS_ORIGINAL:'+dest)
 adm=read(root/'EXTERNAL_ADMISSION_HASH_ONLY.json');require(adm['root_GO_sha256']==GO and adm['private_GO_bodies_included'] is False and adm['GO_or_launch_permission_granted_by_this_packet'] is False,'HASH_ONLY_NO_AUTHORITY')
 first=read(root/'FIRST5_VERIFIED_PUBLICATION_REFERENCE.json');require(first['commit']=='48e42f4040e317edf732bfedc9dce5d54e29ed12' and first['archive']['SHA256']=='d050f5f5d8349c8c927d6ca96cf48fc7f6e9db3b0e5efd63c8ceef290fa92e0b' and first['full_local_publication_receipt_sha256']=='74075f4290e8ed8ece6ea56c1d0e27bca88bec29a4a4a2149c9caa65c555c988' and first['all_remote_bytes_independently_verified'] is True,'FIRST5_PINNED_PUBLICATION_REFERENCE')
 source=read(root/'SOURCE_PUBLICATION_REFERENCE.json');require(source['source_commit']=='5a48a669f71c290a119fa9dabc8f14480626fc7d' and source['source_archive_sha256']=='ae58a91e80e89155ed7f123c1b3343efbab250c30c1ac12b991422fcc06c8f30' and source['every_remote_byte_matches_expected_local'] is True,'SOURCE_PINNED_PUBLICATION_REFERENCE')
 omitted=read(root/'OMITTED_MINUTE_OUTPUTS.json');require(omitted['all_minute_risk_regeneration_is_self_contained'] is False,'MINUTE_RECOVERY_SCOPE');controller=read(root/'CONTROLLER_TERMINAL_PROJECTION.json');out=[];warnings=0;overshoots=0;ledger=0
 for c in CELLS:
  a=load_case(root,c,'ACCOUNT_FINANCIAL_AUDIT.json');r=load_case(root,c,'NATIVE_RESULT.json');proof=load_case(root,c,'NATIVE40_RECONSTRUCTION_PROOF.json');rec=load_case(root,c,'CASE_RECEIPT.json');checkpoint=load_case(root,c,'TERMINAL_CHECKPOINT.json');review=read(root/R/f'actual_remaining12_saved_review/{c}_REVIEW.json');risk=load_case(root,c,'ACTUAL_HELD_RISK_REPORT.json');rr=read(root/R/f'actual_remaining12_risk_review/{c}_RISK_REVIEW.json')
  validate_financial(a,r,proof)
  if '_H090_' in c:
   canonical=read(root/R/'actual_remaining12_saved_review/ALL_SIX_H090_STATIC50_CANONICAL_EQUIVALENCE.json');equiv=next(x for x in canonical['cases'] if x['cell_id']==c)
   require(canonical_sha256({k:a[k] for k in canonical['financial_projection_fields']})==equiv['canonical_financial_projection_SHA256'],'H090_CANONICAL_FINANCIAL_DUPLICATE_PROJECTION')
  wr=warning_rows(a);require(wr==review['paid_warning_signals'],'WARNING_INDEPENDENT_BINDING');validate_prefix(a,c,root);validate_risk_saved(risk,rr)
  require(rec['cell_id']==c and rec['root_GO_SHA256']==GO and rec['preparation_SHA256']==PREP and rec['independent_review_SHA256']==SOURCE_REVIEW and rec['checker_SHA256']==CHECKER,'CASE_ADMISSION_IDENTITY')
  require(rec['code_identity']==adm['code_identity']==source['financial_code_identity'] and rec['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT','CASE_SOURCE_SCOPE');require(rec['completed_minutes']==rec['required_minutes']==(525600 if rec['year']==2023 else 527040),'FULL_CALENDAR')
  require(checkpoint['all_evidence_fsynced'] is True and checkpoint['restart_financial_snapshot_permission'] is False,'CHECKPOINT_SCOPE')
  for name,h in checkpoint['files'].items():require(pins[f'{ATT}/{c}/{name}']['sha256']==h,'CHECKPOINT_ORIGINAL_PIN:'+name)
  minute=omitted['files'][c];require(minute['sha256']==checkpoint['files']['MINUTE.npz'] and minute['bytes']==pins[minute['source']]['bytes'],'OMITTED_MINUTE_PIN')
  cr=next(x for x in controller['cases'] if x['cell_id']==c);require(cr['checkpoint_SHA256']==hashlib.sha256(raw(root/ATT/c/'TERMINAL_CHECKPOINT.json')).hexdigest(),'CONTROLLER_TERMINAL_BINDING')
  require(proof['exact_native40_NAV']==review['exact_financials']['NAV']==r['summary']['decimal_strings']['NAV'],'EXACT_NAV_REVIEW_BINDING');warnings+=len(wr);overshoots+=risk['forecast_volatility_breach_minutes'];ledger+=proof['financial_ledger_rows_checked']
  out.append({'cell_id':c,'exact_NAV':proof['exact_native40_NAV'],'financial_ledger_rows':proof['financial_ledger_rows_checked'],'paid_warning_exits':len(wr),'saved_forecast_overshoot_minutes':risk['forecast_volatility_breach_minutes']})
 report=read(root/'RESULTS_REPORT.json');validate_report(report);require(report['cases']==[read(root/R/f'actual_remaining12_saved_review/{c}_REVIEW.json') for c in CELLS],'REPORT_EXACT_REVIEW_ROWS');require(report['paid_warning_exits']==warnings and report['held_forecast_budget_overshoot_case_minutes']==overshoots,'REPORT_AGGREGATES');verify_matrix(root)
 return {'status':'PASS_REMAINING12_FINAL18_COMPACT_SAVED_RECOVERY','cases':out,'retained_members_rehashed':len(files),'exact_copy_files':len(pairs),'lossless_gzip_originals':len(compressed),'exact_native40_ledger_events':ledger,'final18_byte_identical_rerender':True,'accounts_constructed':0,'financial_minutes_advanced':0,'full_minute_risk_regenerated':False,'full_minute_arrays_omitted':True,'private_GO_bodies_omitted':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));args=p.parse_args();print(json.dumps(verify(args.root),sort_keys=True,allow_nan=False))

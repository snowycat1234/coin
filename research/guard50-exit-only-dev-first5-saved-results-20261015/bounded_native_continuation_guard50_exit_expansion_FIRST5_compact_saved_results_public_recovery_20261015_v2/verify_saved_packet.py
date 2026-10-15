#!/usr/bin/env python3
"""Offline compact saved-result checks; no account construction or financial clock."""
import pathlib,hashlib,json,gzip,sys,argparse,math
from decimal import Decimal,localcontext
from saved_native_reconciliation import reconcile_saved_native,canonical_sha256
CELLS=['2024_STATIC50_LOW','2024_STATIC50_HIGH','2023_STATIC50_LOW','2023_STATIC50_MID','2023_STATIC50_HIGH']
GO='1c561a74d1e3a5aced466e1d9e9912b4e4695007b88bcb932bf0f4b986cb598c'; PREP='635e58d9d2f6672ef382d4fa3c828224f107127093226530594a03014fbf4266'; SOURCE_REVIEW='1c4281f73b5db73852ab2286b90c62cb5b9c46ef38e7b79766540c0e774eeb90';CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
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
 p=root/'cases'/cell/name
 return read(p if p.exists() else p.with_name(p.name+'.gz'))
def numeric_equal(a,b):
 if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(numeric_equal(v,b[k]) for k,v in a.items())
 if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(numeric_equal(x,y) for x,y in zip(a,b))
 if isinstance(a,float):return type(b) in (int,float) and math.isclose(a,b,rel_tol=2e-13,abs_tol=2e-13)
 return a==b

def validate_financial(audit,result,proof):
 got=reconcile_saved_native(audit,result)
 require(got==proof,'EXACT_NATIVE40_PROOF_OR_RAW100_RESIDUAL_CHANGED')
 require(proof['checker_SHA256']==CHECKER,'CHECKER_IDENTITY')
 require(proof['account_objects_constructed']==proof['financial_clocks_advanced']==0,'SAVED_ONLY_BOUNDARY')
 require(audit['transfer_journal']==[] and audit['settlement_journal']==[] and audit['unpaid_liability']=='0','NO_TRANSFER_SETTLEMENT_DEBT')
 require(all(Decimal(p['quantity'])==Decimal(p['isolated_balance'])==0 for p in audit['positions'].values()),'PAID_FLAT_POSITIONS')
 require(all(not t.get('liquidation_takeover') for t in audit['trades']),'NO_CONDITIONAL_TAKEOVER')
 require(result['economics']['actual_paid_market_flat'] is True and result['economics']['conditional_settled_flat'] is False,'PAID_FLAT_TAXONOMY')
 require(result['summary']['funding_rate_unit']=='UNCONFIRMED' and result['summary']['unit_certified'] is False and result['summary']['publication_certified'] is False,'FUNDING_UNIT_QUALIFICATION')
 return got

def warning_rows(a):
 rows=[];seen=set();minute=60_000_000
 for m in a['monitor_journal']:
  for action in m['actions']:
   if action.get('reason')!='GUARD50_PAID_EXIT_NO_TOPUP':continue
   s=action['symbol'];signal=m['pending_exits'][s]['signal_us'];key=(s,signal)
   if key in seen:continue
   seen.add(key);require(action['transferred']=='0','WARNING_TRANSFER')
   first=next((t for t in a['trades'] if t['symbol']==s and t['event_us']>signal and t['leg']=='CLOSE'),None)
   earliest=((signal+minute-1)//minute+1)*minute+1
   require(first is not None and first['event_us']==earliest and first['signal_us']==signal and not first.get('liquidation_takeover'),'EXACT_FIRST_NATIVE_ELIGIBLE_WARNING_CLOSE')
   require(Decimal(first['decimal_strings']['quantity_after'])==0 and Decimal(first['decimal_strings']['fee_amount'])>0,'FULL_PAID_WARNING_EXIT')
   rows.append(dict(symbol=s,warning_signal_us=signal,native_earliest_paid_execution_us=earliest,first_subsequent_close_us=first['event_us'],first_subsequent_close_signal_us=first['signal_us'],first_subsequent_close_is_conditional_takeover=False,first_subsequent_close_quantity=first['decimal_strings']['quantity'],first_subsequent_close_quantity_after=first['decimal_strings']['quantity_after'],first_subsequent_close_fee=first['decimal_strings']['fee_amount']))
 return rows

def validate_risk_saved(report,review):
 require(report['adaptive_DEV_only'] is True and report['nominal_tier_equality_is_not_exact_realized_risk_matching'] is True,'RISK_QUALIFICATION')
 for k,v in review['recomputed_saved_fields'].items():require(numeric_equal(v,report.get(k)),'INDEPENDENT_SAVED_RISK_BINDING:'+k)
 require(review['covariance_is_strictly_past_at_every_observation'] is True and review['covariance_recomputed_from_raw_daily_prices_in_this_review'] is False,'COVARIANCE_SCOPE')
 return True

def validate_prefix(audit,cell,root):
 review=read(root/'independent_reviews/FIRST5_NATIVE_BASELINE_D_PREFIX_EQUIVALENCE.json')
 row=next(x for x in review['cases'] if x['cell_id']==cell);stop=row['first_D_warning_us']
 trades=[t for t in audit['trades'] if stop is None or t['event_us']<=stop];funding=[f for f in audit['funding'] if stop is None or f['event_us']<=stop];fills={k:v for k,v in audit['fill_requests'].items() if stop is None or v['identity']['event_us']<=stop}
 for value,count,name in [(trades,'trade_rows_exact','trade_prefix_canonical_SHA256'),(funding,'funding_rows_exact','funding_prefix_canonical_SHA256'),(fills,'fill_request_records_exact','fill_request_prefix_canonical_SHA256')]:
  require(len(value)==row[count] and canonical_sha256(value)==row[name],'D_SIDE_CAUSAL_EVENT_PREFIX:'+name)
 return row

def validate_report(report,terminal):
 require(report['cases']==terminal['cases'],'REPORT_METRICS_EXACT_INDEPENDENT_RECEIPT_BINDING')
 require(report['annual_accounts_are_separate_not_compounded'] is True and report['continuous_two_year_CAGR'] is None and report['equal_nominal_tiers_are_not_actual_risk_matching'] is True,'ANNUAL_RISK_SCOPE')
 require(report['all_minute_risk_regeneration_is_self_contained'] is False,'FALSE_ALL_MINUTE_COLD_RECOVERY')
 require(report['held_forecast_budget_overshoot_case_minutes']==331228 and report['paid_warning_exits']==11,'TOTAL_WARNING_AND_RISK_COUNTS')

def verify(root):
 root=pathlib.Path(root).resolve();manifest=read(root/'MANIFEST.json')
 require(manifest['ordered_cells']==CELLS and manifest['packet_kind']=='SAVED_RESULTS_ONLY','SCOPE')
 files=manifest['files'];actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 require(actual==set(files)|{'MANIFEST.json'},'MANIFEST_MEMBER_ALLOWLIST')
 for rel,pin in files.items():
  p=root/rel;require(p.is_file() and sha(p)==pin['sha256'] and p.stat().st_size==pin['bytes'],'MEMBER_PIN:'+rel)
 require(sha(root/'saved_native_reconciliation.py')==CHECKER,'FROZEN_PURE_CHECKER')
 pins=read(root/'FULL_SAVED_OUTPUT_HASH_PINS.json')['files'];pairs=read(root/'EXACT_COPY_SOURCE_MAP.json');compressed=read(root/'LOSSLESS_GZIP_SOURCE_MAP.json')
 for dest,src in pairs.items():require(sha(root/dest)==pins[src]['sha256'] and (root/dest).stat().st_size==pins[src]['bytes'],'EXACT_SOURCE_COPY:'+dest)
 for dest,binding in compressed.items():
  b=raw(root/dest);require(hashlib.sha256(b).hexdigest()==binding['uncompressed_sha256']==pins[binding['source']]['sha256'] and len(b)==binding['uncompressed_bytes']==pins[binding['source']]['bytes'],'LOSSLESS_ORIGINAL:'+dest)
 terminal=read(root/'independent_reviews/FIRST5_TERMINAL_INDEPENDENT_REVIEW.json');require(sha(root/'independent_reviews/FIRST5_TERMINAL_INDEPENDENT_REVIEW.json')=='4a800382d10193b1f3ac559b507cb9a165f4da53686e450f90af266d43c3794e','INDEPENDENT_TERMINAL_REVIEW_PIN')
 require(sha(root/'independent_reviews/FINAL_FIRST5_HELD_RISK_RECEIPT.json')=='bb90ee51e3751c8649e0dee96b18c5d842bcf6a9f117554c7c1ae9ae64f7965b','INDEPENDENT_RISK_REVIEW_PIN')
 require(sha(root/'source_evidence/INDEPENDENT_MATRIX_SOURCE_PACKET_REVIEW.json')=='c52850fb259a82f3c38ce46b338ca27b2f405f0defcdcaa7c4381380ea8d4c92','SOURCE_PACKET_REVIEW_PIN')
 require(sha(root/'source_evidence/PREPARATION.json')==PREP,'PREPARATION_PIN')
 adm=read(root/'EXTERNAL_ADMISSION_HASH_ONLY.json');require(adm['root_GO_sha256']==GO and adm['private_GO_bodies_included'] is False and adm['GO_or_launch_permission_granted_by_this_packet'] is False,'HASH_ONLY_NO_AUTHORITY')
 ref=read(root/'SOURCE_PUBLICATION_REFERENCE.json');require(ref['source_archive_sha256']=='ae58a91e80e89155ed7f123c1b3343efbab250c30c1ac12b991422fcc06c8f30' and ref['source_packet_independent_review_sha256']=='c52850fb259a82f3c38ce46b338ca27b2f405f0defcdcaa7c4381380ea8d4c92','SOURCE_PIN')
 publication=read(root/'source_evidence/SOURCE_PUBLICATION_VERIFIED.json')
 require(ref['source_commit']=='5a48a669f71c290a119fa9dabc8f14480626fc7d' and ref['status']=='VERIFIED_IMMUTABLE_SOURCE_PUBLICATION','VERIFIED_SOURCE_COMMIT')
 require(publication['commit']==ref['source_commit'] and publication['status']=='PASS' and publication['remote_content_verification']['every_remote_byte_matches_expected_local'] is True,'SOURCE_PUBLICATION_EVIDENCE')
 require(publication['packet_readme_url']==ref['verified_remote_source_link'] and publication['archive']['SHA256']==ref['source_archive_sha256'] and sha(root/'source_evidence/SOURCE_PUBLICATION_VERIFIED.json')==ref['publication_receipt_sha256'],'SOURCE_PUBLICATION_EXACT_BINDING')
 omitted=read(root/'OMITTED_MINUTE_OUTPUTS.json');require(omitted['all_minute_risk_regeneration_is_self_contained'] is False and omitted['large_arrays_intentionally_not_published'] is True,'MINUTE_RECOVERY_LIMIT_DISCLOSURE')
 controller=read(root/'source_evidence/CONTROLLER_TERMINAL_PROJECTION.json');out=[];warnings=0;breaches=0
 for cell in CELLS:
  a=load_case(root,cell,'ACCOUNT_FINANCIAL_AUDIT.json');r=load_case(root,cell,'NATIVE_RESULT.json');proof=load_case(root,cell,'NATIVE40_RECONSTRUCTION_PROOF.json');rec=load_case(root,cell,'CASE_RECEIPT.json');cp=load_case(root,cell,'TERMINAL_CHECKPOINT.json');review=read(root/'independent_reviews'/f'{cell}_REVIEW.json');risk=load_case(root,cell,'ACTUAL_HELD_RISK_REPORT.json');rr=read(root/'independent_reviews'/f'{cell}_RISK_REVIEW.json')
  validate_financial(a,r,proof);wr=warning_rows(a);require(wr==review['paid_warning_signals'],'WARNING_RECEIPT_BINDING');warnings+=len(wr)
  validate_risk_saved(risk,rr);validate_prefix(a,cell,root);breaches+=risk['forecast_volatility_breach_minutes']
  require(rec['cell_id']==cell and rec['root_GO_SHA256']==GO and rec['preparation_SHA256']==PREP and rec['independent_review_SHA256']==SOURCE_REVIEW and rec['checker_SHA256']==CHECKER,'CASE_ADMISSION_HASH_BINDING')
  require(rec['code_identity']==adm['code_identity']==ref['financial_code_identity'] and rec['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT','CASE_SOURCE_SCOPE')
  require(rec['completed_minutes']==rec['required_minutes']==(525600 if rec['year']==2023 else 527040),'FULL_CALENDAR_MINUTE_COUNT')
  require(cp['all_evidence_fsynced'] is True and cp['restart_financial_snapshot_permission'] is False,'CHECKPOINT_BOUNDARY')
  for name,h in cp['files'].items():
   src=f'bounded_native_continuation_guard50_exit_expansion_20261015/actual_first5_attempt001/{cell}/{name}'
   require(pins[src]['sha256']==h,'ORIGINAL_CHECKPOINT_HASH:'+name)
  minute=omitted['files'][cell];require(minute['sha256']==cp['files']['MINUTE.npz'] and minute['bytes']==pins[minute['source']]['bytes'],'OMITTED_MINUTE_PIN')
  ctl=next(x for x in controller['cases'] if x['cell_id']==cell);require(ctl['checkpoint_SHA256']==hashlib.sha256(raw(root/'cases'/cell/'TERMINAL_CHECKPOINT.json')).hexdigest(),'CONTROLLER_CHECKPOINT_BINDING')
  require(proof['exact_native40_NAV']==review['exact_financials']['NAV']==r['summary']['decimal_strings']['NAV'],'NAV_REVIEW_BINDING')
  out.append({'cell_id':cell,'exact_NAV':proof['exact_native40_NAV'],'financial_ledger_rows':proof['financial_ledger_rows_checked'],'paid_warning_exits':len(wr),'saved_risk_overshoot_minutes':risk['forecast_volatility_breach_minutes']})
 require(warnings==11 and breaches==331228,'AGGREGATE_WARNING_RISK_COUNTS');validate_report(read(root/'RESULTS_REPORT.json'),terminal)
 return {'status':'PASS_COMPACT_SAVED_FINANCIAL_AND_RECEIPT_RECOVERY','cases':out,'retained_members_rehashed':len(files),'exact_copy_files':len(pairs),'lossless_gzip_originals':len(compressed),'accounts_constructed':0,'financial_minutes_advanced':0,'full_minute_risk_regenerated':False,'full_minute_arrays_omitted':True,'private_GO_bodies_omitted':True,'source_remote_reference_pending_at_seal':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parent));args=p.parse_args();print(json.dumps(verify(args.root),sort_keys=True,allow_nan=False))

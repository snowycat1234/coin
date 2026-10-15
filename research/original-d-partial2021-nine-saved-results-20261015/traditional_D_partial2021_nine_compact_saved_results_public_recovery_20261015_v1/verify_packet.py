#!/usr/bin/env python3
"""Exact public saved-evidence checks; no constructors or source-array loading."""
from pathlib import Path
from decimal import Decimal
from copy import deepcopy
import hashlib,json,gzip,argparse
from saved_native_reconciliation import reconcile_saved_native
from saved_report import *
AGG='24bed5ada24b3dae6f945da816e2bea9c9fb45b9f458faf1c36f944305e5fd2e'
FINAL='447d6b1891bb4d8ddfdc33778145556a1a5849710a0583ddb5003629f0e6ef27'
EXIT='43e8782e0e81593ebf16102e7a46ff457260e7fcff0570108d2178a79d024df6'
SOURCE_ARCHIVE='b0dcec82a6f8c28feba170aa080a131fb6c6494b3b06b2046a962e99f004c8f7'

def validate_financial(a,r,p):
 got=reconcile_saved_native(a,r,expected_continuation_version=VERSION)
 require(same(got,p),'EXACT_TYPED_NATIVE40_PROOF_WITH_RAW100_RESIDUALS_REQUIRED')
 require(p['checker_SHA256']==CHECKER and p['tolerance_or_epsilon_used'] is False,'FROZEN_NO_EPSILON_CHECKER')
 require(type(p['account_objects_constructed']) is int and p['account_objects_constructed']==0 and type(p['financial_clocks_advanced']) is int and p['financial_clocks_advanced']==0,'SAVED_ONLY_BOUNDARY')
 require(a['settlement_journal']==a['transfer_journal']==[] and a['transfer_ids']=={} and Decimal(a['unpaid_liability'])==0,'NO_TRANSFER_SETTLEMENT_SUPPORT_OR_DEBT')
 require(all(Decimal(x['quantity'])==Decimal(x['isolated_balance'])==0 and x['opened_us'] is None for x in a['positions'].values()),'EXACT_PAID_FLAT_POSITION_AND_MARGIN')
 require(all(not x.get('liquidation_takeover') for x in a['trades']),'NO_CONDITIONAL_TAKEOVER')
 e=r['economics'];s=r['summary']
 for key,expected in {'actual_paid_market_flat':True,'conditional_settled_flat':False,'full_calendar':True,'partial_DEV':True,'partial_return_annualized':False,'annual_wallets_compounded':False,'conditional_position_settlements':0,'actual_liquidation_fills':0}.items():
  require(same(e[key],expected),'EXACT_FINANCIAL_TAXONOMY:'+key)
 require(s['funding_rate_unit']=='UNCONFIRMED' and s['publication_certified'] is False and s['unit_certified'] is False,'HONEST_VENUE_AND_FUNDING_QUALIFICATION')
 require(s['funding_observed_events']==4110 and s['funding_account_applied_events']==len(a['funding'])==4105 and s['fresh_flat_no_past_mark_events']==5,'DISTINCT_SOURCE_COVERAGE_AND_NATIVE_FUNDING')
 require(r['chronological_native40_saved_proof_required_before_terminal_admission'] is True and r['legacy_delta_sum_reconciliation_is_authoritative'] is False,'NATIVE40_AUTHORITY_REQUIRED')
 require(same(r['primary_financial_reconciliation'],r['legacy_primary_financial_reconciliation']),'UNALTERED_EMBEDDED_LEGACY_DIAGNOSTIC')
 return got

def validate_identity(receipt,audit,result,review,descriptor):
 cell=descriptor['cell_id'];tier=descriptor['tier'];strategy=descriptor['strategy']
 for key,value in {'cell_id':cell,'year':2021,'strategy':strategy,'tier':tier,'config':strategy+'_'+tier,'calendar':CALENDAR,'completed_minutes':394560,'required_minutes':394560,'root_GO_SHA256':GO,'preparation_SHA256':PREP,'manifest_SHA256':FROZEN,'independent_review_SHA256':SOURCE_REVIEW,'status':'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT','policy_variant':'GUARD50_EXIT_ONLY'}.items():require(same(receipt[key],value),'EXACT_TYPED_CASE_IDENTITY:'+key)
 binding=audit['historical_execution_scope']
 expected={'cell_id':cell,'year':2021,'strategy':strategy,'tier_name':tier,'config':strategy+'_'+tier,'calendar':CALENDAR,'days':274,'required_minutes':394560,'root_GO_SHA256':GO,'preparation_SHA256':PREP,'manifest_SHA256':FROZEN,'independent_review_SHA256':SOURCE_REVIEW,'fresh_genesis_only':True,'generated_fixture_scope_used':False}
 for key,value in expected.items():require(same(binding[key],value),'EXACT_TYPED_SCOPE_BINDING:'+key)
 require(same(audit['contract']['scope_binding'],binding) and same(result['summary']['contract']['scope_binding'],binding),'CONSISTENT_EXACT_SCOPE_BINDING')
 for key in ('input_binding_SHA256','policy_identity','source_identity'):
  require(type(binding[key]) is str and len(binding[key])==64 and binding[key]==review[key],'REVIEW_PINNED_IDENTITY:'+key)
 for key,value in {'cell_id':cell,'strategy':strategy,'tier':tier,'status':'PASS_SAVED_ONLY_NO_FINANCIAL_RERUN','root_GO_SHA256':GO,'preparation_SHA256':PREP,'manifest_SHA256':FROZEN,'source_generated_review_SHA256':SOURCE_REVIEW,'calendar':CALENDAR,'days':274,'completed_minutes':394560,'review_financial_reruns':0,'review_account_constructions':0,'review_provider_iterations':0,'review_GO_edits':0,'review_claims_created':0,'review_process_launches':0,'partial_period_return_annualized':False,'annual_or_cross_cell_wallets_compounded':False}.items():require(same(review[key],value),'EXACT_TYPED_INDEPENDENT_REVIEW:'+key)
 require(audit['config']['initial_cash']=='10000' and audit['config']['leverage']=='1' and audit['contract']['topup_enabled'] is False,'EXACT_FRESH_10000_ONE_X_NO_TOPUP')
 require(same(result['summary'],review['summary']) and same(result['economics'],review['economics']),'EXACT_REVIEWED_SUMMARY_ECONOMICS')
 require(same(receipt['code_identity'],review['code_identity']),'EXACT_CODE_IDENTITY')
 require(review['terminal_signal_us']==1640991540000000 and 1640991600000001<=review['last_actual_paid_fill_us']<CALENDAR[1],'DECLARED_FINAL60_MINUTE_PAID_TERMINAL_WINDOW')
 require(all(CALENDAR[0]<=t['signal_us']<t['event_us']<CALENDAR[1] for t in audit['trades']),'EXACT_PAID_TRADE_CLOCK_SCOPE')
 return True

def normalized_audit(value):
 v=deepcopy(value);v.pop('historical_execution_scope');v['contract'].pop('scope_binding');v.pop('fill_requests');return v
def normalized_request(value):
 v=deepcopy(value);v['identity'].pop('quantity')
 for k in ('requested_quantity','remaining_quantity'):
  v['receipt'].pop(k,None);v['receipt'].get('decimal_strings',{}).pop(k,None)
 return v

def verify(root,*,require_publication=True):
 root=Path(root).resolve();m=load(root/'MANIFEST.json');files=m['files']
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 require(actual==set(files)|{'MANIFEST.json'},'EXACT_PACKET_FILESET')
 for rel,pin in files.items():
  p=root/rel;require(hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256'] and p.stat().st_size==pin['bytes'],'EXACT_PACKET_MEMBER:'+rel)
 require(sha(root/'saved_native_reconciliation.py')==CHECKER,'EXACT_UNCHANGED_PURE_NATIVE40_CHECKER')
 require(sha(root/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')==FROZEN,'EXACT_FROZEN_NINE_MANIFEST')
 require(sha(root/REV/'INDEPENDENT_NINE_SAVED_REVIEW.json')==AGG,'EXACT_NINE_FINANCIAL_REVIEW')
 require(sha(root/REV/'FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json')==FINAL,'EXACT_FINAL_INDEPENDENT_REVIEW')
 require(sha(root/ATT/'ROOT_OBSERVED_EXIT.json')==EXIT,'ROOT_OWNS_ACTUAL_CONTROLLER_EXIT')
 agg=load(root/REV/'INDEPENDENT_NINE_SAVED_REVIEW.json');require(agg['reviewed_cell_count']==9 and agg['all_nine_executed_separately'] is True and same(agg['ordered_cells'],list(CELLS)),'EXACT_NINE_AGGREGATE_SCOPE')
 require(agg['aggregate_native_minutes_checked']==3551040 and agg['alias_mapping']=={} and agg['financial_reruns']==agg['account_constructions']==0,'NINE_SEPARATE_ACCOUNTS_NOT_COMPOUNDED')
 exit=load(root/ATT/'ROOT_OBSERVED_EXIT.json');require(type(exit['exit_code']) is int and exit['exit_code']==0 and exit['root_GO_SHA256']==GO and exit['no_financial_rerun'] is True,'ROOT_EXACT_EXIT_CONFIRMATION')
 final=load(root/REV/'FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json')
 require(same(final['root_observed_exit'],exit) and final['root_observed_exit_receipt']['SHA256']==EXIT and final['base_nine_saved_review']['SHA256']==AGG and final['equality_receipt']['SHA256']==EQUALITY,'EXACT_FINAL_REVIEW_BINDING')
 require(final['process_exit_confirmed_by_root_not_inferred_by_reviewer'] is True and final['all_nine_native40_all_event_states_pass'] is True and final['all_nine_full_calendar_actual_paid_market_flat'] is True,'FINAL_SAVED_TERMINAL_ADMISSION')
 preservation=load(root/'FULL_SAVED_OUTPUT_HASH_PINS.json');pins=preservation['files'];copies=load(root/'EXACT_COPY_SOURCE_MAP.json');gz=load(root/'LOSSLESS_GZIP_SOURCE_MAP.json')
 for dest,src in copies.items():require(sha(root/dest)==pins[src]['sha256'] and len(raw(root/dest))==pins[src]['bytes'],'EXACT_ORIGINAL_COPY:'+dest)
 for dest,ref in gz.items():
  b=raw(root/dest[:-3]);require(hashlib.sha256(b).hexdigest()==ref['uncompressed_sha256']==pins[ref['source']]['sha256'] and len(b)==ref['uncompressed_bytes']==pins[ref['source']]['bytes'],'LOSSLESS_ORIGINAL_BYTES:'+dest)
 omission=load(root/'OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json');require(omission['all_minute_risk_regeneration_self_contained'] is False and omission['omitted_bytes_recoverable_from_hashes'] is False and len(omission['MINUTE_outputs'])==9,'HONEST_NINE_OMITTED_ARRAY_SCOPE')
 admission=load(root/'EXTERNAL_ADMISSION_HASH_ONLY.json');require(admission['root_GO_sha256']==GO and admission['private_GO_bodies_included'] is False and admission['new_run_or_publication_authority_granted'] is False,'HASH_ONLY_NO_AUTHORITY')
 source=load(root/'SOURCE_PUBLICATION_REFERENCE.json')
 if require_publication:
  require(source['status']=='FULL_REMOTE_BYTES_VERIFIED' and source['every_remote_byte_matches_expected_local'] is True and source['source_archive_sha256']==SOURCE_ARCHIVE,'VERIFIED_SOURCE_BEFORE_RESULTS_REQUIRED')
  require(source['source_parent_commit']=='bf2b1d40df9958033e7d61c38c5b8f343127771b' and source['source_independent_packet_review_sha256']=='ea701c7ef110aa404301215242b3fcf412df126cb240d173f1f6a3abcb8ca63e','EXACT_MONITOR_RESULTS_THEN_SOURCE_CHAIN')
  require(m['sole_authorized_results_publication_parent']==source['source_commit'] and source['results_publication_must_be_additive_child_of_source_commit'] is True,'STRICT_SOURCE_BEFORE_RESULTS_CHAIN')
 frozen=load(root/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json');require([c['cell_id'] for c in frozen['cells']]==list(CELLS),'EXACT_DECLARED_NINE_ORDER')
 rows=[]
 for desc in frozen['cells']:
  cell=desc['cell_id'];d=root/ATT/cell;a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');r=load(d/'NATIVE_RESULT.json');p=load(d/'NATIVE40_RECONSTRUCTION_PROOF.json');cp=load(d/'TERMINAL_CHECKPOINT.json');receipt=load(d/'CASE_RECEIPT.json');review=load(root/REV/(cell+'_SAVED_REVIEW.json'))
  validate_financial(a,r,p);validate_identity(receipt,a,r,review,desc)
  require(same(p,load(d/'PRIMARY_FINANCIAL_RECONCILIATION.json')) and same(p,review['authoritative_native40_proof']),'NATIVE40_PROOF_IDENTITY')
  require(same(load(d/'ACTUAL_HELD_RISK_REPORT.json'),review['actual_held_risk']),'EXACT_REVIEWED_HELD_RISK')
  require(sha(root/REV/(cell+'_SAVED_REVIEW.json'))==agg['cell_review_receipts'][cell]['SHA256'],'AGGREGATE_REVIEW_BINDING')
  require(cp['all_evidence_fsynced'] is True and cp['restart_financial_snapshot_permission'] is False,'CHECKPOINT_NO_RESTART_AUTHORITY')
  for name,h in cp['files'].items():require(pins[f'{ATT}/{cell}/{name}']['sha256']==h,'CHECKPOINT_ORIGINAL_PIN:'+cell+':'+name)
  for name,ref in review['evidence'].items():require(pins[f'{ATT}/{cell}/{name}']=={'sha256':ref['SHA256'],'bytes':ref['bytes']},'INDEPENDENT_ORIGINAL_BINDING:'+cell+':'+name)
  require(cp['files']['MINUTE.npz']==omission['MINUTE_outputs'][cell]['sha256'],'OMITTED_EXACT_MINUTE_PIN')
  rows.append(dict(cell_id=cell,exact_NAV=p['exact_native40_NAV'],native40_ledger_events=p['financial_ledger_rows_checked'],paid_flat=True))
 eq=load(root/REV/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json');require(sha(root/REV/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json')==EQUALITY,'EXACT_POST_HOC_EQUALITY_REVIEW')
 for pair in eq['pairs']:
  a=load(root/ATT/pair['STATIC50_cell']/'ACCOUNT_FINANCIAL_AUDIT.json');b=load(root/ATT/pair['H090_cell']/'ACCOUNT_FINANCIAL_AUDIT.json')
  na,nb=normalized_audit(a),normalized_audit(b);require(same(na,nb),'EXACT_FINANCIAL_HISTORY_WITH_REQUESTS_EXCLUDED')
  require(hashlib.sha256(canonical(na).encode()).hexdigest()==pair['normalized_realized_financial_state_and_history_SHA256'],'EXACT_NORMALIZED_FINANCIAL_HASH')
  require(not same(a,b) and not same(a['fill_requests'],b['fill_requests']),'DISTINCT_FULL_AUDITS_AND_REQUEST_INTENTS_RETAINED')
  require(set(a['fill_requests'])==set(b['fill_requests']),'REQUEST_IDENTITY_SET')
  differences=0
  for key,av in a['fill_requests'].items():
   bv=b['fill_requests'][key];differences+=not same(av,bv);require(same(normalized_request(av),normalized_request(bv)),'ONLY_REQUESTED_AND_REMAINING_QUANTITIES_DIFFER')
  require(differences==pair['different_fill_request_records'] and pair['full_saved_financial_audit_exact_except_scope_metadata'] is False,'HONEST_AUDIT_NONIDENTITY')
 rebuilt=build(root);validate_scope(rebuilt['scope']);require(json_bytes(rebuilt)==raw(root/'summary/REPORT.json'),'BYTE_EXACT_JSON_REPORT_RERENDER')
 require(render_text(rebuilt).encode()==raw(root/'summary/REPORT.txt'),'BYTE_EXACT_TEXT_REPORT_RERENDER')
 require(render_csv(rebuilt['rows']).encode()==raw(root/'summary/REPORT.csv'),'BYTE_EXACT_NINE_CSV_RERENDER')
 require(render_csv(rebuilt['descriptive_period_rows']).encode()==raw(root/'summary/DESCRIPTIVE_PERIOD_TABLE.csv'),'BYTE_EXACT_27_PERIOD_CSV_RERENDER')
 markers=[b'/' + b'workspace/',b'/' + b'tmp/',b'/' + b'home/agent/',b'/' + b'Users/',b'-----BEGIN '+b'PRIVATE KEY',b'github_'+b'pat_',b'gh'+b'p_',b'Bearer'+b' ']
 for rel in files:
  p=root/rel;require(p.suffix not in ('.npz','.npy','.log') and p.name not in ('ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json','BOOTSTRAP_READY.json'),'PUBLIC_ALLOWLIST')
  b=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes();require(not any(v in b for v in markers),'PRIVATE_CONTENT:'+rel)
 return dict(status='PASS_NINE_PARTIAL2021_COMPACT_SAVED_PACKET',cases=rows,files_rehashed=len(files),exact_original_copies=len(copies),lossless_gzip_originals=len(gz),native40_events=sum(r['native40_ledger_events'] for r in rows),byte_exact_report_rerender=True,descriptive_period_table_rows=27,full_MINUTE_arrays_included=False,all_minute_risk_regenerated=False,accounts_constructed=0,financial_minutes_advanced=0,publication_performed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));args=p.parse_args();print(json.dumps(verify(args.root),sort_keys=True))

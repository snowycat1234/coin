"""Exact saved-JSON event/proof checks, byte pins and report regeneration."""
from pathlib import Path
from decimal import Decimal
import hashlib,gzip,argparse,json,zipfile,stat
from pathlib import PurePosixPath
from saved_report import *
from saved_native_reconciliation import reconcile_saved_native

def validate_member_names(names,expected=None):
 require(len(names)==len(set(names)),'DUPLICATE_ARCHIVE_OR_MANIFEST_MEMBER')
 for rel in names:
  require(type(rel) is str and rel and not rel.startswith('/') and '\\' not in rel and ':' not in rel and '\x00' not in rel,'UNSAFE_MEMBER_PATH')
  require(str(PurePosixPath(rel))==rel and all(p not in ('','..','.') for p in rel.split('/')),'PATH_ALIAS_OR_TRAVERSAL_MEMBER:'+rel)
 if expected is not None:require(set(names)==set(expected),'MISSING_OR_EXTRA_ARCHIVE_OR_MANIFEST_MEMBER')
 return True

def verify_archive(archive):
 with zipfile.ZipFile(archive) as z:
  infos=z.infolist();names=[i.filename for i in infos];validate_member_names(names)
  prefix=PACKET_NAME+'/'
  require(all(n.startswith(prefix) for n in names),'EXACT_ARCHIVE_ROOT_PREFIX')
  for i in infos:
   require(not i.is_dir() and not i.flag_bits&1 and stat.S_IFMT(i.external_attr>>16)==stat.S_IFREG,'UNSAFE_NONREGULAR_ENCRYPTED_ARCHIVE_MEMBER')
  manifest_name=prefix+'MANIFEST.json';require(manifest_name in names,'ARCHIVE_MANIFEST_REQUIRED');manifest=strict_json(z.read(manifest_name));files=manifest['files'];validate_member_names(list(files));validate_member_names(names,[prefix+n for n in files]+[manifest_name])
  for rel,ref in files.items():
   require(type(ref['bytes']) is int and ref['bytes']>=0,'EXACT_ARCHIVE_MEMBER_SIZE_TYPE')
   b=z.read(prefix+rel);require(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'EXACT_ARCHIVE_MEMBER_BYTES:'+rel)
  return {'status':'PASS_EXACT_SAFE_COMPACT_ARCHIVE','members':len(names),'manifest_sha256':hashlib.sha256(z.read(manifest_name)).hexdigest(),'duplicate_missing_extra_alias_traversal_symlink_or_encrypted_members':False}

def validate_financial(a,r,p):
 got=reconcile_saved_native(a,r,expected_continuation_version=VERSION)
 require(same(got,p),'EXACT_TYPED_NATIVE40_PROOF_WITH_RAW100_RESIDUALS_REQUIRED')
 require(p['checker_SHA256']==CHECKER and p['tolerance_or_epsilon_used'] is False,'EXACT_FROZEN_NO_EPSILON_CHECKER')
 for k in ('account_objects_constructed','financial_clocks_advanced'):require(type(p[k]) is int and p[k]==0,'EXACT_SAVED_ONLY_BOUNDARY:'+k)
 require(p['financial_values_changed'] is False and p['native_financial_precision']==40 and p['raw_diagnostic_precision']==100,'EXACT_NATIVE40_RAW100_SEPARATION')
 require(a['transfer_journal']==[] and a['transfer_ids']=={},'ORIGINAL_D_NO_TRANSFERS')
 require(a['config']['initial_cash']=='10000' and a['config']['leverage']=='1' and a['contract']['topup_enabled'] is False,'FRESH_10000_ONE_X_NO_TOPUP')
 e=r['economics'];s=r['summary']
 for k,v in {'full_calendar':True,'full_year_DEV':True,'adaptive_DEV_only':True,'annual_wallet_fresh_genesis':True,'annual_wallets_compounded':False,'actual_historical_liquidation_or_no_liquidation_certified':False,'nominal_tier_is_not_exact_realized_risk_matching':True}.items():require(same(e[k],v),'EXACT_HONEST_ECONOMICS:'+k)
 require(s['funding_rate_unit']=='UNCONFIRMED' and s['publication_certified'] is False and s['unit_certified'] is False,'UNCERTIFIED_FUNDING_UNITS_AND_PUBLICATION')
 require(r['chronological_native40_saved_proof_required_before_terminal_admission'] is True and r['legacy_delta_sum_reconciliation_is_authoritative'] is False,'NATIVE40_IS_AUTHORITY')
 require(same(r['primary_financial_reconciliation'],r['legacy_primary_financial_reconciliation']),'UNMODIFIED_EMBEDDED_LEGACY_DIAGNOSTIC')
 return got

def validate_identity(receipt,audit,result,review,cell):
 strategy=cell.removeprefix('2025_').removesuffix('_JAN1_DEC31_D').rsplit('_',1)[0];tier=cell.removesuffix('_JAN1_DEC31_D').rsplit('_',1)[1]
 expected={'cell_id':cell,'year':2025,'strategy':strategy,'tier':tier,'config':strategy+'_'+tier,'calendar':CALENDAR,'completed_minutes':525600,'required_minutes':525600,'root_GO_SHA256':GO,'preparation_SHA256':PREP,'manifest_SHA256':FROZEN,'independent_review_SHA256':SOURCE_REVIEW,'policy_variant':'GUARD50_EXIT_ONLY','cost':'BASE27','adaptive_DEV_only':True,'snapshot_restart_certified':False,'automatic_retry':False}
 for k,v in expected.items():require(same(receipt[k],v),'EXACT_TYPED_CASE_IDENTITY:'+k)
 binding=audit['historical_execution_scope']
 for k,v in {'cell_id':cell,'year':2025,'strategy':strategy,'tier_name':tier,'config':strategy+'_'+tier,'calendar':CALENDAR,'days':365,'required_minutes':525600,'root_GO_SHA256':GO,'preparation_SHA256':PREP,'manifest_SHA256':FROZEN,'independent_review_SHA256':SOURCE_REVIEW,'fresh_genesis_only':True,'generated_fixture_scope_used':False,'quality_sidecar_sha256':QUALITY}.items():require(same(binding[k],v),'EXACT_TYPED_EXECUTION_SCOPE:'+k)
 require(same(audit['contract']['scope_binding'],binding) and same(result['summary']['contract']['scope_binding'],binding),'EXACT_SCOPE_BINDING_AGREEMENT')
 for k,v in {'cell_id':cell,'year':2025,'strategy':strategy,'tier':tier,'calendar':CALENDAR,'root_GO_SHA256':GO,'preparation_SHA256':PREP,'independent_admission_review_SHA256':SOURCE_REVIEW,'completed_minutes':525600,'required_minutes':525600,'status':'PASS_SAVED_TERMINAL_WITH_EXPLICIT_SOURCE_CAVEATS','native40_every_event_exact':True,'financial_values_changed':False,'financial_replays_or_reruns_by_reviewer':0,'actual_accounts_constructed_by_reviewer':0,'provider_iterations_by_reviewer':0,'process_or_claim_or_GO_creations_by_reviewer':0,'publication_actions':0,'actual_native_exchange_fills_funding_publication_filters_insurance_or_liquidation_certified':False}.items():require(same(review[k],v),'EXACT_TYPED_INDEPENDENT_REVIEW:'+k)
 require(same(result['economics'],review['economics']) and same({k:result['summary']['decimal_strings'][k] for k in review['exact_financials']},review['exact_financials']),'EXACT_REVIEWED_FINANCIALS_AND_ECONOMICS')
 require(receipt['status']==review['terminal_classification'],'EXACT_TERMINAL_TAXONOMY')
 require(all(CALENDAR[0]<=t['signal_us']<t['event_us']<CALENDAR[1] for t in audit['trades']),'EXACT_PAID_TRADE_CLOCKS')
 quality=review['source_quality_review']
 for k,v in {'derived_mark_asset_minutes':0,'quality_intervals':0,'source_clock_cells':0,'quality_receipt_count':0,'no_2022_27point_carry_provenance_applies':True,'endpoint_origin':'GENUINE_DEC31_2359_NATIVE_BAR','actual_arrival_installation':'UNKNOWN_NOT_CERTIFIED','actual_exchange_liquidation_or_no_liquidation_certified':False,'quality_sidecar_SHA256':QUALITY}.items():require(same(quality[k],v),'EXACT_GENUINE_NO_IMPUTATION_SOURCE_QUALITY:'+k)
 require(review['scheduler_source_funding_rows']==5475 and review['total_saved_funding_rows']==5470,'EXACT_SOURCE5475_NATIVE5470_FUNDING_DISTINCTION')
 cold=review['coldstart_no_position_no_past_mark_funding'];require(len(cold)==5 and review['coldstart_observed_event_offsets_us']==[15000],'FIVE_INITIAL_FUNDING_EVENTS_AT_PLUS15MS')
 for f in cold:require(f['event_us']==CALENDAR[0]+15000 and f['status']=='NO_POSITION_NO_PAST_MARK' and f['owned'] is False and f['mark_close_us'] is None and f['mark_price'] is None and f['quantity']==0 and f['signed_funding_USDT']==0,'EXACT_UNOWNED_NO_PRIOR_MARK_NO_CHARGE_COLDSTART')
 require(receipt['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' and result['economics']['actual_paid_market_flat'] is True and result['economics']['conditional_position_settlements']==0 and Decimal(result['summary']['decimal_strings']['unpaid_liability'])==0,'FULL_YEAR_PAID_FLAT_ZERO_DEBT_NO_CONDITIONAL_SETTLEMENT')
 require(Decimal(review['exact_marked_net_return'])<0,'SAVED_NET_NEGATIVE')
 risk=review['actual_held_exposure_and_both_covariance_phase_risk'];require(set(risk['covariance_phases'])=={'CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION','CLOSE_WITH_SAMECLOCK_DAILY_DECISION'},'BOTH_COVARIANCE_PHASE_CONVENTIONS')
 return True

def validate_source(source,require_publication=False):
 require(source['source_archive_sha256']==SOURCE_ARCHIVE and source['source_archive_bytes']==1559883 and source['source_packet_independent_review_sha256']==SOURCE_PACKET_REVIEW,'EXACT_NEW_SOURCE_ARCHIVE_AND_REVIEW')
 require(source['no_run_or_publication_authority_granted'] is True and source['results_publication_must_be_additive_child_of_verified_new2025_source'] is True,'SOURCE_BEFORE_RESULTS_REQUIRED')
 if require_publication:require(source['status']=='FULL_REMOTE_BYTES_VERIFIED' and source['every_remote_byte_matches_expected_local'] is True and type(source['source_commit']) is str and len(source['source_commit'])==40,'VERIFIED_NEW2025_SOURCE_COMMIT_REQUIRED_BEFORE_PUBLICATION')
 else:require(source['status'] in ('BLOCKED_PENDING_VERIFIED_REMOTE_SOURCE_PUBLICATION','FULL_REMOTE_BYTES_VERIFIED'),'HONEST_SOURCE_PUBLICATION_STATE')

def verify(root,*,require_publication=False):
 root=Path(root).resolve();m=load(root/'MANIFEST.json');files=m['files'];validate_member_names(list(files));actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 require(actual==set(files)|{'MANIFEST.json'},'EXACT_PACKET_FILESET')
 for rel,ref in files.items():
  p=root/rel;require(not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256'] and p.stat().st_size==ref['bytes'],'EXACT_PACKET_MEMBER:'+rel)
 require(sha(root/'saved_native_reconciliation.py')==CHECKER,'EXACT_UNCHANGED_PURE_NATIVE40_CHECKER')
 require(sha(root/EXEC/'FROZEN_NINE_CELL_MANIFEST.json')==FROZEN,'FROZEN_EXACT_NINE_MANIFEST')
 require(sha(root/PREPDIR/'PREPARATION.json')==PREP,'EXACT_FROZEN_PREPARATION')
 require(sha(root/'source_admission_review/INDEPENDENT_SOURCE_REVIEW_RECEIPT.json')==SOURCE_REVIEW,'EXACT_INDEPENDENT_PREPARED_SOURCE_REVIEW')
 freeze=load(root/'INDEPENDENT_REVIEW_AND_ROOT_EXIT_PINS.json')
 for rel,ref in freeze['files'].items():require(sha(root/rel)==ref['sha256'] and len(raw(root/rel))==ref['bytes'],'EXACT_IMMUTABLE_FINAL_REVIEW_OR_ROOT_EXIT:'+rel)
 require(sha(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json')==FINAL_REVIEW,'EXACT_EXTERNALLY_FROZEN_FINAL_NINE_REVIEW');final=load(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json');require(final['ordered_cells']==list(CELLS) and final['status']=='PASS_ALL_NINE_SEALED_SAVED_TERMINALS_WITH_EXPLICIT_SOURCE_CAVEATS' and final['native40_every_event_authoritative'] is True,'FINAL_ALL_NINE_INDEPENDENT_SAVED_REVIEW')
 final_checkpoint=load(root/REV/'FINAL_NINE_REVIEW_CHECKPOINT.json')
 for name,ref in final_checkpoint['files'].items():require(sha(root/REV/name)==ref['SHA256'] and len(raw(root/REV/name))==ref['bytes'],'IMMUTABLE_FINAL_REVIEW_CHECKPOINT:'+name)
 for name,ref in final['review_evidence'].items():require(sha(root/REV/name)==ref['SHA256'] and len(raw(root/REV/name))==ref['bytes'],'FINAL_AGGREGATE_CASE_REVIEW_BINDING:'+name)
 require(final['all_nine_explicit_fresh10000'] is True and final['alias_mapping']=={} and final['no_transfers_topups_or_capital_injections'] is True,'EXACT_NINE_SEPARATE_FRESH_ACCOUNTS')
 require(sha(root/freeze['root_exit_path'])==ROOT_EXIT,'EXACT_EXTERNALLY_OBSERVED_ROOT_EXIT_RECEIPT');root_exit=load(root/freeze['root_exit_path']);require(root_exit['exit_code']==0 and type(root_exit['exit_code']) is int and root_exit['root_GO_SHA256']==GO,'ROOT_ACTUAL_ZERO_EXIT_RECEIPT')
 require(root_exit['no_financial_rerun'] is True and root_exit['controller_receipt_SHA256']==final['controller_receipt']['SHA256'],'ROOT_EXIT_BINDS_EXACT_CONTROLLER_AND_NO_RERUN')
 require(freeze['actual_root_exit_confirmed_not_inferred'] is True,'ROOT_PROCESS_EXIT_SEPARATE_FROM_SAVED_CONTROLLER')
 pins=load(root/'FULL_SAVED_OUTPUT_HASH_PINS.json')['files'];controller_ref=final['controller_receipt'];controller_rel=ATT+'/CONTROLLER_RECEIPT_'+GO+'.json';require(pins[controller_rel]=={'sha256':controller_ref['SHA256'],'bytes':controller_ref['bytes']},'FINAL_REVIEW_BINDS_LOCAL_ONLY_CONTROLLER_RECEIPT');copies=load(root/'EXACT_COPY_SOURCE_MAP.json');gz=load(root/'LOSSLESS_GZIP_SOURCE_MAP.json')
 for dest,src in copies.items():require(sha(root/dest)==pins[src]['sha256'] and len(raw(root/dest))==pins[src]['bytes'],'EXACT_ORIGINAL_COPY:'+dest)
 for dest,ref in gz.items():
  b=raw(root/dest[:-3]);require(hashlib.sha256(b).hexdigest()==ref['uncompressed_sha256']==pins[ref['source']]['sha256'] and len(b)==ref['uncompressed_bytes']==pins[ref['source']]['bytes'],'LOSSLESS_ORIGINAL_GZIP_BYTES:'+dest)
 omitted=load(root/'OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json');require(omitted['all_minute_risk_regeneration_self_contained'] is False and omitted['omitted_bytes_recoverable_from_hashes'] is False and set(omitted['MINUTE_outputs'])==set(CELLS),'HONEST_OMITTED_MINUTE_ARRAY_SCOPE')
 admission=load(root/'EXTERNAL_ADMISSION_HASH_ONLY.json');require(admission['root_GO_sha256']==GO and admission['private_GO_bodies_included'] is False and admission['new_run_or_publication_authority_granted'] is False,'PRIVATE_AUTHORITY_HASH_ONLY')
 validate_source(load(root/'SOURCE_PUBLICATION_REFERENCE.json'),require_publication)
 rows=[]
 for cell in CELLS:
  d=root/ATT/cell;a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');r=load(d/'NATIVE_RESULT.json');p=load(d/'NATIVE40_RECONSTRUCTION_PROOF.json');cp=load(d/'TERMINAL_CHECKPOINT.json');receipt=load(d/'CASE_RECEIPT.json');review=load(root/REV/(cell+'_REVIEW.json'))
  validate_financial(a,r,p);validate_identity(receipt,a,r,review,cell)
  require(same(p,load(d/'PRIMARY_FINANCIAL_RECONCILIATION.json')) and same(p,review['native40_proof']),'EXACT_NATIVE40_PROOF_IDENTITY')
  require(cp['all_evidence_fsynced'] is True and cp['restart_financial_snapshot_permission'] is False,'IMMUTABLE_TERMINAL_NO_RESTART_AUTHORITY')
  for name,h in cp['files'].items():require(pins[ATT+'/'+cell+'/'+name]['sha256']==h,'EXACT_CHECKPOINT_ORIGINAL_PIN:'+cell+':'+name)
  for name,ref in review['evidence'].items():require(pins[ATT+'/'+cell+'/'+name]=={'sha256':ref['SHA256'],'bytes':ref['bytes']},'INDEPENDENT_REVIEW_ORIGINAL_PIN:'+cell+':'+name)
  require(cp['files']['MINUTE.npz']==omitted['MINUTE_outputs'][cell]['sha256'],'EXACT_OMITTED_MINUTE_PIN')
  require(sha(root/REV/(cell+'_REVIEW.json'))==freeze['files'][REV+'/'+cell+'_REVIEW.json']['sha256'],'FINAL_INDEPENDENT_CASE_REVIEW_PIN')
  rows.append({'cell_id':cell,'exact_NAV':p['exact_native40_NAV'],'native40_events':p['financial_ledger_rows_checked']})
 companion=load(root/REV/'ROOT_EXIT_BINDING_COMPANION.json');require(sha(root/REV/'ROOT_EXIT_BINDING_COMPANION.json')=='a7cb2560ff40ae75e573d34c885442fe1f6d58e9eecba7870f7c809d5425918c','EXACT_INDEPENDENT_ADDITIVE_ROOT_EXIT_BINDING')
 projection=load(root/'SAVED_CONTROLLER_PUBLIC_PROJECTION.json');require(projection['original']=={'source':controller_rel,**pins[controller_rel]} and projection['original_bytes_included'] is False and projection['derivative_not_root_process_exit_evidence'] is True,'HONEST_PUBLIC_CONTROLLER_DERIVATIVE')
 require(len(projection['cases'])==len(CELLS) and {c['cell_id'] for c in projection['cases']}==set(CELLS) and all(c['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' for c in projection['cases']),'PROJECTED_CONTROLLER_ALL9_STATUSES')
 for c in projection['cases']:require(c['checkpoint_SHA256']==pins[ATT+'/'+c['cell_id']+'/TERMINAL_CHECKPOINT.json']['sha256'] and c['reused_saved_terminal'] is False,'DISTINCT_FRESH_SAVED_CONTROLLER_CASES')
 require(projection['copied_fields']['root_GO_SHA256']==GO and projection['copied_fields']['manifest_SHA256']==FROZEN and projection['copied_fields']['status']=='ALL_ADMITTED_ORDERED_CELLS_TERMINAL','PROJECTED_SAVED_CONTROLLER_EXACT_IDENTITY')
 comparison=load(root/REV/'H090_STATIC50_THREE_TIER_PATH_COMPARISON.json');require(sha(root/REV/'H090_STATIC50_THREE_TIER_PATH_COMPARISON.json')==final['same_tier_path_equality_evidence']['SHA256'],'EXACT_POSTHOC_FULL525600_MINUTE_COMPARISON_PROOF')
 require(len(final['H090_STATIC50_same_tier_actual_paths'])==3 and all(v['all_saved_minute_fields_bit_equal'] is True and v['differing_minute_rows']==0 and v['fixed_selected_raw_targets_equal'] is False and v['independent_confirmation'] is False for v in final['H090_STATIC50_same_tier_actual_paths']),'POSTHOC_THREE_PAIR_EQUALITY_NOT_INDEPENDENCE')
 require(sha(root/'full2025_source_generated_packet_independent_review_20261015/FINAL_REVIEW_RECEIPT.json')==SOURCE_PACKET_REVIEW,'EXACT_SOURCE_PACKET_LOCAL_REVIEW_IDENTITY')
 require(sha(root/'full2025_source_generated_packet_independent_review_20261015/PUBLICATION_SCOPE_ADDENDUM.json')=='3085d04e04be3da49e69c905a29a396e75a93986645543b6cdba94e0199ca042','EXACT_MANDATORY_SOURCE_PUBLICATION_SCOPE_ADDENDUM');rebuilt=build(root);validate_scope(rebuilt['scope']);require(json_bytes(rebuilt)==raw(root/'summary/REPORT.json'),'EXACT_JSON_REPORT_REGENERATION');require(render_text(rebuilt).encode()==raw(root/'summary/REPORT.txt'),'EXACT_TEXT_REPORT_REGENERATION');require(render_csv(rebuilt['rows']).encode()==raw(root/'summary/REPORT.csv'),'EXACT_CSV_REPORT_REGENERATION')
 markers=[b'/' + b'workspace/',b'/' + b'tmp/',b'/' + b'home/agent/',b'/' + b'Users/',b'-----BEGIN '+b'PRIVATE KEY',b'github_'+b'pat_',b'gh'+b'p_',b'Bearer'+b' ']
 for rel in files:
  p=root/rel;require(p.suffix not in ('.npz','.npy','.log') and p.name not in PRIVATE_NAMES and not p.name.startswith('ADMISSION_'),'PUBLIC_ALLOWLIST_NO_ARRAYS_OR_PRIVATE_AUTHORITY')
  b=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes();require(not any(v in b for v in markers),'PRIVATE_RUNTIME_PREFIX_OR_SECRET_MARKER:'+rel)
 return dict(status='PASS_EXACT_NINE_FULL2025_COMPACT_SAVED_PACKET',cases=rows,files_rehashed=len(files),native40_events=sum(r['native40_events'] for r in rows),byte_exact_report_regeneration=True,full_MINUTE_arrays_included=False,all_minute_risk_regenerated=False,financial_accounts_constructed=0,financial_minutes_advanced=0,financial_replays=0,provider_iterations=0,publication_performed=False,source_publication_required_for_publication=require_publication)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));p.add_argument('--require-source-publication',action='store_true');p.add_argument('--archive');a=p.parse_args();print(json.dumps(verify_archive(a.archive) if a.archive else verify(a.root,require_publication=a.require_source_publication),sort_keys=True))

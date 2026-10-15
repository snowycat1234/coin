#!/usr/bin/env python3
"""Compact saved-evidence checks; zero accounts, historical advances or network."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,gzip,argparse
from saved_native_reconciliation import reconcile_saved_native
from saved_comparison import CELLS,ATT,REV,load,raw,require,build,render_text
CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
GO='b61e653438b3e68d4b5cdd70df5344c991e83231f7c2989924c17ee50b637dc6'
REVIEW='473911db756157dc960c6a90ae746f24e3262ad2bdd3e1e49b38ff23e6647f45'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_financial(a,r,p):
 got=reconcile_saved_native(a,r,expected_continuation_version='SEPARATE_CAUSAL_HELD_FORECAST_MID_PAID_REDUCTION_V1')
 require(got==p,'EXACT_NATIVE40_PROOF_INCLUDING_RAW100_RESIDUALS')
 require(p['checker_SHA256']==CHECKER and p['tolerance_or_epsilon_used'] is False,'FROZEN_NO_EPSILON_CHECKER')
 require(p['account_objects_constructed']==p['financial_clocks_advanced']==0,'SAVED_ONLY_BOUNDARY')
 e=r['economics'];require(e['actual_paid_market_flat'] is True and e['conditional_settled_flat'] is False and e['full_calendar'] is True,'ACTUAL_PAID_FLAT_TAXONOMY')
 require(a['settlement_journal']==a['transfer_journal']==[] and Decimal(a['unpaid_liability'])==0,'NO_SETTLEMENT_SUPPORT_OR_DEBT')
 require(all(Decimal(x['quantity'])==Decimal(x['isolated_balance'])==0 for x in a['positions'].values()),'EXACT_NATIVE_PAID_FLAT_POSITIONS')
 require(all(not x.get('liquidation_takeover') for x in a['trades']),'NO_CONDITIONAL_TAKEOVER')
 require(r['summary']['funding_rate_unit']=='UNCONFIRMED' and r['summary']['publication_certified'] is False,'PUBLICATION_QUALIFICATION')
 return got

def validate_scope(s):
 require(s['accounts_constructed']==s['financial_minutes_advanced']==s['provider_downloads']==0,'SAVED_ONLY_SCOPE')
 require(s['all_minute_risk_regenerated'] is False and s['risk_fields_are_exact_saved_independently_reviewed_evidence'] is True,'RISK_RECOVERY_SCOPE')
 require(s['four_annual_accounts_each_fresh_initial_10000'] is True and s['annual_accounts_compounded'] is False and s['continuous_two_year_CAGR'] is None,'ANNUAL_ACCOUNT_SCOPE')
 require(s['adaptive_seen_2023_2024_DEV_only'] is True and s['OOS_or_live_performance_claim'] is False,'DEV_SCOPE')
 require(s['native_exchange_or_funding_publication_certified'] is False and s['nominal_forecast_budget_is_not_exact_realized_risk_matching'] is True,'CERTIFICATION_SCOPE')
 require(s['changed_held_budget_management_is_whole_policy_effect'] is True and s['no_pure_statistic_normalization_effect_claim'] is True,'WHOLE_POLICY_EFFECT')
 require(s['monetary_authority']=='FROZEN_NATIVE40_CHRONOLOGICAL_EXACT_EVENT_STATE' and s['raw100_diagnostic_residuals_preserved_without_epsilon_or_repair'] is True,'MONETARY_AUTHORITY')

def verify(root):
 root=Path(root).resolve();m=load(root/'MANIFEST.json');files=m['files'];actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 require(actual==set(files)|{'MANIFEST.json'},'EXACT_PACKET_FILESET')
 for rel,pin in files.items():require(sha(root/rel)==pin['sha256'] and (root/rel).stat().st_size==pin['bytes'],'PACKET_MEMBER:'+rel)
 require(sha(root/'saved_native_reconciliation.py')==CHECKER,'FROZEN_PURE_NATIVE40_CHECKER')
 require(sha(root/REV/'FOUR_CELL_SAVED_TERMINAL_INDEPENDENT_REVIEW.json')==REVIEW,'FINAL_INDEPENDENT_FOUR_REVIEW')
 binding=load(root/REV/'FINAL_SAVED_FOUR_CELL_REVIEW_BINDING.json');require(sha(root/REV/'FINAL_SAVED_FOUR_CELL_REVIEW_BINDING.json')=='549d13e4f1ecc50cccacd01a7c715f20007445b2b698cd0da792d9ff9d473b9c','FINAL_BINDING_PIN')
 for rel,pin in binding['evidence'].items():require(hashlib.sha256(raw(root/rel)).hexdigest()==pin['SHA256'] and len(raw(root/rel))==pin['bytes'],'EXACT_FINAL_REVIEW_BINDING:'+rel)
 require(sha(root/REV/'ADDITIVE_SAVED_RISK_PHASE_MDD_AND_PAID_D_EXIT_SCOPE.json')=='ab78215174dd242ee8c2de88b591328461e6b37bd2d7871601058913262bd013','COVARIANCE_PHASE_AND_MDD_SCOPE_PIN')
 pins=load(root/'FULL_SAVED_OUTPUT_HASH_PINS.json')['files'];copies=load(root/'EXACT_COPY_SOURCE_MAP.json');gz=load(root/'LOSSLESS_GZIP_SOURCE_MAP.json')
 for dest,src in copies.items():require(sha(root/dest)==pins[src]['sha256'] and (root/dest).stat().st_size==pins[src]['bytes'],'EXACT_ORIGINAL:'+dest)
 for dest,ref in gz.items():
  b=raw(root/dest);require(hashlib.sha256(b).hexdigest()==ref['uncompressed_sha256']==pins[ref['source']]['sha256'] and len(b)==ref['uncompressed_bytes']==pins[ref['source']]['bytes'],'LOSSLESS_ORIGINAL:'+dest)
 omitted=load(root/'OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json');require(omitted['all_minute_risk_regeneration_self_contained'] is False and omitted['omitted_bytes_recoverable_from_hashes'] is False,'HONEST_OMITTED_ARRAY_SCOPE')
 require(len(omitted['MINUTE_outputs'])==8,'EXACT_FOUR_PLUS_CONTROL_MINUTE_PINS')
 source=load(root/'SOURCE_PUBLICATION_REFERENCE.json');require(source['status']=='FULL_REMOTE_BYTES_VERIFIED' and source['source_archive_sha256']=='898f923e091f6cf25c7b049d2654bbadc78b55024caa4886770c380ae56c4ea3' and source['every_remote_byte_matches_expected_local'] is True,'FULL_SOURCE_PUBLICATION_VERIFIED')
 require(source['results_publication_must_be_additive_child_of_source_commit'] is True,'SOURCE_BEFORE_RESULTS_CHAIN')
 admission=load(root/'EXTERNAL_ADMISSION_HASH_ONLY.json');require(admission['root_GO_sha256']==GO and admission['private_GO_bodies_included'] is False and admission['GO_or_launch_permission_granted_by_this_packet'] is False,'HASH_ONLY_ADMISSION')
 state=load(root/'RESEARCH_DISPOSITION.json');require(state['disposition']=='PRESERVED_RESEARCH_PROTOTYPE_NOT_ADOPTED' and state['new_policy_search_or_retuning_authorized'] is False,'NO_ADOPTION_NO_RETUNING')
 rows=[]
 for cid in CELLS:
  cell=cid+'_CAUSAL_FORECAST';d=root/ATT/cell;a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');r=load(d/'NATIVE_RESULT.json');p=load(d/'NATIVE40_RECONSTRUCTION_PROOF.json');checkpoint=load(d/'TERMINAL_CHECKPOINT.json');receipt=load(d/'CASE_RECEIPT.json');review=load(root/REV/(cell+'_REVIEW.json'))
  validate_financial(a,r,p)
  require(receipt['cell_id']==cell and receipt['root_GO_SHA256']==GO and receipt['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT','RECEIPT_SCOPE')
  require(receipt['completed_minutes']==receipt['required_minutes']==(525600 if receipt['year']==2023 else 527040),'FULL_CALENDAR')
  require(checkpoint['all_evidence_fsynced'] is True and checkpoint['restart_financial_snapshot_permission'] is False,'CHECKPOINT_SCOPE')
  for name,h in checkpoint['files'].items():require(pins[f'{ATT}/{cell}/{name}']['sha256']==h,'ORIGINAL_CHECKPOINT_PIN:'+name)
  require(checkpoint['files']['MINUTE.npz']==omitted['MINUTE_outputs'][cid+'_CAUSAL_FORECAST']['sha256'],'OMITTED_EXACT_MONITOR_MINUTE')
  require(p['exact_native40_NAV']==review['exact_financials']['NAV'],'INDEPENDENT_EXACT_NAV')
  rows.append({'cell_id':cell,'exact_NAV':p['exact_native40_NAV'],'native40_ledger_events':p['financial_ledger_rows_checked'],'paid_flat':True})
 rebuilt=build(root);validate_scope(rebuilt['scope']);require(rebuilt==load(root/'comparison/PAIRED_COMPARISON.json'),'BYTE_VALUE_EXACT_COMPARISON_REBUILD')
 require(render_text(rebuilt).encode()==raw(root/'comparison/REPORT.txt'),'BYTE_EXACT_TEXT_RERENDER')
 # No raw market/source/target array or private operational body may be published.
 markers=[b'/' + b'workspace/',b'/' + b'home/agent/',b'-----BEGIN ' + b'PRIVATE KEY',b'github_' + b'pat_',b'gh' + b'p_',b'Bearer' + b' ']
 for rel in files:
  p=root/rel;require(p.suffix not in ('.npz','.npy','.log') and p.name not in ('ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json'),'PUBLIC_ALLOWLIST')
  require(not any(marker in raw(p) for marker in markers),'PRIVATE_CONTENT:'+rel)
 return {'status':'PASS_FOUR_MONITOR_COMPACT_SAVED_PACKET','cases':rows,'files_rehashed':len(files),'exact_original_copies':len(copies),'lossless_gzip_originals':len(gz),'native40_events':sum(r['native40_ledger_events'] for r in rows),'comparison_byte_exact_rerender':True,'all_minute_risk_regenerated':False,'accounts_constructed':0,'financial_minutes_advanced':0,'publication_performed':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));args=p.parse_args();print(json.dumps(verify(args.root),sort_keys=True))

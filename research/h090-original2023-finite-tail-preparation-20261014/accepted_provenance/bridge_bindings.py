"""One-year metadata/GO gates. No historical array or account import here."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
FINITE=ROOT/'coin_h090_finite_native_20261014'
GRID=ROOT/'coin_bot_historical_driver_wallet_locator_20261014'
YEAR=2023;DAY=86400000000
CALENDAR=(1672531200000000,1704067200000000)
SOURCE_SHA='54f0c27ec160b99f02848ed9ec121a0f38d4a0672358608da51bafbc0a6e80b1'
ROOTS_SHA='982a532a87825b7f5258c8690bb41ae7c8327ba29c3d7114003a92f5fb017df5'
SOURCE_GO_SHA='17e973a99e1835ce2f2acdfa6c3e692a96a3276cc560455bcfc23b631ceb4c27'
GRID_SHA='44d66918dea6183553f54947a4a73b4fb77601065163b21e75b9aded4ddb91b4'
FINITE_SHA='6f915e88d0f29a1307706d25a206edac5751700687196b88c82643c45e9b2c96'
CONTROL_SHA='cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f'
FINITE_COMMIT='477920abb5af8679c12fb04971a15b2a37fe6adb'
CONTROL_COMMIT='0495a30385d5282f061c50892f8bb1e0550d6fe7'
ARMS=('CONTROL','FINITE')
CONTROL_BASELINE_LINEAGE_SHA='5df8a0a02e95b6d0b9ffdc3a9adfff6dbafa86938c58b2ddf0006b82370d04d4'
def require_original200_source_quality():
 from original200_quality import load_original200_proof
 return load_original200_proof()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def check(p,want):
 p=Path(p)
 if p.is_symlink() or not p.is_file() or sha(p)!=want:raise ValueError('EXACT_BOUND_METADATA_REQUIRED:'+p.name)
 return p
def metadata():
 require_control_baseline_lineage()
 check(HERE/'SOURCE_RECEIPT_2023.json',SOURCE_SHA)
 check(GRID/'PREPARATION_MANIFEST.json',GRID_SHA)
 check(FINITE/'SOURCE_FREEZE.json',FINITE_SHA)
 check(FINITE/'CONTROL_SOURCE_FREEZE.json',CONTROL_SHA)
 return dict(status='PREPARATION_ONLY_NO_ARRAY_OR_ACCOUNT',source_receipt=read(HERE/'SOURCE_RECEIPT_2023.json'),
  source_receipt_SHA256=SOURCE_SHA,roots_SHA256=ROOTS_SHA,source_GO_SHA256=SOURCE_GO_SHA,
  finite_commit=FINITE_COMMIT,control_commit=CONTROL_COMMIT,grid_preparation_SHA256=GRID_SHA,
  year=YEAR,arms=list(ARMS),cost='BASE27',funding_unit='RAW_AS_FRACTION',target_field='STATIC50_UNLAGGED',
  finite_CSH_fraction='8/9',same_source_cost_funding=True,historical_GO=False,
  original_public_target_checksum_files=['Y2023.npz','Y2025.npz'],checksum_only_extra_artifact='Y2025.npz',
  bounds=dict(CPU_seconds=600,wall_seconds=600,AS_bytes=4000000000,RSS_bytes=2000000000,output_bytes=250000000),
  source_quality_status='PINNED_ORIGINAL200_SOURCE_QUALITY_PROOF_REVIEWED_EXACT_CONSUMER_REQUIRED',
  original200_source_quality=require_original200_source_quality().identity(),
  historical_constructor_enabled=True,
  next_case='CONTROL2023_ONLY_AFTER_INDEPENDENT_CONSUMER_REVIEW_PUBLIC_RESTORATION_AND_FRESH_ROOT_GO',automatic_candidate_or_year_sweep=False)
def case_gate(args):
 # All checks are metadata-only and precede every source array/account import.
 metadata()
 if args is None or not hasattr(args,'year') or not hasattr(args,'arm'):raise ValueError('SEPARATE_ROOT_ONE_CASE_GO_REQUIRED')
 if args.year!=YEAR or args.arm not in ARMS:raise ValueError('SINGLE2023_EXACT_ARM_REQUIRED')
 if not args.case_go or not args.case_go_sha:raise ValueError('SEPARATE_ROOT_ONE_CASE_GO_REQUIRED')
 check(args.case_go,args.case_go_sha);g=read(args.case_go)
 expected=dict(schema='EXPLICIT_H090_ORIGINAL2023_ONE_CASE_GO_V1',parent_GO=True,year=YEAR,arm=args.arm,
  preparation_manifest_SHA256=sha(HERE/'PREPARATION_MANIFEST.json'),source_receipt_SHA256=SOURCE_SHA,
  source_GO_SHA256=SOURCE_GO_SHA,roots_SHA256=ROOTS_SHA,finite_source_SHA256=FINITE_SHA,
  CONTROL_source_SHA256=CONTROL_SHA,finite_public_commit=FINITE_COMMIT,CONTROL_public_commit=CONTROL_COMMIT,
  cost='BASE27',funding_unit='RAW_AS_FRACTION',target_field='STATIC50_UNLAGGED',rank_feature_lag_hours=0,
  initial_cash='10000',isolated_leverage=1,automatic_topup=False,
  original200_quality_proof_SHA256=require_original200_source_quality().identity()['proof_SHA256'],
  original200_quality_review_SHA256=require_original200_source_quality().identity()['review_SHA256'],
  original26_hash_only_target_artifacts=['Y2023.npz','Y2025.npz'],output_directory=str(Path(args.output).resolve()))
 if any(type(g.get(k)) is not type(v) or g.get(k)!=v for k,v in expected.items()):raise ValueError('EXACT_H090_ONE_CASE_GO_SCOPE_REQUIRED')
 if not args.review or not args.review_sha:raise ValueError('INDEPENDENT_BRIDGE_PREPARATION_REVIEW_REQUIRED')
 check(args.review,args.review_sha);r=read(args.review)
 if r.get('schema')!='INDEPENDENT_H090_ORIGINAL2023_BRIDGE_PREPARATION_REVIEW_V1' or r.get('status')!='PASS_REVIEWED_PROOF_CONSUMER_PREPARATION_ONLY' or r.get('preparation_manifest_SHA256')!=expected['preparation_manifest_SHA256'] or g.get('review_SHA256')!=args.review_sha:
  raise ValueError('EXACT_BRIDGE_REVIEW_BINDING_REQUIRED')
 check(args.source_receipt,SOURCE_SHA);check(args.source_go,SOURCE_GO_SHA);check(args.roots,ROOTS_SHA)
 if args.source_receipt_sha!=SOURCE_SHA or args.source_go_sha!=SOURCE_GO_SHA:raise ValueError('EXACT_SAVED_SOURCE_IDENTITIES_REQUIRED')
 if args.arm=='FINITE':
  evidence=getattr(args,'completed_control_evidence',None);evidence_sha=getattr(args,'completed_control_evidence_sha',None)
  if not evidence or not evidence_sha or g.get('completed_CONTROL_evidence_SHA256')!=evidence_sha:
   raise ValueError('CONTROL_FIRST_EXACT_COMPLETED_EVIDENCE_BINDING_REQUIRED')
  check(evidence,evidence_sha);record=read(evidence)
  if (record.get('schema')!='COMPLETE_FINAL_H090_NATIVE_OWNER_EVIDENCE_V1' or record.get('year')!=YEAR or record.get('arm')!='CONTROL'
      or not completed_control_preparation_matches(evidence,evidence_sha,record,expected['preparation_manifest_SHA256']) or record.get('source_receipt_SHA256')!=SOURCE_SHA
      or record.get('complete_calendar') is not True or record.get('completed_minutes')!=365*1440
      or record.get('required_minutes')!=365*1440 or record.get('status') not in ('PAID_FLAT','FULL_MARKED_WITH_RESIDUAL')):
   raise ValueError('FULL_YEAR_EXACT_SAME_BRIDGE_CONTROL_REQUIRED_PARTIAL_NOT_COMPARATOR')
 require_original200_source_quality()
 return g

def load_controller():
 from bindings import load_controller as original_grid_controller
 return original_grid_controller()


def require_control_baseline_lineage():
 # Fixed package metadata only. Caller-provided lineage is never accepted.
 check(HERE/'CONTROL_BASELINE_LINEAGE.json',CONTROL_BASELINE_LINEAGE_SHA)
 lineage=read(HERE/'CONTROL_BASELINE_LINEAGE.json')
 check(HERE/'ACCEPTED_B58_PREPARATION_MANIFEST.json',lineage['baseline_preparation_manifest_SHA256'])
 proof_path=check(HERE/lineage['CONTROL_reachable_equality_file'],lineage['CONTROL_reachable_equality_SHA256'])
 proof=read(proof_path)
 # A later preparation cannot reuse a stale equality report against changed
 # CONTROL bodies. Hash only frozen source/closure metadata, never arrays.
 for name,prefix in (('original_bridge.py','descendant_original_bridge'),('finite_preview_callers.py','descendant_finite_preview_callers')):
  path=check(HERE/name,proof[prefix+'_SHA256'])
  if path.stat().st_size!=proof[prefix+'_bytes']:raise ValueError('EXACT_CONTROL_LINEAGE_SOURCE_BYTES_REQUIRED')
 check(HERE/'EXECUTED_SOURCE_CLOSURE.json',proof['source_closure_byte_identical_SHA256'])
 for name,want in proof['unchanged_local_scientific_and_runtime_files'].items():
  path=check(HERE/name,want['SHA256'])
  if path.stat().st_size!=want['bytes']:raise ValueError('EXACT_CONTROL_LINEAGE_SOURCE_BYTES_REQUIRED')
 for name,want in proof['unchanged_closure_project_python_files'].items():
  path=check(ROOT/name,want['SHA256'])
  if path.stat().st_size!=want['bytes']:raise ValueError('EXACT_CONTROL_LINEAGE_SOURCE_BYTES_REQUIRED')
 return lineage


def exact_lineage_fields(record,expected):
 return all(type(record.get(k)) is type(v) and record.get(k)==v for k,v in expected.items())


def completed_control_preparation_matches(evidence,evidence_sha,record,current_preparation_sha):
 # Preserve the original exact same-preparation branch. The only mismatch
 # exception is this one immutable, complete, known b58 CONTROL baseline.
 if record.get('preparation_manifest_SHA256')==current_preparation_sha:return True
 lineage=require_control_baseline_lineage();pins=lineage['baseline_metadata']
 if (evidence_sha!=pins['EVIDENCE_MANIFEST.json']['SHA256']
     or record.get('preparation_manifest_SHA256')!=lineage['baseline_preparation_manifest_SHA256']):
  raise ValueError('EXACT_PINNED_CONTROL_BASELINE_LINEAGE_REQUIRED')
 path=check(evidence,pins['EVIDENCE_MANIFEST.json']['SHA256'])
 if path.stat().st_size!=pins['EVIDENCE_MANIFEST.json']['bytes'] or not exact_lineage_fields(record,lineage['required_evidence_fields']):
  raise ValueError('EXACT_COMPLETE_B58_CONTROL_BASELINE_REQUIRED')
 files=record.get('files')
 if type(files) is not dict:raise ValueError('EXACT_CONTROL_BASELINE_METADATA_LINKS_REQUIRED')
 metadata={}
 for name in ('BINDING.json','SUMMARY.json'):
  want=pins[name]
  if files.get(name)!=want:raise ValueError('EXACT_CONTROL_BASELINE_METADATA_LINKS_REQUIRED')
  file=check(path.parent/name,want['SHA256'])
  if file.stat().st_size!=want['bytes']:raise ValueError('EXACT_CONTROL_BASELINE_METADATA_BYTES_REQUIRED')
  metadata[name]=read(file)
 binding=metadata['BINDING.json'];summary=metadata['SUMMARY.json']
 quality=binding.get('original200_source_quality')
 source_identity=summary.get('bridge_source_identity')
 summary_quality=source_identity.get('original200_source_quality') if type(source_identity) is dict else None
 if (not exact_lineage_fields(binding,lineage['required_binding_fields'])
     or type(quality) is not dict or not exact_lineage_fields(quality,lineage['required_quality_fields'])
     or not exact_lineage_fields(summary,lineage['required_summary_fields'])
     or type(summary_quality) is not dict or not exact_lineage_fields(summary_quality,lineage['required_quality_fields'])
     or source_identity.get('source_receipt_SHA256')!=SOURCE_SHA
     or summary.get('cost_scenario',{}).get('id')!='BASE27'
     or summary.get('unit_scenario')!={'id':'RAW_AS_FRACTION','scale':1.0}):
  raise ValueError('EXACT_CONTROL_BASELINE_SOURCE_PROOF_COST_CALENDAR_REQUIRED')
 return True

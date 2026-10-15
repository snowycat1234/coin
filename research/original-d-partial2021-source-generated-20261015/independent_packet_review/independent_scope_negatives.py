"""Independent metadata-only rejection tests. No source callbacks or financial work.

Arguments: extracted packet root, new receipt path. Runs on one assigned CPU via
an external taskset command. Tests use copied JSON metadata, never market bytes.
"""
import os,sys,json,unittest,ast
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from contextlib import ExitStack
from unittest.mock import patch,Mock
root=Path(sys.argv[1]).resolve(); destination=Path(sys.argv[2]);new=root/'traditional_D_partial2021_20261015'
assert len(os.sched_getaffinity(0))==1
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
 assert os.environ[key]=='1'
sys.dont_write_bytecode=True
for directory in (new,root/'traditional_three_tier_freeze_20261015',root/'bounded_native_continuation_guard50_exit_expansion_20261015'):sys.path.insert(0,str(directory))
import partial_entry as e
import partial_d as d
import run_partial as r
prepraw=(new/'source_preparation_final/PREPARATION.json').read_bytes();prep=json.loads(prepraw)
reviewraw=(root/'traditional_D_partial2021_independent_review_20261015/INDEPENDENT_ORIGINAL_D_PARTIAL2021_REVIEW.json').read_bytes();review=json.loads(reviewraw)
template=(new/'ROOT_GO_TEMPLATE_UNAPPROVED.json').read_bytes()
metadata={name:(new/'source_targets_attempt002'/name).read_bytes() for name in ('DAILY_SOURCE_PROJECTION.json','EXACT_EXECUTION_EQUALITY.json','MINUTE_MARK_PROVENANCE.json')}
raw=e._canonical; checks=[];observed_body_opens=[]
def audit(event,args):
 if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if root not in p.parents:return
 if p.suffix.lower() in ('.npz','.npy','.parquet','.csv','.zip') or p.name in ('RAW_FUNDING_EVENTS.json','EVENTS.json') or any(x in ('annual_go','annual_go_2024','EXECUTION_CLAIMS') for x in p.parts) or p.name.startswith('ROOT_GO_APPROVED'):
  observed_body_opens.append(p.relative_to(root).as_posix());raise AssertionError('PROHIBITED_SOURCE_AUTHORITY_OR_CLAIM_BODY')
sys.addaudithook(audit)
blocked=[(e,'make_case'),(e.CaseExecutionScope,'__post_init__'),(e,'validate_case_inputs'),(e.s,'project'),(e.s.CapturedMinuteProvider,'__call__'),
 (d,'construct_case'),(d.ExpansionAccount,'__init__'),(d.D,'construct_case'),(d.D.Guard50ExitAccount,'__init__'),
 (d.V2,'construct_case'),(d.V2.ContinuationAccount,'__init__'),(d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),
 (e.s.g,'make_account'),(r,'case'),(r,'controller'),(r,'run_pool'),(r,'claim_launch'),(r,'save'),(r,'write_bytes')]
class RejectionTests(unittest.TestCase):
 def test_original_code_identity_closes_without_old_authority_bodies(self):
  self.assertEqual(e.code_identity(),prep['code_identity'])
  self.assertEqual(e.preserved_evidence_identity(),prep['preserved_evidence_pins'])
  tree=ast.parse((new/'partial_entry.py').read_text())
  identities=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('code_identity','preserved_evidence_identity')]
  self.assertEqual(len(identities),2)
  for n in identities:self.assertNotIn('annual_go',ast.unparse(n))
  self.assertFalse(any(root.glob('**/annual_go*')))
  checks.append('EXACT_CODE_IDENTITY_WITH_NO_OLD_AUTHORITY_BODIES')
 def test_policy_preparation_negative_mutations_metadata_only(self):
  mutations=[]
  for k in ('preserved_old_root_GO_is_new_authority','performance_selection_allowed','other_years_or_2025_authorized','locked_or_holdout_consumed','historical_admission','outcomes_inspected','annual_returns_computed','original_interpolated_mark_execution_admitted'):
   mutations.append((k,lambda p,k=k:p.__setitem__(k,True)))
  for k in ('accounts_created','accounts_advanced','historical_market_minutes_advanced','financial_runs','provider_iterations','historical_scopes_created','process_launches','canonical_claims_created','real_GO_written','publication_actions','old_private_GO_bodies_read'):
   mutations.append((k,lambda p,k=k:p.__setitem__(k,1)))
  for k in ('annualization_allowed','wallet_compounding_allowed','publication_authorized','old_GO_is_new_authority','old_GO_private_runtime_bodies_required','automatic_retry_authorized','halted_snapshot_resume_authorized','funding_units'):
   mutations.append(('policy.'+k,lambda p,k=k:p['policy'].__setitem__(k,True)))
  mutations.extend([
   ('years.extra',lambda p:p['years'].__setitem__('2025',deepcopy(p['years']['2021']))),
   ('years.calendar',lambda p:p['years']['2021'].__setitem__('calendar',[e.s.FULL_START,e.s.END])),
   ('years.decisions',lambda p:p['years']['2021'].__setitem__('days',365)),
   ('years.minutes',lambda p:p['years']['2021'].__setitem__('required_minutes',525600)),
   ('cells.drop',lambda p:p['cells'].pop(e.tranche_cells()[0])),
   ('cells.order',lambda p:p['ordered_cells'].reverse()),
   ('bool_as_resource_number',lambda p:p['resource_limits'].__setitem__('maximum_live_workers',True)),
   ('bad_source_pin',lambda p:p['years']['2021']['source_files'][e.s.DAILY_MEMBER].__setitem__('SHA256','0'*64))])
  for label,mutate in mutations:
   p=deepcopy(prep);mutate(p)
   with self.subTest(label=label),self.assertRaises(ValueError):e._validate_preparation(raw(p))
   checks.append('PREPARATION_REJECT:'+label)
 def test_review_negative_mutations_no_scope(self):
  # The minimal second JSON object only supplies a matching review digest for
  # this isolated validator. It is not a GO and never enters admission.
  mutations=[(flag,lambda v,k=flag:v.__setitem__(k,False)) for flag in e.REVIEW_FLAGS]
  mutations.extend([(k,lambda v,k=k:v.__setitem__(k,True)) for k in ('preserved_old_root_GO_is_new_authority','old_private_GO_bodies_required','annualization_allowed','wallet_compounding_allowed','publication_authorized','other_years_or_2025_authorized','locked_or_holdout_consumed')])
  mutations.extend([(k,lambda v,k=k:v.__setitem__(k,1)) for k in ('actual_2021_accounts_constructed','actual_2021_financial_runs','historical_market_minutes_advanced','publication_actions','locked_source_reads')])
  for label,mutate in mutations:
   v=deepcopy(review);mutate(v);b=raw(v);h=e._sha(b)
   with self.subTest(label=label),self.assertRaises(ValueError):e._validate_independent_review(prepraw,prep,b,h,raw(dict(independent_review_SHA256=h)))
   checks.append('REVIEW_REJECT:'+label)
  for label,b,h in [('missing',None,None),('wrong_digest',reviewraw,'0'*64),('old_hash',reviewraw,next(iter(e.OLD_EVIDENCE_HASHES.values())))]:
   with self.subTest(label=label),self.assertRaises(ValueError):e._validate_independent_review(prepraw,prep,b,h,raw({}))
   checks.append('REVIEW_REJECT:'+label)
 def test_invalid_template_fails_all_nine_cells_without_actual_callbacks(self):
  self.assertEqual(json.loads(template)['action'],'INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION')
  for cell in e.tranche_cells():
   with self.subTest(cell=cell),self.assertRaises(ValueError):e.validate_root_go(prepraw,template,e._sha(template),cell_id=cell)
   checks.append('INVALID_TEMPLATE_REJECT:'+cell)
 def test_missing_target_source_not_hash_recoverable(self):
  for name in ('TARGETS.npz','TARGET_PROOFS.json'):
   self.assertFalse((new/'source_targets_attempt002'/name).exists());self.assertFalse((new/'source_preparation_final/2021'/name).exists())
  self.assertFalse((root/'native_2021_source_restore_20261015'/e.s.DAILY_MEMBER).exists())
  self.assertFalse(observed_body_opens)
  checks.append('OMITTED_MARKET_AND_TARGET_BODIES_CONFIRMED_ABSENT')
 def test_duplicate_key_and_nonfinite_metadata_rejected(self):
  for b in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}',b'[]',b'null'):
   with self.assertRaises(ValueError):e._object(b,'REJECT')
  checks.append('DUPLICATE_NONFINITE_NONOBJECT_JSON_REJECTED')
with ExitStack() as stack:
 mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('FORBIDDEN_ACTUAL_BOUNDARY'))) for obj,name in blocked]
 stack.enter_context(patch.object(e,'_artifacts',return_value=metadata))
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RejectionTests))
 for mock in mocks:mock.assert_not_called()
 assert not observed_body_opens
 record=dict(schema='INDEPENDENT_PARTIAL2021_PACKET_METADATA_REJECTION_RECEIPT_V1',status='PASS' if result.wasSuccessful() else 'FAIL',
  tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),checks=checks,check_count=len(checks),
  metadata_only_artifact_seam=True,actual_source_metadata_positive_callbacks_run=False,real_GO_written=0,actual_source_bodies_opened=0,
  actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,actual_2021_market_minutes_advanced=0,actual_provider_iterations=0,
  live_claims_created=0,child_processes_launched=0,publication_actions=0,scope_instances_created=0,
  blocked_boundary_counts=[dict(boundary=getattr(obj,'__name__',type(obj).__name__)+'.'+name,calls=mock.call_count) for (obj,name),mock in zip(blocked,mocks)],
  CPU_affinity=sorted(os.sched_getaffinity(0)),all_current_TID_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},
  source_script_SHA256=sha256(Path(__file__).read_bytes()).hexdigest())
 with destination.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:record[k] for k in ('status','tests_run','check_count','failures','errors')}))
assert result.wasSuccessful()

"""Portable SOURCE-negative and generated-only verification; no historical authority.

Run in a fresh extracted copy, with installed NumPy 2.3.5 and Polars 1.44.2.
The exact archived independent generated suite is loaded with an explicit CPU-only
remap from its historical CPU4 to the caller's assigned CPU. Its bytes stay exact.
"""
import argparse,os,json,sys,time,resource,unittest,runpy
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from contextlib import ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
NEW=ROOT/'traditional_D_partial2021_20261015'
SOURCE=ROOT/'native_2021_source_restore_20261015'
parser=argparse.ArgumentParser();parser.add_argument('--cpu',required=True,type=int);parser.add_argument('--output',required=True)
args=parser.parse_args()
manifest_path=ROOT/'FILE_MANIFEST.json'
assert manifest_path.is_file(),'EXACT_PACKET_FILE_MANIFEST_REQUIRED'
manifest=json.loads(manifest_path.read_bytes())
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
assert actual==set(manifest['files'])|{'FILE_MANIFEST.json'},'UNEXPECTED_OR_MISSING_PACKET_MEMBER'
for name,pin in manifest['files'].items():
 path=ROOT/name;assert not path.is_symlink()
 raw=path.read_bytes();assert len(raw)==pin['bytes'] and sha256(raw).hexdigest()==pin['SHA256'],name
assert args.cpu in os.sched_getaffinity(0),'ASSIGNED_CPU_NOT_ALLOWED'
os.sched_setaffinity(0,{args.cpu})
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
os.environ['PARTIAL2021_TEST_CPUS']=str(args.cpu);os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
for p in (NEW,ROOT/'traditional_three_tier_freeze_20261015',ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'):sys.path.insert(0,str(p))
old_authority_attempts=[];actual_source_body_attempts=[]
def audit(event,values):
 if event!='open' or not values or not isinstance(values[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(values[0])).resolve()
 if ROOT not in p.parents:return
 if SOURCE in p.parents and p.suffix.lower() in ('.npz','.npy','.parquet','.zip','.csv'):
  actual_source_body_attempts.append(p.relative_to(ROOT).as_posix());raise AssertionError('ACTUAL_MARKET_BODY_FORBIDDEN')
 # Old authority directories are intentionally absent. Any attempted read is forbidden.
 allowed_json_roots=(NEW,SOURCE,ROOT/'traditional_three_tier_freeze_20261015',ROOT/'bounded_account_continuation_20261015',ROOT/'traditional_D_partial2021_independent_review_20261015')
 if (p.suffix.lower()=='.json' and p.parent!=ROOT and not any(q==p or q in p.parents for q in allowed_json_roots)) or any(x in ('annual_go','annual_go_2024') for x in p.parts) or p.name.startswith('ROOT_GO_APPROVED'):
  old_authority_attempts.append(p.relative_to(ROOT).as_posix());raise AssertionError('OLD_OR_ACTUAL_AUTHORITY_BODY_FORBIDDEN')
sys.addaudithook(audit)
begun=time.monotonic()
import numpy as np
import polars as pl
import partial_entry as e
import partial_d as d
import run_partial as r
from test_partial import PureMockRunnerTests,SyntheticDTests
metadata={name:(NEW/'source_targets_attempt002'/name).read_bytes() for name in ('DAILY_SOURCE_PROJECTION.json','EXACT_EXECUTION_EQUALITY.json','MINUTE_MARK_PROVENANCE.json')}
prepraw=(NEW/'source_preparation_final/PREPARATION.json').read_bytes();prep=json.loads(prepraw)
negative_checks=[];blocked_counts=[]
class PacketSourceNegativeTests(unittest.TestCase):
 def test_exact_source_generated_code_identity_and_nine_cells(self):
  self.assertEqual(prep['code_identity'],e.code_identity())
  self.assertEqual(len(e.tranche_cells()),9);self.assertEqual(e.frozen_manifest()['alias_mapping'],{})
  comparisons=json.loads(metadata['EXACT_EXECUTION_EQUALITY.json'])['STATIC50_H090_comparisons']
  self.assertEqual(len(comparisons),3);self.assertTrue(all(not x['entire_target_path_byte_exact'] for x in comparisons))
 def test_partial_calendar_terminal_and_unchanged_native_latency(self):
  self.assertEqual(prep['years']['2021']['days'],274);self.assertEqual(prep['years']['2021']['required_minutes'],394560)
  side=json.loads(metadata['MINUTE_MARK_PROVENANCE.json'])
  self.assertEqual(side['terminal_signal_us'],e.s.END-61*e.s.MINUTE)
  self.assertEqual(side['terminal_eligible_open_range'],[e.s.END-60*e.s.MINUTE,e.s.END-e.s.MINUTE])
  self.assertEqual(side['latest_native_terminal_fill_us'],e.s.END-e.s.MINUTE+1)
  self.assertFalse(prep['policy']['annualization_allowed']);self.assertEqual(prep['policy']['initial_shared_wallet_USDT'],'10000')
 def test_actual_source_and_target_gates_explicitly_unavailable(self):
  self.assertFalse((SOURCE/e.s.DAILY_MEMBER).exists())
  self.assertFalse((NEW/'source_targets_attempt002/TARGETS.npz').exists())
  with self.assertRaisesRegex(ValueError,'ORDINARY_EXACT_SOURCE_FILE_REQUIRED'):e.s.project()
  with self.assertRaisesRegex(ValueError,'ORDINARY_EXACT_SOURCE_FILE_REQUIRED'):e._artifacts()
  self.assertFalse(any(NEW.glob('EXECUTION_CLAIMS/*/*.json')))
 def test_invalid_template_rejected_under_explicit_metadata_only_seam(self):
  # Only three copied JSON metadata bodies are supplied. This is not a complete
  # source gate, and cannot construct actual source inputs, a scope or account.
  with patch.object(e,'_artifacts',return_value=metadata):
   self.assertEqual(e._validate_preparation(prepraw),prep)
   invalid=(NEW/'ROOT_GO_TEMPLATE_UNAPPROVED.json').read_bytes()
   with self.assertRaises(ValueError):e.validate_root_go(prepraw,invalid,e._sha(invalid),cell_id=e.tranche_cells()[0])
   self.assertEqual(json.loads(invalid)['action'],'INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION')
 def test_preparation_metadata_negative_mutations_no_actual_callbacks(self):
  tests=[('annualization',lambda p:p['policy'].__setitem__('annualization_allowed',True)),
   ('calendar',lambda p:p['years']['2021'].__setitem__('calendar',[e.s.FULL_START,e.s.END])),
   ('warmup',lambda p:p['years']['2021']['original200_quality'].__setitem__('warmup_only_before',e.s.FULL_START)),
   ('quality',lambda p:p['years']['2021']['original200_quality'].__setitem__('imputed',True)),
   ('old_authority',lambda p:p.__setitem__('preserved_old_root_GO_is_new_authority',True)),
   ('source_hash',lambda p:p['years']['2021']['source_files'][e.s.DAILY_MEMBER].__setitem__('SHA256','0'*64)),
   ('cell_tier',lambda p:p['cells'][e.tranche_cells()[0]]['descriptor'].__setitem__('tier','HIGH')),
   ('target_hash',lambda p:p['cells'][e.tranche_cells()[0]].__setitem__('selected_target_raw_SHA256','0'*64)),
   ('resource_bool',lambda p:p['resource_limits'].__setitem__('maximum_live_workers',True))]
  targets=[(d,'construct_case'),(d.ExpansionAccount,'__init__'),(d.D,'construct_case'),(d.D.Guard50ExitAccount,'__init__'),
   (d.V2,'construct_case'),(d.V2.ContinuationAccount,'__init__'),(d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),
   (e.s.g,'make_account'),(e.s.CapturedMinuteProvider,'__call__'),(e.CaseExecutionScope,'__post_init__'),
   (e,'make_case'),(e.s,'project'),(r,'case'),(r,'controller'),(r,'claim_launch')]
  with ExitStack() as stack:
   mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('PROHIBITED_ACTUAL_BOUNDARY'))) for obj,name in targets]
   stack.enter_context(patch.object(e,'_artifacts',return_value=metadata))
   for label,change in tests:
    p=deepcopy(prep);change(p)
    with self.subTest(label=label),self.assertRaises(ValueError):e._validate_preparation(e._canonical(p))
    negative_checks.append(label)
   for (obj,name),mock in zip(targets,mocks):mock.assert_not_called();blocked_counts.append(dict(boundary=obj.__name__+'.'+name,calls=mock.call_count))
 def test_old_GO_metadata_hashes_never_runtime_authority(self):
  self.assertEqual(e.preserved_evidence_identity(),prep['preserved_evidence_pins'])
  self.assertFalse(prep['preserved_old_root_GO_is_new_authority'])
  self.assertFalse(prep['policy']['old_GO_private_runtime_bodies_required'])
  self.assertEqual(prep['old_private_GO_bodies_read'],0)
  self.assertEqual(old_authority_attempts,[])

suite=unittest.TestSuite()
for name in ('test_generated_d','test_generated_native40','test_generated_runner'):suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
for cls in (PureMockRunnerTests,SyntheticDTests,PacketSourceNegativeTests):suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
# Read exact archived reviewer source; remap only its process affinity request
# during module loading. No bound source or archived receipt is rewritten.
original_affinity=os.sched_setaffinity
remaps=[]
def assigned_affinity(pid,mask):
 assert pid==0 and set(mask)=={4},'UNEXPECTED_REVIEW_AFFINITY_REQUEST'
 remaps.append(dict(original_CPU=4,assigned_CPU=args.cpu));return original_affinity(pid,{args.cpu})
with patch.object(os,'sched_setaffinity',assigned_affinity):
 independent=runpy.run_path(str(ROOT/'traditional_D_partial2021_independent_review_20261015/review_generated_final.py'),run_name='portable_independent_generated')
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(independent['GeneratedReview']))
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert not old_authority_attempts and not actual_source_body_attempts
report=dict(schema='PUBLIC_PACKET_COLD_SOURCE_NEGATIVE_GENERATED_RECEIPT_V1',status='PASS' if result.wasSuccessful() else 'FAIL',
 tests_run=result.testsRun,tests_passed=result.testsRun-len(result.skipped)-len(result.errors)-len(result.failures),
 skipped=[dict(test=str(test),reason=reason) for test,reason in result.skipped],failures=len(result.failures),errors=len(result.errors),
 metadata_negative_checks=negative_checks,source_negative_boundary_counts=blocked_counts,actual_source_gate_available=False,
 actual_source_metadata_positive_tests_repeated=False,full_source_or_historical_resource_certification=False,
 original_independent_review_CPU_only_runtime_remap=remaps,original_review_source_rewritten=False,
 old_private_authority_body_open_attempts=old_authority_attempts,actual_market_body_open_attempts=actual_source_body_attempts,
 actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,actual_2021_market_minutes_advanced=0,
 actual_source_provider_iterations=0,real_GO_written=0,live_canonical_claims_created=0,
 generated_temporary_claim_process_and_synthetic_account_tests=True,numpy_version=np.__version__,polars_version=pl.__version__,
 numerical_thread_environment={k:os.environ[k] for k in r.THREAD_ENV},CPU_affinity=sorted(os.sched_getaffinity(0)),
 all_current_TID_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},
 wall_seconds=time.monotonic()-begun,CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
 maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 script_SHA256=sha256(Path(__file__).read_bytes()).hexdigest())
out=Path(args.output)
with out.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ('status','tests_run','tests_passed','failures','errors','wall_seconds','maximum_RSS_bytes')}))
sys.exit(0 if result.wasSuccessful() else 1)

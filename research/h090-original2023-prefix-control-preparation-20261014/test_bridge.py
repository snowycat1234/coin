"""Focused generated bridge tests; original finance is compared, never rewritten."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase,mock
import gzip,hashlib,json,os,resource,tempfile
import numpy as np
import bridge_bindings as B
from original_bridge import make_sim,OriginalProjectionRegistry,OriginalH090Control,OriginalFiniteCandidate
from native_control import H090NativeControl,DESCRIPTOR,S,DAY
from finite_candidate import FiniteNativeCandidate
from owner_ledger import BASE
from generated_fixtures import make_generated,new_h090,generated_original_csh,BASE27,UNIT,START
from finite_fixtures import make_candidate,demo_bundle
from export_evidence import run_calendar
import driver


def admitted(bundle,*,recipe=False):
 window,_,_,_,weights=bundle;days=(window['end']-window['start'])//DAY
 if recipe:clock,prices,original,cov=generated_original_csh(days);assert original.tobytes()==weights.tobytes()
 else:
  clock=np.arange(0,window['end']+DAY,DAY,dtype=np.int64);prices=np.full((len(clock),5),100.,dtype=np.float64)
  cov=np.zeros((days,5,5),dtype=np.float64)
 decisions=np.arange(window['start'],window['end'],DAY,dtype=np.int64)
 return dict(window=dict(window),decision_us=decisions,weights=weights.copy(),clock=clock,prices=prices,
  covariance=cov,source_ids=np.searchsorted(clock,decisions),original_daily_admission=np.ones(days,dtype=bool))

def complete(sim,bundle=None):
 while sim.stop is None and sim.cursor<sim.end:
  if bundle is None:sim.advance_day()
  else:
   index=(sim.cursor-START)//DAY;sim.advance_day(original_csh_weights=dict(zip(S,bundle[-1][index],strict=True)))
 return sim

class Bridge(TestCase):
 def test_fixed_metadata_receipt_and_recipes(self):
  metadata=B.metadata();self.assertFalse(metadata['historical_GO']);self.assertEqual(B.sha(B.HERE/'SOURCE_RECEIPT_2023.json'),B.SOURCE_SHA)
  self.assertEqual((DESCRIPTOR.gross_cap,DESCRIPTOR.asset_cap,DESCRIPTOR.annual_vol_target,DESCRIPTOR.isolated_leverage),(.90,.30,.15,1))
  self.assertEqual((DESCRIPTOR.maximum_actual_isolated_margin,DESCRIPTOR.increase_free_cash_floor),('8500','1000'))
  self.assertEqual(metadata['year'],2023);self.assertFalse(metadata['automatic_candidate_or_year_sweep'])

 def test_financial_and_atomic_methods_are_exact_inherited_objects(self):
  for name in ('execute_fill','schedule','attempt','funding_through','observe','risk_schedule','advance_day'):
   parent=H090NativeControl if name!='execute_fill' else None
   if parent:self.assertIs(getattr(OriginalH090Control,name),getattr(parent,name))
  for name in ('_atomic_owner_route_admission','_atomic_owner_admission','_admit_decision','attempt','_flush_account','_evaluate_program','result'):
   self.assertIs(getattr(OriginalFiniteCandidate,name),getattr(FiniteNativeCandidate,name))

 def test_control_and_finite_native_receipt_parity(self):
  # Three independent fixed cases, two arms each, exact old-vs-bridge native
  # account/fill/funding/owner parity. No accepted 86-test suite is repeated.
  cases=[demo_bundle(),make_generated(days=2,weights=[[.06,.08,.08,0,0],[0,.1,.1,0,0]]),make_generated(days=1,quote=0,weights=[.06,.08,.08,0,0])]
  for bundle in cases:
   for arm in B.ARMS:
    bridge=complete(make_sim(admitted(bundle),arm,generated=True))
    legacy=complete(new_h090(bundle,preloaded=False) if arm=='CONTROL' else make_candidate(bundle,preloaded=False),bundle)
    self.assertEqual(bridge.account.snapshot(),legacy.account.snapshot())
    self.assertEqual(bridge.account.trades,legacy.account.trades);self.assertEqual(bridge.funding_journal,legacy.funding_journal)
    self.assertEqual(bridge.result()['minute'].to_dicts(),legacy.result()['minute'].to_dicts())
    if arm=='FINITE':
     self.assertEqual(bridge.owners.snapshot(),legacy.owners.snapshot());self.assertEqual(bridge.program.completed_opening_orders,legacy.program.completed_opening_orders)
     self.assertEqual(bridge.program_budget.consumed_fee_funding_reserve,legacy.program_budget.consumed_fee_funding_reserve)
     self.assertEqual(bridge._program_order_authorizations,legacy._program_order_authorizations)

 def test_original_recipe_covariance_bit_identity_and_no_extra_lag(self):
  bundle=make_generated(days=2,original_recipe=True);data=admitted(bundle,recipe=True)
  registry=OriginalProjectionRegistry(data,generated=True)
  for index,t in enumerate(data['decision_us']):
   sim=make_sim(data,'CONTROL',generated=True);t=int(t)
   context=sim._prepare(t,dict(zip(S,data['weights'][index],strict=True)),registry.packets[t])
   self.assertTrue(context['ready']);self.assertEqual(context['covariance'].tobytes(),data['covariance'][index].tobytes())
   source=json.loads(registry.packets[t].source_bytes);self.assertEqual(source['daily_bars'][-1]['available_us'],t);self.assertEqual(source['daily_bars'][-1]['close_us'],t)
   self.assertEqual(source['clock_provenance'],'PINNED_ORIGINAL_CLOSE_AVAILABLE_US_NOT_NEW_PROVIDER_ARRIVAL_CERTIFICATION')

 def test_bad_clock_order_covariance_and_target_row_refused(self):
  bundle=demo_bundle()
  for field,change in [('source_ids',lambda a:a.astype(np.float64)),('clock',lambda a:a[::-1]),('prices',lambda a:np.zeros_like(a)),('weights',lambda a:np.full_like(a,np.nan))]:
   data=admitted(bundle);data[field]=change(data[field])
   with self.assertRaises((ValueError,IndexError)):OriginalProjectionRegistry(data,generated=True)
  data=admitted(bundle);sim=make_sim(data,'CONTROL',generated=True);t=int(data['decision_us'][0]);original=dict(zip(S,data['weights'][0],strict=True));original[S[0]]+=.001
  before=sim.account.snapshot()
  with self.assertRaisesRegex(ValueError,'EXACT_RECEIPT_BOUND_ORIGINAL_TARGET_ROW'):sim.advance_day(original_csh_weights=original)
  self.assertEqual(sim.account.snapshot(),before)
  data=admitted(bundle);data['covariance'][0,0,0]=1.;sim=make_sim(data,'CONTROL',generated=True)
  with self.assertRaisesRegex(ValueError,'COV365_BIT_MISMATCH'):sim.advance_day()

 def test_generated_cannot_relabel_real_or_annual_scope(self):
  data=admitted(demo_bundle());data['window'].pop('fixture_scope')
  with self.assertRaisesRegex(ValueError,'BOUNDED_GENERATED_SOURCE'):make_sim(data,'FINITE',generated=True)
  data=admitted(make_generated(days=3));data['window']['end']+=DAY
  with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_PROJECTION_SHAPE'):make_sim(data,'CONTROL',generated=True)
  with self.assertRaisesRegex(ValueError,'EXPLICIT_SOURCE_SCOPE'):OriginalProjectionRegistry(admitted(demo_bundle()),generated=1)

 def test_historical_constructor_gate_precedes_every_account(self):
  args=SimpleNamespace(year=2023,arm='CONTROL',case_go=None,case_go_sha=None)
  with mock.patch.object(np,'load',side_effect=AssertionError('ARRAY_PARSE_FORBIDDEN')):
   with self.assertRaisesRegex(ValueError,'SEPARATE_ROOT_ONE_CASE_GO_REQUIRED'):make_sim(admitted(demo_bundle()),'CONTROL',case_args=args)
  args.year=2024
  with self.assertRaisesRegex(ValueError,'SINGLE2023_EXACT_ARM'):B.case_gate(args)

 def test_registry_packets_and_approved_rows_are_immutable(self):
  data=admitted(demo_bundle());registry=OriginalProjectionRegistry(data,generated=True);t=int(data['decision_us'][0])
  with self.assertRaises(TypeError):registry.packets[t]=None
  with self.assertRaises(TypeError):registry.original_rows[t]=()
  with self.assertRaises(TypeError):registry.covariance_bytes[t]=b''
  packet=registry.packets[t];wrong=type(packet)(packet.source_bytes+b' ',packet.manifest_bytes,packet.approved_manifest_sha256)
  with self.assertRaisesRegex(ValueError,'EXACT_RECEIPT_BOUND_ORIGINAL_SOURCE_PACKET'):registry.check(wrong,t)

 def test_final_export_keeps_paid_or_marked_status_and_all_owner_money(self):
  with tempfile.TemporaryDirectory() as folder:
   sim=make_sim(admitted(demo_bundle()),'FINITE',generated=True)
   binding={'year':2023,'arm':'FINITE','generated':True,'preparation_manifest_SHA256':B.sha(B.HERE/'PREPARATION_MANIFEST.json'),'source_receipt_SHA256':None}
   out=Path(folder)/'evidence';receipt=run_calendar(sim,out,binding,__import__('time').monotonic()+60,'GENERATED_BRIDGE_PARITY_ONLY')
   manifest=json.loads((out/'EVIDENCE_MANIFEST.json').read_text());self.assertEqual(manifest['capital_accounts'],1);self.assertEqual(manifest['owner_cash_wallet_count'],0);self.assertFalse(manifest['restore_supported'])
   for name,r in manifest['files'].items():self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),r['SHA256'])
   with gzip.open(out/'NATIVE_FILLS.jsonl.gz','rt') as f:rows=[json.loads(line) for line in f]
   self.assertEqual(rows,sim.account.trades)
   with gzip.open(out/'OWNER_FILLS.jsonl.gz','rt') as f:rows=[json.loads(line) for line in f]
   self.assertEqual(rows,sim.result()['owner_fill_allocations'])
   with gzip.open(out/'OWNER_AND_POLICY_FINAL.json.gz','rt') as f:state=json.load(f)
   self.assertEqual(state['owner_reconciliation'],sim.owners.reconcile(sim.account.engine));self.assertEqual(state['program_order_authorizations'],sim._program_order_authorizations)
   self.assertIn(receipt['status'],('PAID_FLAT','FULL_MARKED_WITH_RESIDUAL','HALTED_MARKED'));self.assertTrue(manifest['complete_calendar'])

 def test_partial_resource_stop_is_not_paid_or_complete(self):
  with tempfile.TemporaryDirectory() as folder:
   sim=make_sim(admitted(demo_bundle()),'CONTROL',generated=True);out=Path(folder)/'partial'
   receipt=run_calendar(sim,out,{'year':2023,'arm':'CONTROL','generated':True},__import__('time').monotonic(),'GENERATED_RESOURCE_STOP_ONLY')
   summary=json.loads((out/'SUMMARY.json').read_text());self.assertEqual(receipt['status'],'PARTIAL_MARKED');self.assertFalse(summary['complete_calendar']);self.assertIsNone(summary['paid_NAV_decimal']);self.assertEqual(sim.rows_written,0)

 def test_finite_budget_and_no_second_wallet(self):
  sim=complete(make_sim(admitted(demo_bundle()),'FINITE',generated=True))
  self.assertEqual(str(sim.reservations.reservations.get(BASE,sim.reservations.retired_reservations.get(BASE))),'8000')
  self.assertEqual(sim.program_budget.plan.total_sleeve_investment,__import__('decimal').Decimal('1000'))
  self.assertFalse(sim.descriptor.automatic_topup);self.assertEqual(sim.account.config.initial_cash,__import__('decimal').Decimal('10000'))
  self.assertFalse(sim.owners.reconcile(sim.account.engine)['owner_cash_accounts'])

 def test_direct_worker_and_noncase_dispatch_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   args=SimpleNamespace(command='source-check')
   with self.assertRaisesRegex(ValueError,'ONE_CASE_ONLY'):driver.dispatch(args)
   args=SimpleNamespace(remaining_seconds='595')
   with self.assertRaisesRegex(ValueError,'ORIGINAL_BOUNDED_PARENT'):driver.bounded_worker_guard(args)

 def test_exact_metadata_file_hash_and_symlink_guards(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'generated.json';p.write_text('{}');B.check(p,B.sha(p))
   with self.assertRaisesRegex(ValueError,'EXACT_BOUND_METADATA'):B.check(p,'f'*64)
   link=Path(folder)/'link.json';link.symlink_to(p)
   with self.assertRaisesRegex(ValueError,'EXACT_BOUND_METADATA'):B.check(link,B.sha(p))

 def test_case_GO_types_year_arm_review_and_control_first(self):
  # Source bytes do not exist in a generated gate fixture. Only those two
  # immutable original locators are mocked; GO/review/evidence SHA checks are
  # genuine and no array/account routine is reached by this test.
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);roots=folder/'GENERATED_ROOTS.json';source_go=folder/'GENERATED_SOURCE_GO.json';roots.write_text('{}');source_go.write_text('{}')
   review=folder/'GENERATED_REVIEW.json';freeze=B.sha(B.HERE/'PREPARATION_MANIFEST.json')
   review.write_text(json.dumps(dict(schema='INDEPENDENT_H090_ORIGINAL2023_BRIDGE_PREPARATION_REVIEW_V1',status='PASS_REVIEWED_PROOF_CONSUMER_PREPARATION_ONLY',preparation_manifest_SHA256=freeze)))
   args=SimpleNamespace(year=2023,arm='CONTROL',case_go=folder/'GENERATED_CASE_GO.json',case_go_sha=None,output=folder/'fresh',review=review,review_sha=B.sha(review),source_receipt=B.HERE/'SOURCE_RECEIPT_2023.json',source_receipt_sha=B.SOURCE_SHA,source_go=source_go,source_go_sha=B.SOURCE_GO_SHA,roots=roots,completed_control_evidence=None,completed_control_evidence_sha=None)
   value=dict(schema='EXPLICIT_H090_ORIGINAL2023_ONE_CASE_GO_V1',parent_GO=True,year=2023,arm='CONTROL',preparation_manifest_SHA256=freeze,source_receipt_SHA256=B.SOURCE_SHA,source_GO_SHA256=B.SOURCE_GO_SHA,roots_SHA256=B.ROOTS_SHA,finite_source_SHA256=B.FINITE_SHA,CONTROL_source_SHA256=B.CONTROL_SHA,finite_public_commit=B.FINITE_COMMIT,CONTROL_public_commit=B.CONTROL_COMMIT,cost='BASE27',funding_unit='RAW_AS_FRACTION',target_field='STATIC50_UNLAGGED',rank_feature_lag_hours=0,initial_cash='10000',isolated_leverage=1,automatic_topup=False,original200_quality_proof_SHA256=B.require_original200_source_quality().identity()['proof_SHA256'],original200_quality_review_SHA256=B.require_original200_source_quality().identity()['review_SHA256'],original26_hash_only_target_artifacts=['Y2023.npz','Y2025.npz'],output_directory=str(args.output.resolve()),review_SHA256=args.review_sha)
   check=B.check
   def fixture_check(path,want):
    if Path(path) in (roots,source_go):return Path(path)
    return check(path,want)
   def set_go(row):args.case_go.write_text(json.dumps(row));args.case_go_sha=B.sha(args.case_go)
   with mock.patch.object(B,'check',side_effect=fixture_check),mock.patch.object(np,'load',side_effect=AssertionError('ARRAY_PARSE_FORBIDDEN')):
    set_go(value)
    self.assertEqual(B.case_gate(args)['arm'],args.arm)
    for key,wrong in [('parent_GO',1),('isolated_leverage',True),('automatic_topup',0),('year',2024),('arm','CASH'),('target_field','PRICE_ONLY_CSH'),('rank_feature_lag_hours',1),('cost','STRESS43'),('preparation_manifest_SHA256','f'*64),('review_SHA256','f'*64),('original200_quality_proof_SHA256','f'*64),('original200_quality_review_SHA256','f'*64)]:
     set_go({**value,key:wrong})
     with self.assertRaisesRegex(ValueError,'EXACT_H090|EXACT_BRIDGE_REVIEW'):B.case_gate(args)
    args.arm='FINITE';finite={**value,'arm':'FINITE'};set_go(finite)
    with self.assertRaisesRegex(ValueError,'CONTROL_FIRST'):B.case_gate(args)
    evidence=folder/'GENERATED_CONTROL_EVIDENCE.json';record=dict(schema='COMPLETE_FINAL_H090_NATIVE_OWNER_EVIDENCE_V1',year=2023,arm='CONTROL',preparation_manifest_SHA256=freeze,source_receipt_SHA256=B.SOURCE_SHA,complete_calendar=True,completed_minutes=365*1440,required_minutes=365*1440,status='PAID_FLAT')
    evidence.write_text(json.dumps(record));args.completed_control_evidence=evidence;args.completed_control_evidence_sha=B.sha(evidence);finite['completed_CONTROL_evidence_SHA256']=args.completed_control_evidence_sha;set_go(finite)
    self.assertEqual(B.case_gate(args)['arm'],args.arm)
    record.update(complete_calendar=False,completed_minutes=133*1440,status='PARTIAL_MARKED');evidence.write_text(json.dumps(record));args.completed_control_evidence_sha=B.sha(evidence);finite['completed_CONTROL_evidence_SHA256']=args.completed_control_evidence_sha;set_go(finite)
    with self.assertRaisesRegex(ValueError,'FULL_YEAR_EXACT_SAME_BRIDGE_CONTROL'):B.case_gate(args)

 def test_original_quality_block_before_projection_and_account(self):
  import native_control
  with mock.patch.object(B,'require_original200_source_quality',side_effect=ValueError('EXACT_ORIGINAL200_PROOF_FILE_REQUIRED')),mock.patch.object(np,'load',side_effect=AssertionError('ARRAY_PARSE_FORBIDDEN')),mock.patch.object(native_control.NATIVE,'__init__',side_effect=AssertionError('ACCOUNT_CONSTRUCTION_FORBIDDEN')):
   for arm in B.ARMS:
    with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):make_sim({},arm)
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):OriginalProjectionRegistry({})
   forged=OriginalProjectionRegistry.__new__(OriginalProjectionRegistry);forged.generated=False
   for constructor in (OriginalH090Control,OriginalFiniteCandidate):
    with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):constructor({},forged)

 def test_original_quality_block_before_worker_source_import(self):
  with mock.patch.object(driver,'bounded_worker_guard'),mock.patch.object(B,'require_original200_source_quality',side_effect=ValueError('EXACT_ORIGINAL200_PROOF_FILE_REQUIRED')),mock.patch.object(B,'case_gate',side_effect=AssertionError('QUALITY_GATE_MUST_BE_FIRST')),mock.patch.object(np,'load',side_effect=AssertionError('ARRAY_PARSE_FORBIDDEN')):
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):driver.worker(SimpleNamespace())
  self.assertIs(B.metadata()['historical_constructor_enabled'],True)

 def test_direct_constructor_rejects_other_window_before_account(self):
  data=admitted(demo_bundle());registry=OriginalProjectionRegistry(data,generated=True)
  for change in ({'end':data['window']['end']+DAY},{'start':0},{'market':{}},{'fixture_scope':None}):
   changed={**data['window'],**change}
   with self.assertRaisesRegex(ValueError,'EXACT_ADMITTED_WINDOW'):OriginalH090Control(changed,registry)
  changed=dict(data['window']);rows=changed['daily'].to_dicts();rows[0]['close']+=1;changed['daily']=__import__('native_control').PORT.native.pl.DataFrame(rows)
  with self.assertRaisesRegex(ValueError,'EXACT_CURRENT_AVAILABLE_DAILY_SOURCE_PRICE'):OriginalFiniteCandidate(changed,registry)

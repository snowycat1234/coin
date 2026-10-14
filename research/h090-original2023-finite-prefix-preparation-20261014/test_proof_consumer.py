"""Focused proof-consumer checks using reviewed audit output, never source inputs."""
from pathlib import Path
from unittest import TestCase,mock
import copy,gzip,hashlib,json,struct,tempfile
import numpy as np
import original200_quality as Q
import bridge_bindings as B
from original_bridge import make_sim,OriginalProjectionRegistry,OriginalH090Control,OriginalFiniteCandidate
from native_control import H090NativeControl
from finite_candidate import FiniteNativeCandidate

class ProofConsumer(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.proof=Q.load_original200_proof()
  cls.document=json.loads(gzip.decompress((Q.HERE/'ORIGINAL200_SOURCE_QUALITY_PROOF.json.gz').read_bytes()))
  cls.clock=np.arange(Q.START,Q.END+Q.DAY,Q.DAY,dtype=np.int64)
  cls.prices=np.asarray([[struct.unpack('<d',bytes.fromhex(cls.proof._rows[(int(t),s)]['close_float64_hex']))[0] for s in Q.SYMBOLS] for t in cls.clock],dtype=np.float64)
  cls.decisions=np.arange(*Q.CALENDAR,Q.DAY,dtype=np.int64);cls.ids=np.searchsorted(cls.clock,cls.decisions)
 def test_exact_carrier_raw_proof_review_and_all365_windows(self):
  identity=self.proof.validate_projection(self.decisions,self.clock,self.prices,self.ids)
  self.assertEqual(identity['proof_SHA256'],Q.PROOF_SHA);self.assertEqual(identity['review_SHA256'],Q.REVIEW_SHA)
  self.assertEqual(len(self.decisions),365);self.assertEqual(len(self.proof._rows),2820)
  for t,k in zip(self.decisions,self.ids):
   rows=[self.proof.packet_row(int(end),s,self.prices[j,col]) for j,end in enumerate(self.clock) if int(t)-199*Q.DAY<=int(end)<=int(t) for col,s in enumerate(Q.SYMBOLS)]
   self.assertEqual(len(rows),1000)
   for row in rows:
    self.assertIs(row['complete'],True);self.assertIs(row['actual_source'],True);self.assertIs(row['imputed'],False)
    self.assertEqual(row['source_quality_proof_SHA256'],Q.PROOF_SHA);self.assertEqual(row['source_quality_review_SHA256'],Q.REVIEW_SHA)
  self.assertFalse(identity['provider_arrival_certified']);self.assertFalse(identity['fresh_raw_CSV_verification'])
 def test_missing_mutated_and_symlinked_files_refused(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'proof';p.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_HASH'):Q._exact_file(p,Q.CARRIER_SHA)
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):Q._exact_file(p.with_name('missing'),Q.CARRIER_SHA)
   link=p.with_name('linked');link.symlink_to(p)
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):Q._exact_file(link,hashlib.sha256(b'changed').hexdigest())
 def test_raw_body_and_review_hash_binding_precede_document_flags(self):
  original=Q._exact_file
  with mock.patch.object(Q,'_exact_file',return_value=gzip.compress(b'{}',mtime=0)):
   with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_RAW_PROOF_HASH'):Q.load_original200_proof()
  def wrong_review(path,*args):
   if Path(path).name=='ORIGINAL200_SOURCE_QUALITY_REVIEW.json':return b'{}'
   return original(path,*args)
  with mock.patch.object(Q,'_exact_file',side_effect=wrong_review):
   with self.assertRaisesRegex(ValueError,'EXACT_INDEPENDENT_ORIGINAL200_REVIEW'):Q.load_original200_proof()
 def test_flag_types_coverage_clock_and_price_mismatches_refused(self):
  for change in ({'complete':False},{'actual_source':1},{'imputed':True},{'available_us':Q.START+Q.DAY},{'symbol':'BAD'},{'close_float64_hex':'0000000000000000'}):
   doc=copy.deepcopy(self.document);doc['bars'][0].update(change)
   with self.assertRaises(ValueError):Q._validate_document(doc)
  doc=copy.deepcopy(self.document);doc['bars'].pop()
  with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_UNION'):Q._validate_document(doc)
 def test_admitted_price_clock_ids_dtype_and_outside_union_refused(self):
  for field,changed in [('prices',np.nextafter(self.prices,np.inf)),('clock',self.clock+Q.DAY),('ids',self.ids+1),('decisions',self.decisions+Q.DAY),('ids',self.ids.astype(np.float64))]:
   values=dict(decisions=self.decisions,clock=self.clock,prices=self.prices,ids=self.ids);values[field]=changed
   with self.assertRaises(ValueError):self.proof.validate_projection(**values)
  for t,s,price in ((Q.START-Q.DAY,Q.SYMBOLS[0],1.),(Q.END+Q.DAY,Q.SYMBOLS[0],1.),(Q.START,'BAD',1.)):
   with self.assertRaisesRegex(ValueError,'OUTSIDE_EXACT_PROOF_UNION'):self.proof.packet_row(t,s,price)
  with self.assertRaisesRegex(ValueError,'PROOF_BIT_MISMATCH'):self.proof.packet_row(Q.START,Q.SYMBOLS[0],1.)
 def test_binding_and_proof_rows_are_immutable(self):
  with self.assertRaises(TypeError):self.proof._rows={}
  with self.assertRaises(TypeError):self.proof._rows[(Q.START,Q.SYMBOLS[0])]['actual_source']=False
  with self.assertRaises(TypeError):self.proof._rows[(Q.START,Q.SYMBOLS[0])]['quality_proof']['observed_minutes']=0
  with self.assertRaisesRegex(ValueError,'EXACT_REVIEWED_ORIGINAL200_PROOF_CONSTRUCTION'):Q.VerifiedOriginal200Proof({},None)
 def test_missing_quality_or_case_GO_rejects_before_arrays_or_accounts(self):
  import native_control
  with mock.patch.object(np,'load',side_effect=AssertionError('ARRAY_PARSE_FORBIDDEN')),mock.patch.object(native_control.NATIVE,'__init__',side_effect=AssertionError('ACCOUNT_CONSTRUCTION_FORBIDDEN')):
   for arm in B.ARMS:
    with self.assertRaisesRegex(ValueError,'SEPARATE_ROOT_ONE_CASE_GO_REQUIRED'):make_sim({},arm)
   with mock.patch.object(B,'require_original200_source_quality',side_effect=ValueError('EXACT_ORIGINAL200_PROOF_FILE_REQUIRED')):
    for arm in B.ARMS:
     with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):make_sim({},arm)
    with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'):OriginalProjectionRegistry({})
 def test_frozen_finance_and_source_closure_are_unchanged(self):
  self.assertEqual(B.sha(B.FINITE/'SOURCE_FREEZE.json'),B.FINITE_SHA);self.assertEqual(B.sha(B.FINITE/'CONTROL_SOURCE_FREEZE.json'),B.CONTROL_SHA)
  old=B.ROOT/'finite_original2023_bridge_author_review_20261014/predecessor_bf61_source_quality_disabled'
  if old.exists():self.assertEqual(B.sha(old/'PREPARATION_MANIFEST.json'),Q.PREDECESSOR_SHA)
  self.assertEqual(B.sha(B.HERE/'EXECUTED_SOURCE_CLOSURE.json'),'2ae447e241c6476877f16ed312e0d95e616a06ef66c9835eed739c7308730a6c')
  closure=B.read(B.HERE/'EXECUTED_SOURCE_CLOSURE.json')
  for mode in closure['modes'].values():
   for name,digest in mode['files_SHA256'].items():self.assertEqual(B.sha(B.ROOT/name),digest)
  for name in ('schedule','attempt','funding_through','observe','risk_schedule','advance_day'):
   self.assertIs(getattr(OriginalH090Control,name),getattr(H090NativeControl,name))
  for name in ('_atomic_owner_route_admission','_atomic_owner_admission','_admit_decision','attempt','_flush_account','_evaluate_program','result'):
   self.assertIs(getattr(OriginalFiniteCandidate,name),getattr(FiniteNativeCandidate,name))

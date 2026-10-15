"""Pure saved-evidence tests and genuine corruption rejection; no financial replay."""
from copy import deepcopy
from decimal import Decimal,localcontext
from pathlib import Path
from unittest.mock import patch
import os,sys,json,unittest,tempfile,shutil,socket,subprocess,zipfile,hashlib,warnings
from saved_report import *
from verify_packet import validate_financial,validate_identity,validate_source,validate_member_names,verify_archive,verify
ROOT=Path(os.environ.get('SAVED_PACKET_TEST_ROOT',str(Path(__file__).resolve().parent)))
class SavedEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  d=ROOT/ATT/CELLS[0];cls.a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');cls.r=load(d/'NATIVE_RESULT.json');cls.p=load(d/'NATIVE40_RECONSTRUCTION_PROOF.json');cls.receipt=load(d/'CASE_RECEIPT.json');cls.review=load(ROOT/REV/(CELLS[0]+'_REVIEW.json'))
 def rejected(self,a=None,r=None,p=None):
  with self.assertRaises((ValueError,KeyError,AssertionError)):validate_financial(a if a is not None else self.a,r if r is not None else self.r,p if p is not None else self.p)
 def test_exact_native40_positive(self):validate_financial(self.a,self.r,self.p)
 def test_genuine_terminal_cash_corruption_rejected(self):
  a=deepcopy(self.a);a['free_cash']='9999';self.rejected(a=a)
 def test_small_terminal_debt_corruption_rejected(self):
  a=deepcopy(self.a);a['unpaid_liability']='1e-40';self.rejected(a=a)
 def test_small_terminal_margin_corruption_rejected(self):
  a=deepcopy(self.a);a['positions']['BTCUSDT']['isolated_balance']='1e-40';self.rejected(a=a)
 def test_native_ledger_cash_state_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['free_cash_after']='9999';self.rejected(a=a)
 def test_native_ledger_debt_state_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['unpaid_liability_after']='1e-40';self.rejected(a=a)
 def test_native_ledger_margin_delta_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['isolated_delta']['BTCUSDT']='1e-40';self.rejected(a=a)
 def test_native_fee_digit_corruption_rejected(self):
  a=deepcopy(self.a)
  with localcontext() as c:c.prec=100;a['trades'][0]['decimal_strings']['fee_amount']=str(Decimal(a['trades'][0]['decimal_strings']['fee_amount'])+Decimal('1e-40'))
  self.rejected(a=a)
 def test_raw100_residual_forced_zero_rejected(self):
  p=deepcopy(self.p);p['raw_precision100_stored_delta_terminal_residuals']['isolated']['BTCUSDT']='0';self.rejected(p=p)
 def test_epsilon_permission_rejected(self):
  p=deepcopy(self.p);p['tolerance_or_epsilon_used']=True;self.rejected(p=p)
 def test_bool_integer_scope_confusion_rejected(self):
  p=deepcopy(self.p);p['account_objects_constructed']=False;self.rejected(p=p)
 def test_funding_ownership_corruption_rejected(self):
  a=deepcopy(self.a);a['funding'][0]['owned']=not a['funding'][0]['owned'];self.rejected(a=a)
 def test_illegal_D_transfer_rejected(self):
  a=deepcopy(self.a);a['transfer_journal']=[{'amount':'1'}];self.rejected(a=a)
 def test_wrong_case_identity_rejected(self):
  r=deepcopy(self.receipt);r['cell_id']=CELLS[1]
  with self.assertRaises(ValueError):validate_identity(r,self.a,self.r,self.review,CELLS[0])
 def test_typed_year_identity_rejected(self):
  r=deepcopy(self.receipt);r['year']=2022.0
  with self.assertRaises(ValueError):validate_identity(r,self.a,self.r,self.review,CELLS[0])
 def test_source_quality_upgrade_rejected(self):
  r=deepcopy(self.review);r['source27_impact_audit']['cells'][0]['actual_arrival_installation']='CERTIFIED'
  with self.assertRaises(ValueError):validate_identity(self.receipt,self.a,self.r,r,CELLS[0])
 def test_unknown_sensitivity_claim_rejected(self):
  r=deepcopy(self.review);r['source27_impact_audit']['terminal_and_return_sensitivity']='NEGLIGIBLE'
  with self.assertRaises(ValueError):validate_identity(self.receipt,self.a,self.r,r,CELLS[0])
 def test_both_covariance_phases_required(self):
  r=deepcopy(self.review);r['actual_held_exposure_and_both_covariance_phase_risk']['covariance_phases'].pop('CLOSE_WITH_SAMECLOCK_DAILY_DECISION')
  with self.assertRaises(ValueError):validate_identity(self.receipt,self.a,self.r,r,CELLS[0])
 def test_false_saved_scope_claims_rejected(self):
  for k,v in [('accounts_constructed',False),('MINUTE_arrays_opened',1),('annual_wallets_compounded',True),('continuous_CAGR','0.1'),('minute_risk_regenerated_by_compact_packet',True),('counterfactual_mark_sensitivity_identified',True),('actual_exchange_liquidation_or_no_liquidation_certified',True),('nominal_tier_is_not_exact_realized_risk_matching',False)]:
   s=dict(SCOPE);s[k]=v
   with self.assertRaises(ValueError,msg=k):validate_scope(s)
 def test_case_report_has_no_process_network_financial_import_or_array_read(self):
  import builtins
  orig=builtins.__import__;read=Path.read_bytes
  def guarded(name,*a,**kw):
   if any(n in name for n in ('full_entry','full_d','run_full','perpetual_account','native_runtime','numpy','polars','source_projection','full_source')):raise AssertionError('FORBIDDEN_FINANCIAL_OR_ARRAY_IMPORT')
   return orig(name,*a,**kw)
  def arrayguard(p,*a,**kw):
   if p.suffix in ('.npz','.npy'):raise AssertionError('FORBIDDEN_ARRAY_OPEN')
   return read(p,*a,**kw)
  with patch('builtins.__import__',side_effect=guarded),patch.object(Path,'read_bytes',arrayguard),patch.object(socket,'socket',side_effect=AssertionError('NO_NETWORK')),patch.object(subprocess,'Popen',side_effect=AssertionError('NO_CHILD_PROCESS')),patch.object(os,'system',side_effect=AssertionError('NO_SHELL')):
   got=row(ROOT,CELLS[0]);validate_financial(self.a,self.r,self.p);self.assertEqual(got['completed_minutes'],525600)
class FullPacket(unittest.TestCase):
 def test_full_exact_nine_packet(self):self.assertEqual(verify(ROOT)['status'],'PASS_EXACT_NINE_FULL2022_COMPACT_SAVED_PACKET')
 def test_pending_source_publication_is_not_verified(self):
  source=load(ROOT/'SOURCE_PUBLICATION_REFERENCE.json');validate_source(source)
  if source['status']=='BLOCKED_PENDING_VERIFIED_REMOTE_SOURCE_PUBLICATION':
   with self.assertRaisesRegex(ValueError,'VERIFIED_NEW2022_SOURCE_COMMIT_REQUIRED'):validate_source(source,True)
 def test_original_member_byte_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   cp=Path(td)/'candidate';shutil.copytree(ROOT,cp,ignore=shutil.ignore_patterns('__pycache__'));p=cp/ATT/CELLS[0]/'CASE_RECEIPT.json';p.write_bytes(p.read_bytes()+b' ')
   with self.assertRaisesRegex(ValueError,'EXACT_PACKET_MEMBER'):verify(cp)
 def test_lossless_gzip_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   cp=Path(td)/'candidate';shutil.copytree(ROOT,cp,ignore=shutil.ignore_patterns('__pycache__'));p=cp/ATT/CELLS[0]/'ACCOUNT_FINANCIAL_AUDIT.json.gz';b=bytearray(p.read_bytes());b[len(b)//2]^=1;p.write_bytes(b)
   with self.assertRaisesRegex(ValueError,'EXACT_PACKET_MEMBER'):verify(cp)
 def test_full_report_rebuild_has_no_network_process_financial_import_or_arrays(self):
  import builtins
  orig=builtins.__import__;read=Path.read_bytes
  def guarded(name,*a,**kw):
   if any(n in name for n in ('full_entry','full_d','run_full','perpetual_account','native_runtime','numpy','polars','source_projection','full_source')):raise AssertionError('FORBIDDEN_FINANCIAL_OR_ARRAY_IMPORT')
   return orig(name,*a,**kw)
  def arrayguard(p,*a,**kw):
   if p.suffix in ('.npz','.npy'):raise AssertionError('FORBIDDEN_ARRAY_OPEN')
   return read(p,*a,**kw)
  with patch('builtins.__import__',side_effect=guarded),patch.object(Path,'read_bytes',arrayguard),patch.object(socket,'socket',side_effect=AssertionError('NO_NETWORK')),patch.object(subprocess,'Popen',side_effect=AssertionError('NO_CHILD_PROCESS')):
   got=build(ROOT);self.assertEqual(json_bytes(got),raw(ROOT/'summary/REPORT.json'))
class ArchiveSafety(unittest.TestCase):
 def fixture(self,path,mutation=None):
  prefix=PACKET_NAME+'/';payload=b'exact saved proof bytes';files={'proof.txt':{'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}};manifest=json_bytes({'files':files})
  entries=[(prefix+'proof.txt',payload,0o100644),(prefix+'MANIFEST.json',manifest,0o100644)]
  if mutation=='missing':entries=entries[1:]
  elif mutation=='extra':entries.append((prefix+'extra.txt',b'extra',0o100644))
  elif mutation=='duplicate':entries.append(entries[0])
  elif mutation=='alias':entries.append((prefix+'a/../proof.txt',payload,0o100644))
  elif mutation=='double_slash':entries.append((prefix+'a//proof.txt',payload,0o100644))
  elif mutation=='symlink':entries[0]=(prefix+'proof.txt',b'target',0o120777)
  elif mutation=='duplicate_JSON':entries[1]=(prefix+'MANIFEST.json',b'{"files":{},"files":{}}',0o100644)
  with warnings.catch_warnings():
   warnings.simplefilter('ignore',UserWarning)
   with zipfile.ZipFile(path,'w') as z:
    for name,b,mode in entries:
     info=zipfile.ZipInfo(name,date_time=(2026,10,15,0,0,0));info.external_attr=mode<<16;info.compress_type=zipfile.ZIP_STORED;z.writestr(info,b)
 def check_rejected(self,mutation,pattern):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'candidate.zip';self.fixture(p,mutation)
   with self.assertRaisesRegex(ValueError,pattern):verify_archive(p)
 def test_exact_safe_archive_positive(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'candidate.zip';self.fixture(p);self.assertEqual(verify_archive(p)['status'],'PASS_EXACT_SAFE_COMPACT_ARCHIVE')
 def test_missing_archive_member_rejected(self):self.check_rejected('missing','MISSING_OR_EXTRA')
 def test_extra_archive_member_rejected(self):self.check_rejected('extra','MISSING_OR_EXTRA')
 def test_duplicate_archive_member_rejected(self):self.check_rejected('duplicate','DUPLICATE_ARCHIVE')
 def test_traversal_path_alias_rejected(self):self.check_rejected('alias','PATH_ALIAS_OR_TRAVERSAL')
 def test_double_slash_path_alias_rejected(self):self.check_rejected('double_slash','PATH_ALIAS_OR_TRAVERSAL')
 def test_symlink_archive_member_rejected(self):self.check_rejected('symlink','UNSAFE_NONREGULAR')
 def test_duplicate_manifest_JSON_key_rejected(self):self.check_rejected('duplicate_JSON','DUPLICATE_JSON_OBJECT_KEY')
 def test_duplicate_manifest_member_list_rejected(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE_ARCHIVE'):validate_member_names(['a','a'])
 def test_missing_manifest_member_rejected(self):
  with self.assertRaisesRegex(ValueError,'MISSING_OR_EXTRA'):validate_member_names(['a'],['a','b'])
 def test_extra_manifest_member_rejected(self):
  with self.assertRaisesRegex(ValueError,'MISSING_OR_EXTRA'):validate_member_names(['a','b'],['a'])
 def test_manifest_path_alias_rejected(self):
  for name in ('a//b','a/./b','a/../b','/a','a\\b'):
   with self.assertRaisesRegex(ValueError,'PATH_ALIAS_OR_TRAVERSAL|UNSAFE_MEMBER_PATH'):validate_member_names([name])
if __name__=='__main__':unittest.main(verbosity=2)

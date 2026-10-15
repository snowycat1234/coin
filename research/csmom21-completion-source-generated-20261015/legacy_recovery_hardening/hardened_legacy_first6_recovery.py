#!/usr/bin/env python3
"""Additive, externally trusted pre-import hardening for the immutable legacy ZIP."""
import argparse,hashlib,json,os,re,stat,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath
EXPECTED_ZIP_SHA256='1a7cd6f0bff059cb76053dd6a41b4e6c03e45291f1fb26fda1a3b8bb1f0afc3b'
EXPECTED_ROOT='legacy_intrinsic_D_FIRST6_compact_saved_results_public_recovery_20261015_v3'
MAX_ARCHIVE_BYTES=16*1024*1024
MAX_MEMBERS=512
MAX_MEMBER_BYTES=4*1024*1024
MAX_EXPANDED_BYTES=32*1024*1024

def require(condition,message):
 if not condition:raise ValueError(message)

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def validate_member_metadata(infos):
 require(0<len(infos)<=MAX_MEMBERS,'ZIP_MEMBER_COUNT_CAP_REQUIRED');names=set();total=0
 for info in infos:
  name=info.filename;p=PurePosixPath(name);mode=(info.external_attr>>16)&0o170000
  require(type(name) is str and name and '\\' not in name and '\x00' not in name and not p.is_absolute() and '..' not in p.parts and '.' not in p.parts and p.parts[0]==EXPECTED_ROOT and name==str(p),'UNSAFE_ZIP_MEMBER_REJECTED')
  require(name not in names,'DUPLICATE_ZIP_MEMBER_REJECTED');names.add(name)
  require(not info.is_dir() and mode in (0,stat.S_IFREG) and mode!=stat.S_IFLNK,'SYMLINK_OR_NONREGULAR_ZIP_MEMBER_REJECTED')
  require(not info.flag_bits&1 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ENCRYPTED_OR_UNSUPPORTED_ZIP_MEMBER_REJECTED')
  require(type(info.file_size) is int and 0<=info.file_size<=MAX_MEMBER_BYTES and type(info.compress_size) is int and 0<=info.compress_size<=MAX_ARCHIVE_BYTES,'ZIP_MEMBER_SIZE_CAP_REQUIRED')
  total+=info.file_size;require(total<=MAX_EXPANDED_BYTES,'ZIP_EXPANDED_SIZE_CAP_REQUIRED')
 return dict(members=len(names),expanded_bytes=total)

def run(archive,trusted,verify_saved=False):
 # Refuse optimized mode explicitly before any archive access or packet imports.
 require(sys.flags.optimize==0,'NORMAL_PYTHON_REQUIRED_OPTIMIZED_MODE_REFUSED_BEFORE_ARCHIVE_ACCESS')
 # All trust/safety checks are explicit exceptions, never assert.
 # Reject an absent/wrong supplied trust value before opening even the raw file.
 require(type(trusted) is str and re.fullmatch('[0-9a-f]{64}',trusted) is not None and trusted==EXPECTED_ZIP_SHA256,'EXTERNALLY_KNOWN_LEGACY_ZIP_SHA256_REQUIRED')
 archive=Path(archive).resolve();require(archive.is_file() and archive.stat().st_size<=MAX_ARCHIVE_BYTES,'TRUSTED_ARCHIVE_SIZE_CAP_REQUIRED')
 require(digest(archive)==trusted,'TRUSTED_OUTER_ZIP_SHA256_MISMATCH')
 require(not verify_saved or sys.flags.optimize==0,'EXISTING_SAVED_VERIFIER_SUPPORTED_WITH_NORMAL_PYTHON_ONLY')
 for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
 with tempfile.TemporaryDirectory(prefix='legacy_hardened_saved_') as td:
  target=Path(td)
  with zipfile.ZipFile(archive) as z:
   meta=validate_member_metadata(z.infolist())
   # No extraction or packet import occurs until all names/types/size caps pass.
   z.extractall(target)
   packet=target/EXPECTED_ROOT;require(packet.is_dir(),'EXPECTED_FRESH_PACKET_ROOT_REQUIRED')
   for info in z.infolist():
    p=target/info.filename;require(p.is_file() and not p.is_symlink() and p.stat().st_size==info.file_size and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(z.read(info)).digest(),'EXACT_FRESH_EXTRACTED_MEMBER_BYTES_REQUIRED')
  result=dict(schema='ADDITIVE_LEGACY_FIRST6_HARDENED_PREIMPORT_RECOVERY_V1',status='PASS_TRUSTED_HASH_AND_SAFE_FRESH_EXTRACTION',ZIP_SHA256=trusted,ZIP_bytes=archive.stat().st_size,**meta,mandatory_hash_checked_before_ZIP_parse_or_packet_import=True,safe_member_checks_complete_before_extraction=True,optimized_mode_refused_before_archive_access=True,python_optimization_level=sys.flags.optimize,saved_financial_verifier_invoked=verify_saved,original_results_archive_changed=False,new_financial_execution=False,source_or_provider_calls=0,network_calls=0)
  if verify_saved:
   # Optional saved-only reporting: use the unchanged verifier from the exact trusted ZIP.
   sys.dont_write_bytecode=True;sys.path.insert(0,str(packet))
   import verify_packet
   result['saved_verification']=verify_packet.verify_outer(packet,archive,trusted)
   result['status']='PASS_HARDENED_PREIMPORT_AND_UNCHANGED_SAVED_VERIFIER'
  return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive');p.add_argument('--trusted-zip-sha256',required=True);p.add_argument('--verify-saved',action='store_true',help='Optionally invoke the unchanged saved-only verifier, normal Python only.');p.add_argument('--receipt');a=p.parse_args();result=run(a.archive,a.trusted_zip_sha256,a.verify_saved)
 if a.receipt:Path(a.receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()

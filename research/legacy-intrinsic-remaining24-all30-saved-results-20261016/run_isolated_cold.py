#!/usr/bin/env python3
"""Externally trusted cold launcher: validate outer ZIP before loading packet code."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{6})
import argparse,hashlib,json,tempfile,zipfile,sys,socket,subprocess,fcntl,builtins,re
from pathlib import Path,PurePosixPath
def require(condition,message):
 if not condition:raise ValueError(message)
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--trusted-zip-sha256',required=True);p.add_argument('--receipt',required=True);a=p.parse_args()
archive=Path(a.archive).resolve();receipt_path=Path(a.receipt).resolve();require(type(a.trusted_zip_sha256) is str and re.fullmatch('[0-9a-f]{64}',a.trusted_zip_sha256) is not None,'EXTERNAL_TRUSTED_ZIP_SHA256_REQUIRED')
require(archive.is_file() and archive.stat().st_size<=128*1024*1024,'COLD_ARCHIVE_SIZE_CAP_REQUIRED')
h=hashlib.sha256(archive.read_bytes()).hexdigest();require(h==a.trusted_zip_sha256,'EXTERNAL_TRUSTED_ZIP_HASH_MISMATCH')
with tempfile.TemporaryDirectory(prefix='legacy24_saved_cold_') as td:
 root=Path(td)
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();require(0<len(names)<=2048 and len(names)==len(set(names)),'ZIP_MEMBER_COUNT_OR_DUPLICATE_REJECTED');expanded=0
  for info in z.infolist():
   path=PurePosixPath(info.filename);require(not path.is_absolute() and '..' not in path.parts and info.filename==str(path) and '\\' not in info.filename and not info.is_dir() and (info.external_attr>>16)&0o170000 in (0,0o100000),'UNSAFE_ZIP_MEMBER_REJECTED')
   expanded+=info.file_size;require(0<=info.file_size<=16*1024*1024 and expanded<=256*1024*1024 and not info.flag_bits&1 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ZIP_SIZE_TYPE_OR_ENCRYPTION_CAP_REQUIRED')
  z.extractall(root)
 dirs=[d for d in root.iterdir() if d.is_dir()];require(len(dirs)==1,'EXACTLY_ONE_PACKET_ROOT_REQUIRED');packet=dirs[0]
 sys.dont_write_bytecode=True;sys.path[:]=[str(packet)]+[s for s in sys.path if s and ('site-packages' not in s) and ('dist-packages' not in s) and (Path(s).is_absolute() and not Path(s).is_relative_to(Path.cwd()))]
 # Credential and inherited execution-lease environment is absent for cold reporting.
 keep={'PATH','LANG','LC_ALL','HOME','TMPDIR','PYTHONHASHSEED','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'}
 for name in list(os.environ):
  if name not in keep:del os.environ[name]
 attempts=[];file_reads=[]
 # Every generated mutation stays inside this one fresh extraction workspace.
 original_tempdir=tempfile.TemporaryDirectory
 def confined_tempdir(*args,**kwargs):kwargs['dir']=root;return original_tempdir(*args,**kwargs)
 tempfile.TemporaryDirectory=confined_tempdir
 allowed_code_roots=[Path(x).resolve() for x in sys.path[1:] if Path(x).is_dir()]
 def audit_read_guard(event,args):
  if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  path=Path(os.fsdecode(args[0])).resolve();mode=args[1] if len(args)>1 else 'r';flags=args[2] if len(args)>2 else 0
  writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)))
  allowed=(writing and path==receipt_path) or path.is_relative_to(root) or (not writing and (path==archive or any(path.is_relative_to(x) for x in allowed_code_roots)))
  if not allowed:attempts.append('outside_fresh_extraction_file_access');raise RuntimeError('COLD_FORBIDDEN:OUTSIDE_FRESH_EXTRACTION_FILE_ACCESS')
  if not writing:file_reads.append(str(path.relative_to(root)) if path.is_relative_to(root) else 'trusted_archive_or_standard_library')
 # open audit events omit dir_fd. Normalize fd-relative os.open calls first,
 # so standard-library rmtree cleanup is checked against its real directory.
 original_os_open=os.open
 def resolved_os_open(path,flags,mode=0o777,*,dir_fd=None):
  if dir_fd is not None and not os.path.isabs(path):
   parent=os.readlink('/proc/self/fd/'+str(dir_fd));path=os.path.join(parent,os.fsdecode(path));dir_fd=None
  return original_os_open(path,flags,mode,dir_fd=dir_fd)
 os.open=resolved_os_open
 sys.addaudithook(audit_read_guard)
 def blocked(label):
  def f(*args,**kwargs):attempts.append(label);raise RuntimeError('COLD_FORBIDDEN:'+label)
  return f
 for obj,names in ((socket,('create_connection','getaddrinfo')),(socket.socket,('connect','connect_ex')),(subprocess,('Popen','run','call','check_call','check_output')),(os,('system','fork','forkpty','posix_spawn','posix_spawnp','execv','execve','execvp','execvpe')),(fcntl,('flock',))):
  for name in names:
   if hasattr(obj,name):setattr(obj,name,blocked(getattr(obj,'__name__',str(obj))+'.'+name))
 oldimport=builtins.__import__
 def guarded_import(name,*args,**kwargs):
  require(not name.startswith(('cs_source','cs_entry','cs_native','cs_process','cs_claim','cs_saved','run_cs','prepare_cs','legacy_','matrix_','native_account','numpy','pandas','polars')),'HISTORICAL_OR_ARRAY_RUNTIME_IMPORT_FORBIDDEN')
  return oldimport(name,*args,**kwargs)
 builtins.__import__=guarded_import
 import verify_packet
 result=verify_packet.verify_outer(packet,archive,a.trusted_zip_sha256)
 import test_packet
 tests=test_packet.run(packet,archive,a.trusted_zip_sha256);require(not attempts,'FORBIDDEN_COLD_ACTION_ATTEMPTS_REJECTED')
 # The trusted ZIP and its fresh extracted original members still match after mutations.
 verify_packet.verify_manifest(verify_packet.load(packet/'MANIFEST.json'),verify_packet.files(packet))
 require(hashlib.sha256(archive.read_bytes()).hexdigest()==a.trusted_zip_sha256,'TRUSTED_ARCHIVE_UNCHANGED_AFTER_TESTS')
 result=dict(schema='LEGACY_REMAINING24_ALL30_EXTERNALLY_TRUSTED_ISOLATED_COLD_AND_MUTATION_RUN_V1',status='PASS',verification=result,mutation_tests=tests,forbidden_attempts=attempts,fresh_extraction=True,external_trusted_ZIP_hash_checked_before_loading_packet_code=True,site_packages_disabled=True,inherited_authority_and_credential_environment_scrubbed=True,historical_imports=False,network_calls=0,child_process_launches=0,accounts_created=0,financial_clocks_advanced=0,all_extracted_original_members_unchanged_after_tests=True,private_original_or_authority_file_reads=0,all_saved_reads_confined_to_trusted_archive_fresh_extraction_or_standard_library=True,observed_read_count=len(file_reads),CPU_affinity=sorted(os.sched_getaffinity(0)),numerical_pools=1)
Path(a.receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status='PASS',cases=24,comparison_rows=30,tests=tests['test_count'],external_trust=h),sort_keys=True))

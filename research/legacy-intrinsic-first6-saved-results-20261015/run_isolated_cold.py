#!/usr/bin/env python3
"""External saved-only cold launcher. Hash-check trusted ZIP before loading its code."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{0})
import argparse,hashlib,json,tempfile,zipfile,sys,runpy,socket,subprocess,fcntl,builtins
from pathlib import Path,PurePosixPath
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--trusted-zip-sha256',required=True);p.add_argument('--receipt',required=True);a=p.parse_args()
archive=Path(a.archive).resolve();h=hashlib.sha256(archive.read_bytes()).hexdigest();assert h==a.trusted_zip_sha256,'EXTERNAL_TRUSTED_ZIP_HASH_MISMATCH'
with tempfile.TemporaryDirectory(prefix='legacy_saved_cold_') as td:
 root=Path(td)
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();assert len(names)==len(set(names));assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names);z.extractall(root)
 dirs=[d for d in root.iterdir() if d.is_dir()];assert len(dirs)==1;packet=dirs[0]
 # Import only reporting code from this fresh trusted extraction, never historical paths.
 sys.dont_write_bytecode=True;sys.path[:]=[str(packet)]+[s for s in sys.path if s and ('site-packages' not in s) and ('dist-packages' not in s) and (Path(s).is_absolute() and not Path(s).is_relative_to(Path.cwd()))]
 attempts=[]
 def blocked(label):
  def f(*args,**kwargs):attempts.append(label);raise RuntimeError('COLD_FORBIDDEN:'+label)
  return f
 for obj,names in ((socket,('create_connection','getaddrinfo')),(socket.socket,('connect','connect_ex')),(subprocess,('Popen','run','call','check_call','check_output')),(os,('system','fork','forkpty','posix_spawn','posix_spawnp','execv','execve','execvp','execvpe')),(fcntl,('flock',))):
  for name in names:
   if hasattr(obj,name):setattr(obj,name,blocked(getattr(obj,'__name__',str(obj))+'.'+name))
 oldimport=builtins.__import__
 def guarded_import(name,*args,**kwargs):
  assert not name.startswith(('legacy_','matrix_','native_account','run_legacy','numpy','pandas')),'HISTORICAL_OR_ARRAY_RUNTIME_IMPORT_FORBIDDEN'
  return oldimport(name,*args,**kwargs)
 builtins.__import__=guarded_import
 import verify_packet
 result=verify_packet.verify_outer(packet,archive,a.trusted_zip_sha256)
 import test_packet
 tests=test_packet.run(packet,archive,a.trusted_zip_sha256)
 assert not attempts
 result=dict(schema='LEGACY_FIRST6_ISOLATED_EXTERNALLY_TRUSTED_COLD_AND_MUTATION_RUN_V1',status='PASS',verification=result,mutation_tests=tests,forbidden_attempts=attempts,fresh_extraction=True,external_trusted_ZIP_hash_checked_before_loading_packet_code=True,historical_imports=False,network_calls=0,process_launches=0,accounts_created=0,financial_clocks_advanced=0,CPU_affinity=sorted(os.sched_getaffinity(0)),numerical_pools=1)
Path(a.receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='PASS',cases=6,tests=tests['test_count'],external_trust=h),sort_keys=True))

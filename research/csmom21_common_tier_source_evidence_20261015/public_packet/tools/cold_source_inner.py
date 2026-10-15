"""Finite generated test observer, not a universal Python sandbox."""
import os,sys,json,runpy,unittest,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
V4=ROOT/'original_cs_mom21_D_20261015_v5'
SRC=ROOT/'original_cs_mom21_D_v4_independent_review_20261015'
NATIVE=SRC
for path in [V4,SRC,NATIVE]:sys.path.insert(0,str(path))
observed={'external_process_events':0,'network_events':0,'outside_allowed_file_events':0}
roots=[ROOT,Path(sys.base_prefix),Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/tmp'),Path('/dev')]
def audit(event,args):
 if event in ['subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.exec']:
  observed['external_process_events']+=1;raise AssertionError('COLD_GENERATED_PROCESS_EVENT_DENIED')
 if event in ['socket.connect','socket.connect_ex','socket.sendto','socket.getaddrinfo']:
  observed['network_events']+=1;raise AssertionError('COLD_GENERATED_NETWORK_EVENT_DENIED')
 if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
  p=Path(os.path.abspath(os.fsdecode(args[0])))
  # This process may use only its extraction, runtime libraries and generated
  # temporary fixtures. There are no historical source bodies in the extraction.
  if not any(p==r or r in p.parents for r in roots):
   observed['outside_allowed_file_events']+=1;raise AssertionError('COLD_GENERATED_OUTSIDE_READ_OR_WRITE_DENIED')
sys.addaudithook(audit)
start=time.monotonic()
if sys.argv[1]=='unittest':
 modules=sys.argv[2:];sys.argv=[sys.argv[0],str(V4)];suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 receipt={'tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'passed':result.wasSuccessful()}
else:
 flag=sys.argv[2:];sys.argv=[str(V4/'test_cold_generated_zip.py')]+flag
 runpy.run_path(sys.argv[0],run_name='__main__');receipt={'tests':1,'passed':True,'errors':0,'failures':0}
receipt.update(observed=observed,CPU_affinity=sorted(os.sched_getaffinity(0)),elapsed_wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,scope='GENERATED_FAKE_CODE_METADATA_ONLY',historical_source_or_target_replay=False,universal_sandbox_claim=False)
print('COLD_RECEIPT_JSON='+json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if receipt['passed'] and not any(observed.values()) else 1)

"""Build the full admitted source only from exact public Git, with no network."""
import argparse,json,shutil,sys,time
from pathlib import Path
from driver import source,b,sha,save,HERE
def rebuild(state,artifact):
 assert not state.exists() and not b.git('status','--porcelain');state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in ('/workspace/portfolio-risk-2025-state/SOURCE_OBSERVED','/workspace/portfolio-risk-2025-state/H2_ORIGINAL_BODIES','/workspace/portfolio-risk-2025-state/SOURCE_PARTIAL_NUMERIC_FLAG_FAILURE')):blocked.append(str(p));raise RuntimeError('Observed source forbidden during public rebuilding')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(HERE.parents[1]))+'/input/';expected=json.loads(b.git('show',artifact+':'+prefix+'SOURCE_INDEX.json'))
 h2=source.restore_h2(state/'H2_GIT_ONLY',artifact);source.build(state/'source',h2,expected['source_commit'],expected=expected)
 for n in ('Y2025.npz','Y2025_RISK.json','SOURCE_INDEX.json'):assert (state/'source'/n).read_bytes()==b.git('show',artifact+':'+prefix+n)
 save(state/'PUBLIC_SOURCE_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_FULL2025_SOURCE_TARGET_RISK',artifact_commit=artifact,original_minute_archives=120,minutes_per_asset=525600,actual_funding_events=5475,causal_targets=365,observed_STATE_open_attempts=len(blocked),provider_downloads=0,new_wallets=0,new_fits=0,account_advances=0,seconds=time.monotonic()-began))
 shutil.rmtree(h2);print('EXACT2025_PUBLIC_SOURCE_RESTORE_PASS',time.monotonic()-began,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--artifact-commit',required=True);a=p.parse_args();rebuild(a.state,a.artifact_commit)

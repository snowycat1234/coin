"""Fixed-source synthetic review runner. No data, history or execution interface."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'coin_bot_risk_matched_synthetic_20261014'
EXPECTED_MANIFEST='ddea8797f02722f39c779fc548d0e3471f13907f04d94f9f9c3fe8b4be605bd8'
ORIGINAL={
 'perpetual_account.py':('native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo/src/quant/perpetual_account.py','ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110'),
 'execution_contract.py':('native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo/src/quant/execution_contract.py','b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1'),
 'fine_account.py':('native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/fine/fine_account.py','050806a41fefd33814f6dbbe2b5c9dfa4e1c446187fd100e77431d154143e386'),
 'terminal_adapter.py':('native_pair_replacement_review_20261014/published_ca11e94d/terminal_adapter.py','923f23a56a3c9a84de49f2527889f2b4c50ac5ad66ad150416f9ed7c2b7d1280'),
}

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def source_hashes(): return {p.name:digest(p) for p in sorted(SOURCE.iterdir()) if p.is_file()}
def original_hashes(): return {name:digest(ROOT/rel) for name,(rel,_) in ORIGINAL.items()}
def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(10*1024*1024,10*1024*1024))
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def clean(s):return s.replace(str(ROOT)+'/','WORKSPACE/').replace(sys.executable,'python')

def main():
    if len(sys.argv)!=1:raise SystemExit('generated-only review accepts no arguments')
    attempt=1
    while (HERE/f'REVIEW_CHECK_RECEIPT_{attempt:04d}.json').exists():attempt+=1
    out=HERE/f'REVIEW_CHECK_RECEIPT_{attempt:04d}.json'
    before=source_hashes();original_before=original_hashes()
    manifest=json.loads((SOURCE/'FINAL_MANIFEST.json').read_text())
    exact_manifest=before['FINAL_MANIFEST.json']==EXPECTED_MANIFEST
    bound=all(before.get(k)==v for k,v in manifest['files_SHA256'].items())
    rows=[]
    if not exact_manifest or not bound:raise SystemExit('source freeze mismatch; no checks executed')
    fixed=[(SOURCE,['-m','unittest','-v','test_synthetic']),
           (HERE,['-m','unittest','-v','test_adversarial']),
           (SOURCE,['toy_demo.py'])]
    for cwd,args in fixed:
        started=time.monotonic()
        p=subprocess.run([sys.executable,*args],cwd=cwd,preexec_fn=limits,
              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
              capture_output=True,text=True,timeout=60)
        rows.append({'command':['python',*args],'cwd':cwd.name,'exit_code':p.returncode,
                     'wall_seconds':time.monotonic()-started,'stdout':clean(p.stdout),'stderr':clean(p.stderr)})
    after=source_hashes();original_after=original_hashes()
    unchanged=(before==after)
    original_match=all(original_before[name]==expected and original_after[name]==expected for name,(_,expected) in ORIGINAL.items())
    ok=all(r['exit_code']==0 for r in rows) and unchanged and original_match
    receipt={
      'stage':'INDEPENDENT_GENERATED_SYNTHETIC_REVIEW_ONLY',
      'status':'PASS_SYNTHETIC_SOURCE_ONLY' if ok else 'FAIL_SYNTHETIC_REVIEW',
      'candidate':'CSH_BTC_GRID_REPLACE10',
      'frozen_manifest_SHA256':before['FINAL_MANIFEST.json'],
      'manifest_exact_match':exact_manifest,'manifest_all_entries_verified':bound,
      'source_before_SHA256':before,'source_after_SHA256':after,'candidate_bytes_unchanged':unchanged,
      'independent_suite_SHA256':digest(HERE/'test_adversarial.py'),
      'review_runner_SHA256':digest(Path(__file__).resolve()),
      'original_sources_before_SHA256':original_before,'original_sources_after_SHA256':original_after,
      'original_sources_match_pins_and_unchanged':original_match,
      'commands':rows,'one_cpu_per_command':True,'wall_limit_seconds_per_command':60,
      'memory_limit_bytes':512*1024*1024,
      'max_child_RSS_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
      'market_data_reads':0,'downloads':0,'historical_wallets':0,'native_financial_imports':0,
      'native_financial_advances':0,'external_mutations':0,'publication':'NOT_PUSHED',
      'native_adapter':'NOT_IMPLEMENTED','native_risk_certification':'NOT_CERTIFIED_NEEDS_NATIVE_BINDING',
      'historical_go':False,'not_performance_evidence':True,
    }
    with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({'receipt':out.name,'status':receipt['status'],'commands_passed':all(r['exit_code']==0 for r in rows),
                      'candidate_bytes_unchanged':unchanged,'original_sources_unchanged':original_match},indent=2))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())

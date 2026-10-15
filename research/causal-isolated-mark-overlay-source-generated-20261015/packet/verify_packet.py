"""Pure offline packet verification; optional synthetic checks only."""
import argparse, hashlib, json, os
from pathlib import Path, PurePosixPath
import subprocess, sys
ROOT=Path(__file__).resolve().parent
def verify():
    m=json.loads((ROOT/'FILE_MANIFEST.json').read_text())
    expected={x['path']:x for x in m['files']}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    if actual != set(expected)|{'FILE_MANIFEST.json'}: raise ValueError('Exact file set mismatch')
    for n,pin in expected.items():
        q=PurePosixPath(n)
        if q.is_absolute() or '..' in q.parts or not n or '\\' in n: raise ValueError('Unsafe path')
        p=ROOT/n
        if p.is_symlink(): raise ValueError('Symlink forbidden')
        b=p.read_bytes()
        if len(b)!=pin['bytes'] or hashlib.sha256(b).hexdigest()!=pin['SHA256']: raise ValueError('Byte pin mismatch: '+n)
    return len(expected)
def main():
    a=argparse.ArgumentParser();a.add_argument('--execute-generated',action='store_true');args=a.parse_args()
    count=verify();runs=[]
    if args.execute_generated:
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
        commands=[('author',39,[sys.executable,'-B','run_generated_tests.py'],ROOT/'causal_isolated_mark_overlay_20261015_v4'),('independent',24,[sys.executable,'-B','causal_isolated_mark_overlay_independent_review_20261015/run_independent_tests.py','causal_isolated_mark_overlay_20261015_v4'],ROOT)]
        for name,expected,cmd,cwd in commands:
            r=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=45,check=False)
            print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr)
            if r.returncode: raise RuntimeError(name+' generated suite failed')
            result=json.loads(r.stdout.strip().splitlines()[-1])
            if result['tests_run']!=expected or not result['successful'] or result['failures'] or result['errors'] or any(result['counters'].values()): raise ValueError('Unexpected guarded results')
            runs.append({'name':name,'tests':expected,'counters':result['counters']})
        verify()
    print(json.dumps({'status':'PASS_GENERATED_ONLY_NO_ACTUAL_AUTHORITY','payload_files':count,'runs':runs},sort_keys=True))
if __name__=='__main__':main()

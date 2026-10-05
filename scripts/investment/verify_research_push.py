"""Verify a published module and its explicitly preserved untracked work."""
import argparse, hashlib, json, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT

def git(*args):
    return subprocess.check_output([a.git_executable, *args], cwd=ROOT, text=True,timeout=60).strip()

def read(path):
    return json.loads(Path(path).read_bytes())

ap=argparse.ArgumentParser()
ap.add_argument('--git-executable',default='git',help='Existing Git binary; all scientific computation stays in bounded WSL')
for name in ('binding', 'gate', 'remote-head', 'output'):
    ap.add_argument('--'+name, required=True)
a=ap.parse_args();binding=read(a.binding);gate=read(a.gate)
assert binding['status']=='ACCEPTED_MODULE_SOURCE_BINDING'
assert gate['status']=='STAGED_MODULE_CHECKPOINT_PASS'
head=git('rev-parse','HEAD')
assert git('rev-parse','HEAD^')==binding['parent_commit']
remote=Path(a.remote_head).read_text().strip().split()
assert remote==[head, 'refs/heads/main'], 'Remote branch does not match local HEAD'
assert not git('diff','--name-only') and not git('diff','--cached','--name-only')
tracked=set(n for n in git('ls-files','-z').split('\0') if n)
for name, expected in binding['source_hashes'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, name
    assert name in tracked, name
untracked=set(n for n in git('ls-files','--others','--exclude-standard','-z').split('\0') if n)
assert untracked==set(binding['prior_WIP_preserved']), 'Untracked work changed'
out=Path(a.output).resolve();assert out.is_relative_to(ROOT/'reports')
with out.open('x') as f:
    json.dump(dict(status='MODULE_EXACT_REMOTE_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
        local_HEAD=head,remote_HEAD=head,parent_commit=binding['parent_commit'],
        source_binding_path=a.binding,source_binding_sha256=hashlib.sha256(Path(a.binding).read_bytes()).hexdigest(),
        staged_gate_path=a.gate,staged_gate_sha256=hashlib.sha256(Path(a.gate).read_bytes()).hexdigest(),
        tracked_worktree_clean=True,prior_WIP_preserved=sorted(untracked),git_executable=a.git_executable),f,indent=2)
    f.write('\n')
print(json.dumps(dict(status='MODULE_EXACT_REMOTE_VERIFIED',HEAD=head,preserved_WIP=len(untracked))))

"""Existing unchanged source, financial, snapshot and fingerprint APIs."""
import hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
follow=load('sma_frozen_follow_apis',ROOT/'research/rejected-break-follow-native-20261012/driver.py')
native,Closing,checkpoint,restore_snapshot,profile_sha=follow.native,follow.Closing,follow.checkpoint,follow.restore_snapshot,follow.profile_sha
SYMBOLS=follow.SYMBOLS;DAY=follow.DAY;MINUTE=60000000;save=follow.save
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert file_sha(ROOT/p)==s,p
def clean(commit):assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT) and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==commit
def window(key):
 W=proto()['windows'][key];return follow.window(key,Path(W['prepared']))
def fingerprint(frame):return [dict(name=c,dtype=frame[c].to_numpy().dtype.str,rows=frame.height,raw_SHA256=sha(frame[c].to_numpy().tobytes())) for c in frame.columns]

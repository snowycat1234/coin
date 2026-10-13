"""Stdlib exact-byte gate for operational continuation; old finance never edited."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
FILES={'resume_cases.py','RESUME_PLAN.json','PROTOCOL.md','test_resume.py','cold_recovery.py','resume_limits.py'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(require_review=False):
 m=json.loads((H/'FROZEN_RECOVERY.json').read_text())
 if m['status']!='PREPARED_SERIAL_CONTINUATION_NO_NEW_HISTORY' or m['bootstrap_SHA256']!=sha(H/'freeze_resume.py') or set(m['files_SHA256'])!=FILES:raise ValueError('Recovery exact file set changed')
 for n,s in m['files_SHA256'].items():
  if (H/n).is_symlink() or sha(H/n)!=s:raise ValueError('Recovery bytes changed: '+n)
 for n,s in m['dependencies_SHA256'].items():
  if sha(H.parent/n)!=s:raise ValueError('Original resume dependency changed: '+n)
 if require_review:
  r=json.loads((H/'REVIEW_RECEIPT.json').read_text())
  if r['status']!='PASS_INDEPENDENT_PRE_GO_SERIAL_RESUME_REVIEW' or r['freeze_manifest_SHA256']!=sha(H/'FROZEN_RECOVERY.json') or r['financial_advances']!=0:raise ValueError('Separate exact serial recovery review required')
 return m


def require_publication():
 verify(require_review=True);p=H/'PUBLICATION_RECEIPT.json';r=json.loads(p.read_text())
 if (r.get('status')!='PASS_EXACT_PRE_GO_REMOTE_RECOVERY_PUBLICATION' or r.get('remote_verified') is not True
  or r.get('recovery_manifest_SHA256')!=sha(H/'FROZEN_RECOVERY.json') or r.get('review_receipt_SHA256')!=sha(H/'REVIEW_RECEIPT.json')
  or r.get('resume_plan_SHA256')!=sha(H/'RESUME_PLAN.json') or r.get('remote_ref_exact') is not True):raise RuntimeError('Exact remote recovery preregistration required before continuation')
 return {'receipt_SHA256':sha(p)}

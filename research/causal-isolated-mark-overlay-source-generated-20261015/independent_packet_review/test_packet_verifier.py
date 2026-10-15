"""Focused isolated mutation probes; never edit the sealed packet or originals."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

OUT=Path(__file__).resolve().parent
COLD=OUT/'cold_packet'
PYTHON=OUT.parent/'coin_partial_restore_20261014/.venv/bin/python'
WORK=OUT/'mutation_probes'
WORK.mkdir(exist_ok=False)
RESULTS=[]

def write_manifest(root,data):
 (root/'FILE_MANIFEST.json').write_text(json.dumps(data,sort_keys=True)+'\n')
def mutate(case,root):
 m=json.loads((root/'FILE_MANIFEST.json').read_text())
 if case=='payload_byte_tamper':
  p=root/'README.md'; p.write_bytes(p.read_bytes()+b'\nMUTATION\n')
 elif case=='missing_payload': (root/'README.md').unlink()
 elif case=='unlisted_regular_file': (root/'unlisted.txt').write_text('mutation')
 elif case=='payload_file_symlink':
  p=root/'README.md'; target=WORK/'owned_readme_target.txt'; target.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(target)
 elif case=='payload_directory_symlink':
  p=root/'causal_isolated_mark_overlay_20261015_v4/evidence'; target=WORK/'owned_evidence_target'; shutil.copytree(p,target); shutil.rmtree(p); p.symlink_to(target,target_is_directory=True)
 elif case in ('parent_traversal_path','absolute_payload_path','noncanonical_dot_path','backslash_payload_path'):
  old='README.md'; row=next(x for x in m['files'] if x['path']==old)
  if case=='parent_traversal_path': row['path']='../README.md'
  elif case=='absolute_payload_path': row['path']='/README.md'
  elif case=='noncanonical_dot_path': row['path']='./README.md'
  else:
   row['path']='bad\\README.md'; (root/old).rename(root/row['path'])
  write_manifest(root,m)
 elif case=='duplicate_manifest_row': m['files'].append(dict(m['files'][0])); m['files_count']+=1; write_manifest(root,m)
 elif case=='incorrect_manifest_count': m['files_count']=999; write_manifest(root,m)
 elif case=='manifest_file_symlink':
  p=root/'FILE_MANIFEST.json'; target=WORK/'owned_manifest_target.json'; target.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(target)
 elif case=='unlisted_dangling_symlink': (root/'unlisted_link').symlink_to(root/'does_not_exist')
 else: raise AssertionError(case)

reject_cases=['payload_byte_tamper','missing_payload','unlisted_regular_file','payload_file_symlink','payload_directory_symlink','parent_traversal_path','absolute_payload_path','noncanonical_dot_path','backslash_payload_path']
limits=['duplicate_manifest_row','incorrect_manifest_count','manifest_file_symlink','unlisted_dangling_symlink']
for case in reject_cases+limits:
 root=WORK/case; shutil.copytree(COLD,root); mutate(case,root)
 r=subprocess.run(['taskset','-c','1',str(PYTHON),'-B','verify_packet.py'],cwd=root,env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'},capture_output=True,text=True,timeout=10)
 accepted=r.returncode==0
 expected_rejection=case in reject_cases
 assert not expected_rejection or not accepted,(case,r.stdout,r.stderr)
 detail=(r.stdout.strip().splitlines()[-1] if accepted else r.stderr.strip().splitlines()[-1])
 RESULTS.append({'case':case,'exit_code':r.returncode,'accepted':accepted,'expected_rejection':expected_rejection,'result':detail})
 # The mutation trees are intentionally not public review artifacts.
 shutil.rmtree(root)
for p in WORK.iterdir():
 if p.is_dir(): shutil.rmtree(p)
 else: p.unlink()
WORK.rmdir()
report={'schema':'ISOLATED_PACKET_VERIFIER_MUTATION_PROBES_V1','expected_rejections':len(reject_cases),'all_expected_rejections_pass':True,'structural_limits_observed':[x['case'] for x in RESULTS if not x['expected_rejection'] and x['accepted']],'results':RESULTS,'scope':'Externally SHA256-pinned archive remains authoritative. These mutations alter owned test copies only. The verifier is a regular-payload byte checker, not an authenticated manifest or whole-filesystem object validator.'}
(OUT/'VERIFIER_MUTATION_PROBES.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'expected_rejections':9,'all_expected_rejections_pass':True,'structural_limits_observed':report['structural_limits_observed']},sort_keys=True))

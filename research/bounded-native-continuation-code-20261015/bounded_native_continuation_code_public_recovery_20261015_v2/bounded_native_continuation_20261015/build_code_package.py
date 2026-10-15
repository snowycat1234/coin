"""Build local public-safe source packet, never publish or run history."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
NAME='bounded_native_continuation_code_public_recovery_20261015_v2'
OUTPUT=ROOT/NAME
if OUTPUT.exists():raise ValueError('EXCLUSIVE_NEW_CODE_PACKAGE_DIRECTORY_REQUIRED')
OUTPUT.mkdir()
pins=json.loads((HERE/'EXTERNAL_DEPENDENCY_PINS.json').read_bytes())
for category in ('external_code_files','preserved_evidence_files'):
    for name,record in pins[category].items():
        if '/root_go_2024_' in name:continue # Original evidence omitted, exact pins retained.
        path=ROOT/name;raw=path.read_bytes()
        if sha256(raw).hexdigest()!=record['SHA256'] or len(raw)!=record['bytes']:raise ValueError('DEPENDENCY_PIN_CHANGED:'+name)
        target=OUTPUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
files=('integration.py','continuation_entry.py','run_finite.py','test_integration.py','test_coupled_boundaries.py',
    'test_finite.py','test_continuation_entry.py','profile_generated.py','README.md','EXTERNAL_DEPENDENCY_PINS.json',
    'TEST_LOG_FINAL.txt','GENERATED_RESOURCE_PROFILE.json','ROOT_GO_TEMPLATE_UNAPPROVED.json','PER_SCOPE_PROOF.json',
    'verify_code_package.py','build_code_package.py','PUBLIC_COPY_METADATA.json')
for name in files:
    target=OUTPUT/HERE.name/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/('GENERATED_RESOURCE_PROFILE_REVIEW_BOUND.json' if name=='GENERATED_RESOURCE_PROFILE.json' else name),target)
# Exact generated fixture helpers; no captured market content.
for name in ('test_native_runtime.py','test_frozen_grid.py'):
    shutil.copyfile(ROOT/'traditional_three_tier_freeze_20261015'/name,OUTPUT/'traditional_three_tier_freeze_20261015'/name)
review=ROOT/'bounded_native_continuation_independent_review_20261015'
for name in ('test_independent_integration.py','INDEPENDENT_NATIVE_CONTINUATION_REVIEW.json','SOURCE_ONLY_FINAL_VERIFICATION.json','ALL_AUTHOR_SUITE_FINAL.txt','INDEPENDENT_FINAL.txt'):
    if not (review/name).is_file():raise ValueError('FINAL_INDEPENDENT_REVIEW_FILE_REQUIRED:'+name)
    target=OUTPUT/review.name/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(review/name,target)
preparation=HERE/'source_only_preparation_attempt003/PREPARATION.json'
target=OUTPUT/HERE.name/'source_only_preparation_attempt003/PREPARATION.json';target.parent.mkdir(parents=True);shutil.copyfile(preparation,target)
# Metadata receipt only; required external source/targets remain separately pinned.
shutil.copyfile(HERE/'SOURCE_PREPARATION_ATTEMPT003_REVALIDATION_RECEIPT.json',OUTPUT/HERE.name/'SOURCE_PREPARATION_ATTEMPT003_REVALIDATION_RECEIPT.json')
(OUTPUT/'README.txt').write_text('Source/code-only offline bounded native continuation candidate.\nNo historical market arrays, saved account results, credentials or new root GO are included.\nRead bounded_native_continuation_20261015/README.md. Generated tests run from that directory.\nSource-audit tests require the separately restored exact pinned sources/target artifacts.\nThe ROOT_GO template is deliberately unapproved and fails admission.\n')
manifest={str(p.relative_to(OUTPUT)):dict(bytes=p.stat().st_size,SHA256=sha256(p.read_bytes()).hexdigest()) for p in sorted(OUTPUT.rglob('*')) if p.is_file()}
(OUTPUT/'FILES.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=ROOT/(NAME+'.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as stream:
    for p in sorted(OUTPUT.rglob('*')):
        if p.is_file():stream.write(p,str(p.relative_to(ROOT)))
record=dict(path=archive.name,bytes=archive.stat().st_size,SHA256=sha256(archive.read_bytes()).hexdigest(),
    files=len(manifest)+1,source_only=True,new_historical_GO_included=False,publication_actions=0)
(HERE/'CODE_PACKAGE.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))

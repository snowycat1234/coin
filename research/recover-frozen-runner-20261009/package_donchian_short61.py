"""Preserve one audited short diagnostic in compact relative-path transport."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

HERE=Path(__file__).resolve().parent


def package(state,destination):
    from summarize_donchian_short61 import summarize
    results=summarize(state)
    package_root=state/'portable-donchian-short61'
    package_root.mkdir(exist_ok=False);destination.mkdir(exist_ok=False)
    source=state/'donchian-short61/DONCHIAN20_EXIT10_SHORT_ONLY'
    shutil.copytree(source,package_root/'accounts/DONCHIAN20_EXIT10_SHORT_ONLY')
    for name in ('DONCHIAN_SHORT61_PLAN.json','DONCHIAN_SHORT61_PREFLIGHT.json','verify_native61.py','requirements-native61.txt','requirements.txt'):
        shutil.copyfile(HERE/name,package_root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        dest=package_root/'verification_helpers'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE/'verification_helpers'/name,dest)
    shutil.copyfile(HERE/'DONCHIAN_SHORT61_README.md',package_root/'README.md')
    (package_root/'DONCHIAN_SHORT61_RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    files=[]
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for file in sorted(package_root.rglob('*')):
        if not file.is_file():continue
        data=file.read_bytes()
        assert '__pycache__' not in file.parts
        if file.suffix in ('.json','.py','.txt','.md'):
            assert not any(s in data for s in (b'/workspace/',b'/mnt/d/',b'/home/xflops/')),file
            assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',data),file
        files.append(dict(path=file.relative_to(package_root).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest=dict(schema='DONCHIAN_SHORT61_UNCHANGED_JOURNAL_MEMBERS_V1',files=files,
        original_account_journals_edited=False,raw_market_archives_included=False,private_runtime_inventory_included=False)
    (package_root/'RESULT_MEMBER_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=state/'coin_fixed_Donchian_short_native61_results_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(package_root.rglob('*')):
            if file.is_file():z.write(file,file.relative_to(package_root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        part=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}'
        (destination/name).write_bytes(part);parts.append(dict(path=name,bytes=len(part),sha256=sha(part)))
    artifact=dict(schema='DONCHIAN_SHORT61_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=sha(data),
        part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha((package_root/'RESULT_MEMBER_HASHES.json').read_bytes()),
        account_journals_byte_identical=True,raw_market_archives_duplicated=False)
    for name in ('RESULT_MEMBER_HASHES.json','DONCHIAN_SHORT61_RESULTS.json','README.md'):
        shutil.copyfile(package_root/name,destination/name)
    (destination/'ARTIFACT.json').write_text(json.dumps(artifact,indent=2)+'\n')
    print(json.dumps(dict(status='PASS_PACKAGED_UNCHANGED_JOURNALS',files=len(files),bytes=len(data),sha256=artifact['sha256'],parts=len(parts))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    package(a.state,a.destination)

"""Preserve four unchanged audited accounts as portable small transport parts."""
import argparse, hashlib, json, re, shutil, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent


def package(state, public):
    results=json.loads((state/'MOMENTUM_SHORT_RESULTS.json').read_bytes())
    assert results['status']=='PASS_FOUR_COMPLETE_INDEPENDENT_ACCOUNTS_AND_FROZEN_TARGETS'
    root=state/'portable-momentum-short'; root.mkdir(exist_ok=False); public.mkdir(exist_ok=False)
    for case in results['cases']: shutil.copytree(state/'momentum-short'/case,root/'accounts'/case)
    for name in ('MOMENTUM_SHORT_PLAN.json','MOMENTUM_SHORT_PREFLIGHT.json','verify_momentum_short.py','verify_native61.py',
                 'verify_short_regimes.py','verify_market_execution.py','requirements-native61.txt','requirements.txt'):
        shutil.copyfile(HERE/name,root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        dest=root/'verification_helpers'/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(HERE/'verification_helpers'/name,dest)
    shutil.copyfile(HERE/'MOMENTUM_SHORT_README.md',root/'README.md')
    shutil.copyfile(state/'MOMENTUM_SHORT_RESULTS.json',root/'MOMENTUM_SHORT_RESULTS.json')
    sha=lambda b:hashlib.sha256(b).hexdigest(); files=[]
    for file in sorted(root.rglob('*')):
        if not file.is_file(): continue
        data=file.read_bytes(); assert '__pycache__' not in file.parts
        if file.suffix in ('.json','.py','.md','.txt'):
            assert not re.search(rb'/(?:workspace|mnt/d|home/xflops)/[A-Za-z0-9_.-]',data),file
            assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',data),file
        files.append(dict(path=file.relative_to(root).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest=dict(schema='FOUR_FIXED_MOMENTUM_SHORT_RESULT_MEMBERS_V1',files=files,original_account_journals_edited=False,
                  raw_market_archives_included=False,private_runtime_inventory_included=False)
    (root/'RESULT_MEMBER_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=state/'coin_fixed_momentum_short_four_regimes_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(root.rglob('*')):
            if file.is_file(): z.write(file,file.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    data=archive.read_bytes(); parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        b=data[start:start+768*1024]; name=archive.name+f'.bytepart{i:03d}'; (public/name).write_bytes(b)
        parts.append(dict(path=name,bytes=len(b),sha256=sha(b)))
    artifact=dict(schema='FOUR_FIXED_MOMENTUM_SHORT_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=sha(data),
        part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha((root/'RESULT_MEMBER_HASHES.json').read_bytes()),
        account_journals_byte_identical=True,raw_market_archives_duplicated=False)
    for name in ('RESULT_MEMBER_HASHES.json','MOMENTUM_SHORT_RESULTS.json','README.md'): shutil.copyfile(root/name,public/name)
    (public/'ARTIFACT.json').write_text(json.dumps(artifact,indent=2)+'\n')
    print(json.dumps(dict(status='PASS_FOUR_AUDITED_UNCHANGED_ACCOUNT_PACKAGE',members=len(files),bytes=len(data),sha256=artifact['sha256'],parts=len(parts))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);a=p.parse_args()
    package(a.state,a.public)

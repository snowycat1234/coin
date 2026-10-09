"""Compact immutable journals and separate causal context deliverables."""
import argparse,hashlib,json
from pathlib import Path
import re,shutil,zipfile

HERE=Path(__file__).resolve().parent


def package(state,public):
    from summarize_short_regimes import summarize
    results=summarize(state);root=state/'portable-short-regimes';root.mkdir(exist_ok=False);public.mkdir(exist_ok=False)
    for case in ('NOV2022','JAN2023','OKX86'):shutil.copytree(state/'short-regimes'/case,root/'accounts'/case)
    for name in ('SHORT_REGIMES_PLAN.json','SHORT_REGIMES_PREFLIGHT.json','SHORT_JUNE_ATTRIBUTION.json','verify_short_regimes.py','verify_market_execution.py','requirements-native61.txt','requirements.txt'):
        shutil.copyfile(HERE/name,root/name)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        dest=root/'verification_helpers'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,dest)
    shutil.copyfile(HERE/'SHORT_REGIMES_README.md',root/'README.md')
    shutil.copytree(state/'short-expert-contexts',root/'short-contexts')
    (root/'SHORT_REGIMES_RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    files=[];sha=lambda b:hashlib.sha256(b).hexdigest()
    for file in sorted(root.rglob('*')):
        if not file.is_file():continue
        data=file.read_bytes();assert '__pycache__' not in file.parts
        if file.suffix in ('.json','.py','.md','.txt'):
            assert not re.search(rb'/(?:workspace|mnt/d|home/xflops)/[A-Za-z0-9_.-]',data),file
            assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',data),file
        files.append(dict(path=file.relative_to(root).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest=dict(schema='THREE_FROZEN_SHORT_REGIME_RESULT_MEMBERS_V1',files=files,original_account_journals_edited=False,raw_market_archives_included=False,private_runtime_inventory_included=False)
    (root/'RESULT_MEMBER_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=state/'coin_frozen_short_three_regime_results_20261009.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(root.rglob('*')):
            if file.is_file():z.write(file,file.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        b=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';(public/name).write_bytes(b);parts.append(dict(path=name,bytes=len(b),sha256=sha(b)))
    artifact=dict(schema='FROZEN_SHORT_THREE_REGIMES_ORDERED_RESULT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=sha(data),part_max_bytes=768*1024,parts=parts,
        member_manifest_sha256=sha((root/'RESULT_MEMBER_HASHES.json').read_bytes()),account_journals_byte_identical=True,raw_market_archives_duplicated=False)
    for name in ('RESULT_MEMBER_HASHES.json','SHORT_REGIMES_RESULTS.json','README.md'):shutil.copyfile(root/name,public/name)
    (public/'ARTIFACT.json').write_text(json.dumps(artifact,indent=2)+'\n')
    target=HERE/'short-contexts';shutil.copytree(state/'short-expert-contexts',target)
    print(json.dumps(dict(status='PASS_THREE_AUDITED_ACCOUNT_PACKAGE_AND_SEPARATE_CONTEXTS',members=len(files),bytes=len(data),sha256=artifact['sha256'],parts=len(parts))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);a=p.parse_args()
    package(a.state,a.public)

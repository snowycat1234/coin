"""Publish newly acquired immutable originals once, in bounded Git parts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
digest=lambda b:hashlib.sha256(b).hexdigest()


def run(state):
    proof=json.loads((state/"RECOVERY.json").read_bytes())
    assert proof["actual_minutes"]==446400 and proof["fits"]==proof["wallets"]==0
    root=HERE/"source-parts"
    root.mkdir(exist_ok=False)
    records=[]
    for row in proof["sources"]:
        logical=row["raw_name"]
        p=Path(proof["raw_cache_path"])/logical
        raw=p.read_bytes()
        assert len(raw)==row["bytes"] and digest(raw)==row["SHA256"]
        folder=root/row["family"]/row["symbol"]
        folder.mkdir(parents=True)
        parts=[]
        for j,start in enumerate(range(0,len(raw),800000)):
            b=raw[start:start+800000]
            target=folder/(p.name+f".part{j:04d}")
            target.write_bytes(b)
            parts.append(dict(path=str(target.relative_to(HERE)),bytes=len(b),SHA256=digest(b)))
        check=Path(str(p)+".CHECKSUM").read_bytes()
        assert digest(check)==row["CHECKSUM"]
        target=folder/(p.name+".CHECKSUM")
        target.write_bytes(check)
        records.append(dict(**row,parts=parts,checksum_path=str(target.relative_to(HERE))))
    (HERE/"prepared").mkdir(exist_ok=False)
    for name,sha in proof["derived"].items():
        raw=(state/"prepared"/name).read_bytes()
        assert digest(raw)==sha
        (HERE/"prepared"/name).write_bytes(raw)
    shutil.copyfile(state/"RECOVERY.json",HERE/"RECOVERY.json")
    record=dict(source_commit=proof["source_commit"],source_monthly_archives=10,
        original_bytes=sum(r["bytes"] for r in records),originals_uploaded_once=True,
        reused_old_daily_source_commit="49017d88b75498a53f90857fe0d01a622e812a2f",
        reused_old_wrapper_path="research/cached-history-repair-20261010/RECOVERY.zip",
        reused_old_wrapper_SHA256="42e59bf2200034f433816fc70b8a2da43eb36363810ba356d8ffdc3ddb7be929",
        reused_old_manifest_path="research/cached-history-repair-20261010/MANIFEST.json",
        reused_old_manifest_SHA256="8191e0e26287ded3c02302b63f9c7f1f90b2396ff04e09385d9bbcf9b2b18ad6",
        monthly_sources=records,prepared=proof["derived"],fits=0,wallets=0)
    assert record["original_bytes"]==12901147 and record["original_bytes"]<30000000
    (HERE/"SOURCE_INDEX.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(json.dumps(dict(original_bytes=record["original_bytes"],archives=10,parts=sum(len(r["parts"]) for r in records),fits=0,wallets=0)))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--state",type=Path,required=True)
    run(p.parse_args().state)

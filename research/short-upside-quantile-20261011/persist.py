"""Save minimal novel panels/models; reference already-published price panels."""
import argparse
import json
from pathlib import Path
import zipfile
import numpy as np
from prepare import HERE,file_sha,digest


def run(state):
    temp=state/'export'
    temp.mkdir(exist_ok=False)
    panels=np.load(state/'prepared/SOURCE_PANELS.npz',allow_pickle=False)
    np.savez_compressed(temp/'NEW_MARK2021.npz',symbol_order=panels['symbol_order'],available_us=panels['A2021_available_us'],mark=panels['A2021_mark'])
    files={'prepared/NEW_MARK2021.npz':temp/'NEW_MARK2021.npz'}
    for p in (state/'prepared').iterdir():
        if p.name!='SOURCE_PANELS.npz':
            files['prepared/'+p.name]=p
    for p in (state/'diagnostic').iterdir():
        files['diagnostic/'+p.name]=p
    archive=temp/'RESULT_BUNDLE.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,p in files.items():
            z.writestr(name,p.read_bytes())
    raw=archive.read_bytes()
    folder=HERE/'result-parts'
    folder.mkdir(exist_ok=False)
    parts=[]
    for j,k in enumerate(range(0,len(raw),800000)):
        b=raw[k:k+800000];name=f'RESULT_BUNDLE.zip.part{j:04d}'
        (folder/name).write_bytes(b)
        parts.append(dict(path='result-parts/'+name,bytes=len(b),SHA256=digest(b)))
    manifest=dict(bytes=len(raw),SHA256=digest(raw),parts=parts,
        members={n:dict(bytes=p.stat().st_size,SHA256=file_sha(p)) for n,p in files.items()},
        reuse=[dict(commit='b4756ec8fb59457cfd8db74a79ca6a859f07f331',path='research/har-rv-risk-20261011/RESULT_BUNDLE.zip',SHA256='534cea64e8aa6b27b51bba1b4ffa0ff2305e42843c6022d75a68cc301ec27b17',read_only_member='prepared/FIVE_MIN_CLOSES.npz'),
            dict(commit='2cb08742a319d20cf983aa4f98650ace5330b057',path='research/core5-october-warmup-20261011/prepared/FIVE_MIN_CLOSES.npz',SHA256='0ae6eae2cd08d8bb99ab1959221d003c47ca085833f4d51175cd1c6a2df46471'),
            dict(commit='8e739aebaa8549e4dab8165d4aba265ba38da59c',path='research/core5-2022-rv-source-20261011/DATA_BUNDLE.zip',SHA256='409e811be7f555a6e1e5d13d1f84900b8150e11c5a3ae419caf7817217224fe0',read_only_member='prepared/FIVE_MIN_CLOSES.npz')],
        no_existing_large_price_source_reupload=True,source_commit=json.loads((state/'diagnostic/RESULT.json').read_bytes())['source_commit'],
        historical_fits=5,wallets=0)
    assert len(raw)<40000000
    (HERE/'PUBLIC_BUNDLE.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    (HERE/'RESULT.json').write_bytes((state/'diagnostic/RESULT.json').read_bytes())
    print(json.dumps(dict(bytes=len(raw),parts=len(parts),members=len(files),existing_large_price_sources_reuploaded=0,historical_fits=5,wallets=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True)
    run(p.parse_args().state)

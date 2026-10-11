"""Publish each completed source phase once; existing large originals are referenced."""
import argparse
import json
from pathlib import Path
import shutil
from prepare import HERE,ROOT,digest,save


def run(state):
    proof=json.loads((state/'RECOVERY.json').read_bytes())
    assert proof['fits']==proof['wallets']==proof['labels_created']==0
    target=HERE/'phases'/proof['phase'];target.mkdir(parents=True,exist_ok=False)
    def parts(raw,folder,name):
        folder.mkdir(parents=True,exist_ok=True);records=[]
        for i,start in enumerate(range(0,len(raw),800000)):
            b=raw[start:start+800000];p=folder/(name+f'.part{i:04d}')
            with p.open('xb') as f:f.write(b)
            records.append(dict(path=str(p.relative_to(ROOT)),bytes=len(b),SHA256=digest(b)))
        return records
    original={}
    for row in proof['sources']:
        s=row['source']
        if s.get('kind')!='NEW_OFFICIAL_RAW':continue
        p=state/s['raw_path'];raw=p.read_bytes();check=Path(str(p)+'.CHECKSUM').read_bytes()
        assert len(raw)==s['ZIP_bytes'] and digest(raw)==s['ZIP_SHA256'] and digest(check)==s['CHECKSUM_member_SHA256']
        folder=target/'source-parts'/s['symbol'];pieces=parts(raw,folder,p.name)
        cp=folder/(p.name+'.CHECKSUM');cp.write_bytes(check)
        original[s['ZIP_SHA256']]={k:v for k,v in s.items() if k not in ('raw_path','kind')}
        original[s['ZIP_SHA256']].update(kind='NEW_PUBLIC_PARTS',artifact_commit='CURRENT_ARTIFACT',parts=pieces,
            checksum_path=str(cp.relative_to(ROOT)))
    def convert(x):
        if isinstance(x,list):return [convert(y) for y in x]
        if isinstance(x,dict):
            if x.get('kind')=='NEW_OFFICIAL_RAW':return original[x['ZIP_SHA256']]
            return {k:convert(v) for k,v in x.items()}
        return x
    published=convert(proof);artifacts={}
    for name,sha in proof['artifacts'].items():
        b=(state/name).read_bytes();assert digest(b)==sha
        artifacts[name]=dict(SHA256=sha,bytes=len(b),parts=parts(b,target/'prepared',name))
    save(target/'RECOVERY.json',published)
    save(target/'SOURCE_INDEX.json',dict(phase=proof['phase'],source_commit=proof['source_commit'],
        protocol_SHA256=proof['protocol_SHA256'],source_inventory_SHA256=proof['source_inventory_SHA256'],
        original_new_source_count=len(original),original_new_bytes=sum(r['ZIP_bytes'] for r in original.values()),
        original_new_parts=sum(len(r['parts']) for r in original.values()),originals_uploaded_once=True,
        proof_SHA256=digest((target/'RECOVERY.json').read_bytes()),artifacts=artifacts,fits=0,wallets=0))
    print(json.dumps(dict(phase=proof['phase'],new_sources=len(original),new_original_bytes=sum(r['ZIP_bytes'] for r in original.values()),
        calendar_days=proof['calendar_days'],valid_joint_days=proof['valid_joint_RV_days'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);run(p.parse_args().state)

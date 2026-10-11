"""Source-only byte packing; publish new monthly/daily archives exactly once."""
import argparse
import json
from pathlib import Path
from mark_source import HERE,ROOT,digest,save


def walk(value):
    if isinstance(value,dict):
        if value.get('kind')=='NEW_OFFICIAL_RAW':yield value
        for v in value.values():yield from walk(v)
    elif isinstance(value,list):
        for v in value:yield from walk(v)


def run(state):
    proof=json.loads((state/'RECOVERY.json').read_bytes())
    assert proof['fits']==proof['wallets']==proof['labels_created']==0
    target=HERE/'phases'/proof['phase'];target.mkdir(parents=True,exist_ok=False)
    def parts(raw,folder,name):
        folder.mkdir(parents=True,exist_ok=True);rows=[]
        for i,start in enumerate(range(0,len(raw),800000)):
            b=raw[start:start+800000];p=folder/(name+f'.part{i:04d}')
            with p.open('xb') as f:f.write(b)
            rows.append(dict(path=str(p.relative_to(ROOT)),bytes=len(b),SHA256=digest(b)))
        return rows
    originals={}
    for s in walk(proof):
        if s['ZIP_SHA256'] in originals:continue
        p=state/s['raw_path'];b=p.read_bytes();check=Path(str(p)+'.CHECKSUM').read_bytes()
        assert len(b)==s['ZIP_bytes'] and digest(b)==s['ZIP_SHA256'] and digest(check)==s['CHECKSUM_member_SHA256']
        folder=target/'source-parts'/s['symbol'];pieces=parts(b,folder,p.name)
        cp=folder/(p.name+'.CHECKSUM');cp.write_bytes(check)
        originals[s['ZIP_SHA256']]={k:v for k,v in s.items() if k not in ('kind','raw_path')}
        originals[s['ZIP_SHA256']].update(kind='NEW_PUBLIC_PARTS',artifact_commit='CURRENT_ARTIFACT',
            parts=pieces,checksum_path=str(cp.relative_to(ROOT)))
    assert sum(r['ZIP_bytes'] for r in originals.values())==proof['new_original_bytes']
    def convert(value):
        if isinstance(value,list):return [convert(v) for v in value]
        if isinstance(value,dict):
            if value.get('kind')=='NEW_OFFICIAL_RAW':
                # Preserve newlyattachedrepair dependencies on monthly source row.
                return {**originals[value['ZIP_SHA256']],**({'new_daily_repairs':convert(value['new_daily_repairs'])} if value.get('new_daily_repairs') else {})}
            return {k:convert(v) for k,v in value.items()}
        return value
    artifacts={}
    for name,sha in proof['artifacts'].items():
        b=(state/name).read_bytes();assert digest(b)==sha
        artifacts[name]=dict(SHA256=sha,bytes=len(b),parts=parts(b,target/'prepared',name))
    save(target/'RECOVERY.json',convert(proof))
    save(target/'SOURCE_INDEX.json',dict(phase=proof['phase'],source_commit=proof['source_commit'],
        protocol_SHA256=proof['protocol_SHA256'],source_inventory_SHA256=proof['source_inventory_SHA256'],
        original_new_source_count=len(originals),original_new_bytes=proof['new_original_bytes'],
        original_new_parts=sum(len(r['parts']) for r in originals.values()),originals_uploaded_once=True,
        proof_SHA256=digest((target/'RECOVERY.json').read_bytes()),artifacts=artifacts,fits=0,wallets=0))
    print('MARK_PHASE_PUBLISHED',proof['phase'],len(originals),'new originals',proof['new_original_bytes'],'bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);run(p.parse_args().state)

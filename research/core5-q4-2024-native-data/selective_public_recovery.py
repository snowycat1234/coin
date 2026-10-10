"""Recover only 45 source ZIP members using exact public GitHub byte ranges."""
import argparse
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import struct
import threading
from urllib.request import Request, urlopen
import zipfile
import zlib

COMMIT = 'd69e9ac94478c5be54cb46c622afec7aaf3c61f7'
BASE = f'https://raw.githubusercontent.com/snowycat1234/coin/{COMMIT}/research_artifacts/native_20261008/byteparts/'
BUDGET = 180 * 1024 * 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root, project_root):
    inventory = json.loads((root/'INVENTORY.json').read_text())
    contents = json.loads((root/'PACK_CONTENTS.json').read_text())
    assert contents['source_commit'] == COMMIT
    prior = []
    for name in ['MULTI_ASSET_CONTINUOUS_RELEASE_METADATA_20261004_V1/ACCEPTED-CONTINUOUS-INPUT_MANIFEST.json', 'MULTI_ASSET_WINTER_RELEASE_METADATA_20261004_V1/ACCEPTED-WINTER-INPUT_MANIFEST.json']:
        prior.extend(json.loads((project_root/'docs/archive'/name).read_text())['market_records'])
    entries = {}
    for pack in contents['packs']:
        starts = [0]
        for part in pack['parts']:
            starts.append(starts[-1]+part['bytes'])
        assert starts[-1] == pack['original_bytes']
        for member in pack['members']:
            entries[member['name']] = (pack,starts,member)
    targets = [r for r in inventory['records'] if r['source_frequency']=='monthly']
    assert len(targets) == 45
    estimated = sum(r['size'] for r in targets) + 65536*3 + 8192*len(targets)
    assert estimated < BUDGET
    lock, stopped = threading.Lock(), threading.Event()
    transferred, request_count = 0, 0

    def fetch(pack, starts, offset, count):
        nonlocal transferred, request_count
        chunks=[]
        while count:
            if stopped.is_set():
                raise ValueError('Route stopped after an earlier range failure')
            index = bisect_right(starts,offset)-1
            part = pack['parts'][index]
            local = offset-starts[index]
            size = min(count,part['bytes']-local)
            assert size > 0
            url = BASE+part['file_name']
            req = Request(url,headers={'Range':f'bytes={local}-{local+size-1}'})
            try:
                with urlopen(req,timeout=30) as response:
                    assert response.status == 206
                    assert response.headers['Content-Range'] == f"bytes {local}-{local+size-1}/{part['bytes']}"
                    body = response.read(size+1)
                    assert len(body)==size
            except BaseException:
                stopped.set()
                raise
            with lock:
                transferred += len(body)
                request_count += 1
                assert transferred <= estimated and transferred <= BUDGET
            chunks.append(body)
            offset+=size
            count-=size
        return b''.join(chunks)

    def obtain(record):
        source = next(x for x in prior if x['symbol']==record['symbol'] and x['kind']==record['family'] and x['month']==record['month'])
        original_hash = source.get('zip_sha256') or source['entry']['checksum']['announced_zip_sha256']
        assert original_hash == record['SHA256'], 'Official archive identity differs from accepted source manifest'
        path = root/'Q42024/raw'/record['family']/record['symbol']/Path(record['key']).name
        path.parent.mkdir(parents=True,exist_ok=True)
        member_name='tail_data/data/raw/'+record['family']+'/'+record['symbol']+'/'+path.name
        pack,starts,member=entries[member_name]
        assert member['compression']==zipfile.ZIP_STORED and member['bytes']==member['compressed_bytes']==record['size']
        if not path.exists():
            header = fetch(pack,starts,member['local_header_offset'],30)
            fields = struct.unpack('<4s5H3I2H',header)
            assert fields[0]==b'PK\x03\x04' and fields[3]==zipfile.ZIP_STORED
            name_length,extra_length=fields[-2:]
            assert 0<name_length<1024 and extra_length<4096
            metadata = fetch(pack,starts,member['local_header_offset']+30,name_length+extra_length)
            assert metadata[:name_length].decode()==member_name
            body = fetch(pack,starts,member['local_header_offset']+30+name_length+extra_length,member['compressed_bytes'])
            assert f'{zlib.crc32(body):08x}'==member['CRC32']
            assert hashlib.sha256(body).hexdigest()==record['SHA256']
            temporary=path.with_suffix('.zip.partial')
            temporary.write_bytes(body)
            temporary.rename(path)
        assert path.stat().st_size==record['size'] and sha(path)==record['SHA256']
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
        Path(str(path)+'.CHECKSUM').write_text(record['checksum_text'])
        print(json.dumps({'verified':path.name,'family':record['family'],'bytes':record['size'],'source':'SELECTIVE_PUBLIC_REPOSITORY_MEMBER'}),flush=True)
        return {'key':record['key'],'cached_path':str(path),'SHA256':record['SHA256'],'source_pack':pack['original_file'],'member':member_name,'outer_member_CRC32':member['CRC32'],'accepted_normalized_source_SHA256':source['normalized_sha256']}

    with ThreadPoolExecutor(max_workers=4) as pool:
        recovered = list(pool.map(obtain,targets))
    bykey={r['key']:r for r in recovered}
    for record in inventory['records']:
        if record['key'] in bykey:
            record['cached_verified_path']=bykey[record['key']]['cached_path']
            record['selective_public_recovery']=bykey[record['key']]
    inventory['expected_new_download_bytes']=sum(r['size'] for r in inventory['records'] if not r['cached_verified_path'])
    inventory['reuse_archive_count']=sum(bool(r['cached_verified_path']) for r in inventory['records'])
    inventory['new_provider_download_estimate_bytes']=inventory['expected_new_download_bytes']
    (root/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n')
    receipt={'status':'EXACT45_SELECTIVE_PUBLIC_RAW_SOURCE_MEMBERS_VERIFIED','source_commit':COMMIT,'checked_UTC':datetime.now(timezone.utc).isoformat(),'raw_archives':45,'raw_archive_bytes':sum(r['size'] for r in targets),'actual_public_range_body_bytes':transferred,'HTTP_range_requests':request_count,'fresh_provider_archive_body_downloads':0,'remaining_provider_body_estimate_bytes':inventory['expected_new_download_bytes'],'every_original_matches_fresh_official_and_accepted_manifest_SHA256':True,'every_original_inner_ZIP_CRC_verified':True,'whole_outer_archives_or_parts_SHA256_verified':False,'outer_integrity_scope':'Only selected stored member CRCs checked; full original SHA256 verified independently against official and accepted source metadata. No unrelated members recovered.','records':recovered}
    (root/'SELECTIVE_RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='records'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--project-root',type=Path,required=True)
    a=p.parse_args()
    main(a.root,a.project_root)

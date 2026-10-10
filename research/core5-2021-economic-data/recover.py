"""Recover a pinned public packet; verify parts, wrapper, members and original ZIPs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import re
import shutil
from urllib.request import urlopen
import zipfile

PREFIX='research/core5-2021-economic-data'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def remote(url,limit):
    with urlopen(url,timeout=30) as r:
        assert r.status==200
        body=r.read(limit+1)
        assert len(body)<=limit,'Response exceeds declared bound'
    return body

def safe(name):
    p=PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    return p

def main(commit,output,cache):
    assert re.fullmatch('[0-9a-f]{40}',commit),'Immutable full commit required'
    assert shutil.disk_usage(output.parent).free>15*2**30+500*2**20
    output.mkdir(exist_ok=False)
    base=f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/{PREFIX}/'
    body=remote(base+'Y2021/INDEX.json',500000)
    (output/'INDEX.json').write_bytes(body);index=json.loads(body)
    assert index['schema']=='CORE5_FIXED2021_RECOVERABLE_ECONOMIC_PACKET_V1'
    assert index['maximum_part_bytes']==768*1024
    parts=output/'parts';parts.mkdir()
    def obtain(r):
        assert re.fullmatch(r'originals\.zip\.part[0-9]{4}',r['name'])
        assert 0<r['bytes']<=768*1024
        b=remote(base+'Y2021/'+r['name'],r['bytes'])
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['SHA256']
        (parts/r['name']).write_bytes(b)
        return r['bytes']
    with ThreadPoolExecutor(max_workers=4) as pool:part_bytes=sum(pool.map(obtain,index['parts']))
    assert part_bytes==index['package_bytes']
    package=output/'originals.zip'
    with package.open('xb') as out:
        for r in index['parts']:
            with (parts/r['name']).open('rb') as f:shutil.copyfileobj(f,out,1048576)
    assert sha(package)==index['package_SHA256']
    folder=output/'Y2021';folder.mkdir()
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        assert z.namelist()==[r['name'] for r in index['members']]
        assert len(set(z.namelist()))==len(z.namelist())
        for r in index['members']:
            info=z.getinfo(r['name']);assert info.file_size==r['bytes'] and info.compress_type==zipfile.ZIP_STORED
            path=folder/safe(r['name']);path.parent.mkdir(parents=True,exist_ok=True)
            with z.open(r['name']) as f,path.open('xb') as out:shutil.copyfileobj(f,out,1048576)
            assert sha(path)==r['SHA256']
    raw=json.loads((folder/'RAW_MANIFEST.json').read_text())
    for r in raw['records']:
        path=folder/safe(r['relative_raw_path']);assert path.stat().st_size==r['size'] and sha(path)==r['SHA256']
        assert Path(str(path)+'.CHECKSUM').read_text()==r['checksum_text']
        with zipfile.ZipFile(path) as z:assert z.testzip() is None and len(z.namelist())==1
    protocol=output/'protocol';protocol.mkdir()
    files=['PROTOCOL.json','ORIGINAL_SOURCE_MANIFEST.json','conditional_selector_inputs.py','conditional_selector_core.py','RECIPE_SOURCE_RECEIPT.json']
    protocol_hashes={}
    for name in files:
        b=remote(base+'protocol/'+name,250000);(protocol/name).write_bytes(b)
        protocol_hashes[name]=hashlib.sha256(b).hexdigest()
    assert protocol_hashes['PROTOCOL.json']==index['protocol_SHA256']
    assert protocol_hashes['ORIGINAL_SOURCE_MANIFEST.json']=='99f07ef591581a51babb0b4a8b3079310f24a8bfe0e91b09103c4a68ffa82130'
    assert protocol_hashes['conditional_selector_inputs.py']=='9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207'
    assert protocol_hashes['conditional_selector_core.py']=='c0a086ba583dfe4f059b8942988ec2209ac767e4cfe59699f06e804b94890533'
    references=index['cached_inputs'];feature=output/'FEATURE_ARCHIVE.zip'
    feature_body_bytes=0
    if cache:
        assert sha(cache)==references['archive_SHA256'] and cache.stat().st_size==references['archive_bytes']
        shutil.copyfile(cache,feature)
    else:
        feature_base=f'https://raw.githubusercontent.com/snowycat1234/coin/{references["immutable_commit"]}/{references["parts_prefix"]}'
        with feature.open('xb') as out:
            for r in references['original_index']['parts']:
                b=remote(feature_base+str(safe(r['file'])),r['bytes'])
                assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['SHA256']
                feature_body_bytes+=len(b);out.write(b)
    assert sha(feature)==references['archive_SHA256']
    with zipfile.ZipFile(feature) as z:
        assert z.testzip() is None
        for r in references['source_member_bindings']:
            assert hashlib.sha256(z.read(r['member'])).hexdigest()==r['SHA256']
    receipt=dict(schema='REMOTE2021_ECONOMIC_PACKET_READBACK_V1',status='ALL_REMOTE_PARTS_MEMBERS_ORIGINALS_AND_CACHED_SOURCE_BINDINGS_VERIFIED',
        checked_UTC=datetime.now(timezone.utc).isoformat(),source_commit=commit,index_SHA256=sha(output/'INDEX.json'),
        package_SHA256=sha(package),remote_parts=len(index['parts']),remote_part_body_bytes=part_bytes,
        every_part_and_package_and_member_SHA256_verified=True,outer_and_all_original_inner_ZIP_CRC_verified=True,
        original_archive_count=len(raw['records']),original_archive_bytes=sum(r['size'] for r in raw['records']),
        reused_feature_archive_SHA256=sha(feature),feature_archive_read_from_verified_cache=bool(cache),
        newly_read_public_feature_body_bytes=feature_body_bytes,protocol_file_SHA256=protocol_hashes,
        distinct_eligible_active_intervals=index['distinct_eligible_active_intervals'],paid_episode_count=index['paid_episode_count'],
        no_official_provider_redownloads=True,model_fits=0,model_inferences=0,backtests=0,wallets=0)
    (output/'RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cached-feature-archive',type=Path)
    a=p.parse_args();main(a.commit,a.output,a.cached_feature_archive)

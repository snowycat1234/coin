"""Recover the small adapter-ready wire packet with a reviewed exact index hash."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from recover import remote,safe

def main(commit,consumer_sha,output):
    assert re.fullmatch('[0-9a-f]{40}',commit) and re.fullmatch('[0-9a-f]{64}',consumer_sha)
    output.mkdir(exist_ok=False)
    base=f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/research/core5-2021-economic-data/consumer/'
    body=remote(base+'CONSUMER_INDEX.json',250000)
    assert hashlib.sha256(body).hexdigest()==consumer_sha
    (output/'CONSUMER_INDEX.json').write_bytes(body);index=json.loads(body)
    assert index['source_download_complete'] and index['official_archive_receipts_verified']
    assert index['symbols_order']==['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
    records=[index['economic_array']]+index['economic_table_artifacts']
    assert len(records)==16 and len(set(r['path'] for r in records))==16
    assert sum(r['bytes'] for r in records)<2*2**20
    def obtain(r):
        path=output/safe(r['path']);path.parent.mkdir(parents=True,exist_ok=True)
        assert r['bytes']<=768*1024
        b=remote(base+r['path'],r['bytes'])
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['SHA256']
        path.write_bytes(b)
        return dict(path=r['path'],bytes=len(b),SHA256=r['SHA256'])
    with ThreadPoolExecutor(max_workers=4) as pool:checked=list(pool.map(obtain,records))
    receipt=dict(status='ALL17_REMOTE_CONSUMER_FILES_MATCH_REVIEWED_EXACT_HASHES',checked_UTC=datetime.now(timezone.utc).isoformat(),
        source_commit=commit,consumer_SHA256=consumer_sha,economic_SHA256=index['economic_SHA256'],
        remote_files_including_index=17,remote_body_bytes=len(body)+sum(r['bytes'] for r in checked),verified=checked,
        actual_active_intervals=index['distinct_eligible_active_intervals'],paid_episode_count=index['paid_episode_count'],
        original_source_packet_commit=index['original_source_packet_commit'],official_provider_downloads=0,
        model_fits=0,scaler_fits=0,model_inferences=0,backtests=0,wallets=0)
    (output/'REMOTE_READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='verified'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit',required=True)
    p.add_argument('--consumer-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.commit,a.consumer_sha256,a.output)

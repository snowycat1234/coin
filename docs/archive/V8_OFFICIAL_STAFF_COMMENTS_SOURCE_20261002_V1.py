"""Read saved official-repository staff comments; fetch one small comment list."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import resource
import httpx

run=Path('/home/xflops/coin-state/v8-official-input-metadata-20261002-v1')
out=Path('/mnt/d/codex/coin/reports/fast_research/V8_OFFICIAL_STAFF_COMMENTS_20261002_V1.json')
assert not out.exists()
records=[]
for number in (372,437,447):
    path=run/f'official-repo-issue-{number}-comments.json'
    raw=path.read_bytes()
    items=json.loads(raw)
    staff=[{'html_url':i['html_url'],'author_association':i['author_association'],
            'body':i['body'],'body_sha256':hashlib.sha256(i['body'].encode()).hexdigest(),
            'created_at':i['created_at']} for i in items
            if i['author_association'] in ('MEMBER','OWNER','COLLABORATOR')]
    records.append({'issue':number,'saved_body_sha256':hashlib.sha256(raw).hexdigest(),'staff_comments':staff})
number=315
url=f'https://api.github.com/repos/binance/binance-public-data/issues/{number}/comments'
record={'issue':number,'url':url,'method':'GET','access_utc':datetime.now(UTC).isoformat()}
try:
    with httpx.Client(timeout=12,follow_redirects=False) as client:
        with client.stream('GET',url) as response:
            raw=bytearray()
            record['http_status']=response.status_code
            for piece in response.iter_bytes():
                assert len(raw)+len(piece)<=1_000_000,'small-doc limit exceeded'
                raw.extend(piece)
            raw=bytes(raw)
    record['body_sha256']=hashlib.sha256(raw).hexdigest()
    record['body_bytes']=len(raw)
    path=run/f'official-repo-issue-{number}-comments.json'
    with path.open('xb') as stream:stream.write(raw)
    record['local_path']=str(path)
    if record['http_status']==200:
        items=json.loads(raw)
        record['staff_comments']=[{'html_url':i['html_url'],'author_association':i['author_association'],
            'body':i['body'],'body_sha256':hashlib.sha256(i['body'].encode()).hexdigest(),
            'created_at':i['created_at']} for i in items
            if i['author_association'] in ('MEMBER','OWNER','COLLABORATOR')]
except Exception as error:
    record['error_type']=type(error).__name__
    record['error']=str(error)[:300]
records.append(record)
report={'status':'STAFF_COMMENT_EXTRACTION_ONLY','created_utc':datetime.now(UTC).isoformat(),
        'records':records,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
with out.open('x') as stream:json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps(report,ensure_ascii=False))

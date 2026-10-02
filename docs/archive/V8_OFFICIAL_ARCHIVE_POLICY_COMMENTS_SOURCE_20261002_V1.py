"""Two small official-repository comment lists, no market archive access."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import httpx

run=Path('/home/xflops/coin-state/v8-official-input-metadata-20261002-v1')
out=Path('/mnt/d/codex/coin/reports/fast_research/V8_OFFICIAL_ARCHIVE_POLICY_COMMENTS_20261002_V1.json')
assert not out.exists()
rows=[]
for number in (334,380):
    url=f'https://api.github.com/repos/binance/binance-public-data/issues/{number}/comments'
    row={'issue':number,'url':url,'method':'GET','access_utc':datetime.now(UTC).isoformat()}
    try:
        with httpx.Client(timeout=12,follow_redirects=False) as client:
            with client.stream('GET',url) as response:
                raw=bytearray()
                row['http_status']=response.status_code
                for piece in response.iter_bytes():
                    assert len(raw)+len(piece)<=1_000_000,'small-doc limit exceeded'
                    raw.extend(piece)
                raw=bytes(raw)
        row['body_sha256']=hashlib.sha256(raw).hexdigest()
        row['body_bytes']=len(raw)
        path=run/f'official-repo-issue-{number}-comments.json'
        with path.open('xb') as stream:stream.write(raw)
        row['local_path']=str(path)
        if row['http_status']==200:
            row['staff_comments']=[{'html_url':i['html_url'],'author_association':i['author_association'],
                'body':i['body'],'body_sha256':hashlib.sha256(i['body'].encode()).hexdigest(),
                'created_at':i['created_at']} for i in json.loads(raw)
                if i['author_association'] in ('MEMBER','OWNER','COLLABORATOR')]
    except Exception as error:
        row['error_type']=type(error).__name__
        row['error']=str(error)[:300]
    rows.append(row)
report={'status':'ARCHIVE_POLICY_STAFF_COMMENTS_ONLY','created_utc':datetime.now(UTC).isoformat(),'records':rows}
with out.open('x') as stream:json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps(report,ensure_ascii=False))

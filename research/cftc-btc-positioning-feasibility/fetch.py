"""One bounded official-source acquisition cache; refuse access denials and retries."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from urllib.parse import urlparse

BUDGET = 30 * 1024 * 1024
PUBLIC_HEADERS = {'date', 'content-type', 'content-length', 'cache-control', 'server-timing', 'server', 'cf-ray'}


def fetch(root, name, url, limit):
    if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'www.cftc.gov':
        raise ValueError('Only direct official www.cftc.gov sources are permitted')
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / 'ACQUISITION.json'
    records = json.loads(manifest.read_text()) if manifest.exists() else []
    if any(x['name'] == name or x['url'] == url for x in records):
        raise ValueError('Already attempted: reuse recorded bytes or respect its access failure')
    if any(x.get('status') in (401, 403, 451) for x in records):
        raise ValueError('Official host access denied; no bypass or further direct attempts')
    spent = sum(x['downloaded_body_bytes'] for x in records)
    if not 0 < limit <= BUDGET - spent:
        raise ValueError('Insufficient remaining 30 MiB budget for declared maximum')
    record = dict(name=name, url=url, maximum_body_bytes=limit,
                  requested_UTC=datetime.now(timezone.utc).isoformat())
    try:
        response = urlopen(url, timeout=30)
    except HTTPError as exc:
        response = exc
    try:
        with response:
            record.update(status=response.status, final_url=response.geturl(),
                          headers={k.lower():v for k,v in response.headers.items() if k.lower() in PUBLIC_HEADERS},
                          headers_policy='Public diagnostic allowlist; cookies and other headers omitted')
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError('Response exceeds bounded body limit')
            path = root / name
            path.write_bytes(data)
            record.update(downloaded_body_bytes=len(data), body_SHA256=hashlib.sha256(data).hexdigest(),
                          fetched_UTC=datetime.now(timezone.utc).isoformat())
    except BaseException:
        record.setdefault('downloaded_body_bytes', 0)
        record['outcome'] = 'FAILED_NOT_VERIFIED'
        records.append(record)
        manifest.write_text(json.dumps(records, indent=2) + '\n')
        raise
    record['outcome'] = 'ORIGINAL_HTTP_BODY_SAVED' if record['status'] == 200 else 'OFFICIAL_HTTP_ERROR_SAVED_NO_BYPASS'
    records.append(record)
    manifest.write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps({k:v for k,v in record.items() if k != 'headers'}), flush=True)
    if record['status'] != 200:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--limit', type=int, required=True)
    args = parser.parse_args()
    fetch(args.root, args.name, args.url, args.limit)

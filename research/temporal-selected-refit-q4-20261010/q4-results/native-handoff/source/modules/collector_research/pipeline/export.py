from __future__ import annotations
import json
import shutil
import zipfile
from pathlib import Path
from .common import E, REPORTS, WORK, disk_guard, dump, sha256
from .download import verify_local
from .normalize import verify_dataset

VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""Run after extracting coin_dataset_*.zip: python verify_bundle.py"""
import hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'BUNDLE_MANIFEST.json').read_text())
for item in manifest['files']:
    p=(root/item['relative_path']).resolve()
    if not p.is_relative_to(root) or not p.is_file(): raise SystemExit('Missing/unsafe path: '+item['relative_path'])
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    if p.stat().st_size != item['bytes'] or h.hexdigest() != item['sha256']:
        raise SystemExit('Corrupt/missing file: '+item['relative_path'])
print('PASS:',len(manifest['files']),'files; source availability only, not native execution certification')
'''


def export_dataset(destination: Path | None = None, include_raw: bool = False) -> Path:
    manifest = verify_dataset()
    entries = []
    for item in manifest['artifacts']:
        entries.append((WORK / item['relative_path'], item['relative_path'], item['role']))
    for name in ('DATASET_MANIFEST.json', 'data_audit.csv', 'data_audit.json', 'COLLECTOR_REPORT.md'):
        p = REPORTS / name
        if p.exists():
            entries.append((p, f'reports/{name}', 'manifest_or_report'))
    if include_raw:
        seen = set()
        for receipt in manifest['source_receipts']:
            for source in receipt.get('sources', []):
                p = Path(source['path'])
                if str(p) in seen:
                    continue
                seen.add(str(p))
                verify_local(p)
                target = f'data/raw/{receipt["family"]}/{receipt["symbol"]}/{p.name}'
                entries.extend([(p, target, 'raw_archive'), (Path(str(p) + '.CHECKSUM'), target + '.CHECKSUM', 'official_checksum')])
    destination = destination or WORK / 'exports' / ('coin_dataset_' + manifest['date_range']['end_inclusive'] + '.zip')
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError('Export already exists; choose a new path. No silent overwrite.')
    required = sum(p.stat().st_size for p, _, _ in entries) + 1_000_000
    disk_guard(required)
    if shutil.disk_usage(destination.parent).free - required < float(E('MIN_FREE_GIB')) * 2**30:
        raise RuntimeError('Insufficient free space at the export destination')
    tmp = destination.with_suffix('.zip.part')
    inventory = dict(schema='coin-portable-dataset-v1', includes_raw=include_raw,
                     native_repository_acceptance=False, private_credentials_included=False,
                     files=[dict(relative_path=name, role=role, bytes=p.stat().st_size, sha256=sha256(p)) for p, name, role in entries])
    try:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as z:
            for p, name, _ in entries:
                z.write(p, name)
            z.writestr('BUNDLE_MANIFEST.json', json.dumps(inventory, ensure_ascii=False, indent=2))
            z.writestr('verify_bundle.py', VERIFY_SCRIPT)
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)
    dump(dict(path=str(destination), bytes=destination.stat().st_size, sha256=sha256(destination),
              includes_raw=include_raw), REPORTS / 'LAST_EXPORT.json')
    return destination

#!/usr/bin/env python3
"""Reassemble the local public research ZIP after validating every part."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    artifact = json.loads((root / 'ARTIFACT.json').read_text())
    bodies = []
    for part in artifact['parts']:
        path = root / part['path']
        body = path.read_bytes()
        assert len(body) == part['bytes'], part['path']
        assert len(body) <= 768 * 1024, part['path']
        assert hashlib.sha256(body).hexdigest() == part['sha256'], part['path']
        bodies.append(body)
    data = b''.join(bodies)
    assert len(data) == artifact['bytes']
    assert hashlib.sha256(data).hexdigest() == artifact['sha256']
    filename = artifact['filename']
    assert Path(filename).name == filename and filename.endswith('.zip')
    target = root / filename
    if target.exists():
        assert target.read_bytes() == data, 'Existing output differs; choose a clean --root directory.'
    else:
        target.write_bytes(data)
    print('PASS:', filename, len(data), 'bytes', artifact['sha256'])

if __name__ == '__main__':
    main()

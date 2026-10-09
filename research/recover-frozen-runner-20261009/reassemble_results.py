"""Verify published ordered result parts and recover the portable package."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent / "comparison86")
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads((args.root / "ARTIFACT.json").read_bytes())
    parts = []
    for p in spec["parts"]:
        data = (args.root / p["path"]).read_bytes()
        if len(data) != p["bytes"] or hashlib.sha256(data).hexdigest() != p["sha256"]:
            raise ValueError("Published part identity differs")
        parts.append(data)
    data = b"".join(parts)
    if len(data) != spec["bytes"] or hashlib.sha256(data).hexdigest() != spec["sha256"]:
        raise ValueError("Published result archive differs")
    args.destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if z.testzip() is not None:
            raise ValueError("Result archive CRC differs")
        for n in z.namelist():
            p = PurePosixPath(n)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError("Portable relative archive members required")
            if n.endswith('/'):
                continue
            dest = args.destination.joinpath(*p.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                stream.write(z.read(n))
    manifest = json.loads((args.destination / "RESULT_MEMBER_HASHES.json").read_bytes())
    for f in manifest['files']:
        data = (args.destination / f['path']).read_bytes()
        if len(data) != f['bytes'] or hashlib.sha256(data).hexdigest() != f['sha256']:
            raise ValueError("Result member identity differs")
    print(json.dumps(dict(status='PASS', sha256=spec['sha256'], verified_files=len(manifest['files']))))

if __name__ == '__main__':
    main()

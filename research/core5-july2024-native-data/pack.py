"""Pack verified original bytes and compact execution/funding inputs in <=768 KiB parts."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

PART_BYTES = 768 * 1024


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(root, destination, fold):
    source = root / fold
    raw = json.loads((source / 'RAW_MANIFEST.json').read_text())
    validation = json.loads((source / 'VALIDATION.json').read_text())
    if not validation['execution_and_held_funding_ready']:
        raise ValueError('All 63 execution prices and 62 held funding intervals required before publication')
    members = []
    for record in raw['records']:
        path = source / record['relative_raw_path']
        if sha(path) != record['SHA256'] or path.stat().st_size != record['size']:
            raise ValueError('Raw source changed after validation')
        members.extend([path, Path(str(path) + '.CHECKSUM')])
    members.extend([source / 'RAW_MANIFEST.json', source / 'VALIDATION.json'])
    for artifact in validation['derived_artifacts']:
        if artifact['role'] not in ('klines_native_minute','markPriceKlines_native_minute'):
            path=source/artifact['path']
            if sha(path)!=artifact['SHA256']:
                raise ValueError('Derived economic input changed')
            members.append(path)
    package = root / (fold + '-originals.zip')
    metadata = []
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in members:
            name = str(path.relative_to(source))
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
            metadata.append(dict(name=name, bytes=path.stat().st_size, SHA256=sha(path)))
    target = destination / fold
    target.mkdir(parents=True, exist_ok=False)
    parts = []
    with package.open('rb') as stream:
        i = 0
        while chunk := stream.read(PART_BYTES):
            name = f'originals.zip.part{i:04d}'
            (target / name).write_bytes(chunk)
            parts.append(dict(name=name, bytes=len(chunk), SHA256=hashlib.sha256(chunk).hexdigest()))
            i += 1
    index = dict(schema='CORE5_NATIVE_MINUTE_ORIGINALS_PARTS_V1', fold=fold,
        status=validation['status'], interval_UTC_start_inclusive=validation['interval_UTC_start_inclusive'],
        interval_UTC_end_exclusive=validation['interval_UTC_end_exclusive'],
        original_archive_count=raw['archive_count'], original_compressed_bytes=raw['total_original_compressed_bytes'],
        maximum_part_bytes=PART_BYTES, package_bytes=package.stat().st_size, package_SHA256=sha(package),
        parts=parts, members=metadata, compression='ZIP_STORED wrapper, original exchange ZIP bytes unchanged',
        native_minute_Parquets_published=False, normalized_economic_Parquets_published=True,
        primitive_daily_feature_tables_published=False,
        execution_and_held_funding_ready=validation['execution_and_held_funding_ready'],
        native_minute_grid_complete=validation['native_minute_grid_complete'],
        coverage=validation['coverage'], protocol_commit=validation['protocol_commit'],
        protocol_SHA256=validation['protocol_SHA256'], paid_close_UTC=validation['paid_close_UTC'],
        economics_array_path='ECONOMICS.npz',
        normalization_source_commit=validation['normalization_source_commit'],
        normalization_source_SHA256=validation['normalization_source_SHA256'])
    (target / 'INDEX.json').write_text(json.dumps(index, indent=2) + '\n')
    print(json.dumps({k:v for k,v in index.items() if k not in ('parts','members')}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--fold', choices=['JULY2024'], required=True)
    args = p.parse_args()
    main(args.root, args.destination, args.fold)

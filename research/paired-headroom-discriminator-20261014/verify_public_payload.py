"""Identity-only public gate; no downloads or candidate/account imports."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

HERE = Path(__file__).resolve().parent
SCIENCE_SHA = '11d645f59e1cdec1ee141517d550d514a8ffcbe196ddaf27cfede17b589c9f98'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('Unsafe relative metadata path')
    return Path(*p.parts)


def verify(expected_manifest_sha256, external_pins=False):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_manifest_sha256):
        raise ValueError('A trusted public manifest SHA256 is required')
    manifest_path = HERE / 'PUBLIC_PAYLOAD_MANIFEST.json'
    if sha(manifest_path) != expected_manifest_sha256:
        raise ValueError('Public manifest identity mismatch')
    manifest = json.loads(manifest_path.read_text())
    if manifest['scientific_source_manifest_SHA256'] != SCIENCE_SHA:
        raise ValueError('Scientific identity mismatch')
    for name, expected in manifest['files_SHA256'].items():
        if sha(HERE / relative(name)) != expected:
            raise ValueError('Public file identity mismatch: ' + name)
    if sha(HERE / 'SOURCE_MANIFEST.json') != SCIENCE_SHA:
        raise ValueError('Scientific manifest identity mismatch')
    science = json.loads((HERE / 'SOURCE_MANIFEST.json').read_text())
    for name, expected in science['files_SHA256'].items():
        if manifest['files_SHA256'].get(name) != expected:
            raise ValueError('Scientific file omitted or changed: ' + name)
    catalog = json.loads((HERE / 'EXTERNAL_CODE_PIN_CATALOG.json').read_text())
    pins = json.loads((HERE / 'SOURCE_PINS.json').read_text())
    root = pins['read_source_root']
    expected_destinations = {root + '/FROZEN_CODE.json': pins['frozen_manifest_SHA256']}
    expected_destinations.update({root + '/' + k: v for k, v in pins['original_files_SHA256'].items()})
    expected_destinations.update({root + '/runtime_dependencies/' + k: v for k, v in pins['executor_dependencies_SHA256'].items()})
    expected_destinations[pins['terminal60_source']['path']] = pins['terminal60_source']['SHA256']
    observed = {}
    for row in catalog['files']:
        destination = row['destination_relative_to_module_parent']
        relative(destination)
        relative(row['path'])
        if row['repository'] != 'snowycat1234/coin' or not re.fullmatch(r'[0-9a-f]{40}', row['commit']):
            raise ValueError('Unexpected immutable repository locator')
        if destination in observed:
            raise ValueError('Duplicate external destination')
        observed[destination] = row['SHA256']
        if external_pins and sha(HERE.parent / relative(destination)) != row['SHA256']:
            raise ValueError('External code pin mismatch: ' + destination)
    if observed != expected_destinations or len(observed) != 11:
        raise ValueError('External catalog does not exactly cover original pins')
    # The frozen original source preflight does the same pure-code AST gate.
    forbidden_imports = {'quant', 'scripts', 'polars', 'pandas', 'requests', 'urllib', 'http', 'socket'}
    forbidden_calls = {'load', 'read_bytes', 'read_text', 'open', 'execute_fill', 'apply_funding',
                       'update_marks', 'advance_day', 'from_snapshot', 'schedule', 'attempt'}
    for name in ('paired_buffer.py', 'run_toy.py'):
        tree = ast.parse((HERE / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or '']
            else:
                imports = []
            if any(item.split('.')[0] in forbidden_imports for item in imports):
                raise ValueError('Forbidden pure-code import')
            if isinstance(node, ast.Call) and ast.unparse(node.func).split('.')[-1] in forbidden_calls:
                raise ValueError('Forbidden pure-code call')
    return {'status': 'PASS_PUBLIC_IDENTITY_AND_PURE_CODE_AST',
            'public_manifest_SHA256': expected_manifest_sha256,
            'scientific_source_manifest_SHA256': SCIENCE_SHA,
            'public_files_verified': len(manifest['files_SHA256']),
            'external_code_pins_verified': 11 if external_pins else 0,
            'catalog_code_pins_exactly_covered': 11,
            'candidate_imports': 0, 'historical_array_reads': 0, 'wallets': 0,
            'downloads': 0, 'historical_GO': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--external-pins', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.expected_manifest_sha256, args.external_pins), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

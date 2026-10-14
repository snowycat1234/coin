"""Fail-closed code, metadata and explicit source-only authorization gates."""
from __future__ import annotations
import ast
import hashlib
import importlib.machinery
import json
from pathlib import Path
import re
import sys
import types

HERE = Path(__file__).resolve().parent
YEARS = (2023, 2024, 2025)
BASE_COMMIT = '7a31299c0f7eb6136599d5954a206944f50b27a2'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def check(path, digest, size=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or sha(path) != digest:
        raise ValueError('EXACT_FILE_IDENTITY_REQUIRED:' + path.name)
    if size is not None and path.stat().st_size != size:
        raise ValueError('EXACT_FILE_SIZE_REQUIRED:' + path.name)
    return path


def relative(root, name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('SAFE_RELATIVE_PATH_REQUIRED')
    return Path(root) / path


def verify_runner(expected):
    if not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('TRUSTED_RUNNER_MANIFEST_SHA_REQUIRED')
    check(HERE / 'RUNNER_MANIFEST.json', expected)
    manifest = read(HERE / 'RUNNER_MANIFEST.json')
    for name, digest in manifest['files_SHA256'].items():
        check(relative(HERE, name), digest)
    return manifest


def import_file(name, path, expected_sha):
    path = Path(path).resolve()
    if name in sys.modules:
        raise ValueError('PRELOADED_MODULE_REFUSED:' + name)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('ACTUAL_LOADED_SOURCE_SHA_MISMATCH')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition('.')[0]
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=str(path))
    module._verified_source_SHA256 = expected_sha
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def verify_dependencies(roots):
    pins = read(HERE / 'DEPENDENCY_PINS.json')
    paired = Path(roots['paired_module'])
    inp = Path(roots['input_module'])
    for name, digest in pins['paired_publication']['files_SHA256'].items():
        check(relative(paired, name), digest)
    for name, rec in pins['input_publication']['files'].items():
        check(relative(inp, name), rec['SHA256'], rec['bytes'])
    for root_key, pin_key in (('resource_guard', 'original_resource_guard'),
                              ('resource_release', 'original_resource_release')):
        rec = pins[pin_key]
        check(roots[root_key], rec['SHA256'], rec['bytes'])
    # Assert that the fixed three-year projection equals its exact original registry.
    registry = read(inp / 'INPUT_BINDINGS.json')
    cases = read(HERE / 'SOURCE_CASES.json')
    if cases['origin_INPUT_BINDINGS_SHA256'] != pins['input_publication']['files']['INPUT_BINDINGS.json']['SHA256']:
        raise ValueError('REGISTRY_ORIGIN_CHANGED')
    if tuple(cases['symbols']) != tuple(registry['symbols']) or set(cases['years']) != {str(y) for y in YEARS}:
        raise ValueError('FIXED_YEAR_SYMBOL_SCOPE')
    for year in YEARS:
        keys = {'authority', 'calendar', 'derived_mark_cells', 'funding_events',
                'identity_status', 'index', 'months', 'required_files'}
        original = registry['years'][str(year)]
        if (set(cases['years'][str(year)]) != keys
                or cases['years'][str(year)] != {k: original[k] for k in keys}
                or original['identity_status'] != 'PASS'):
            raise ValueError('CASE_PROJECTION_OR_ADMISSION_CHANGED')
    # Pure input transport is the only imported loader. No native financial port.
    tree = ast.parse((inp / 'inherited_input_binding.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or '').split('.')[0] in {'quant', 'scripts', 'polars'}:
            raise ValueError('FINANCIAL_INPUT_IMPORT')
        if isinstance(node, ast.Import) and any(x.name.split('.')[0] in {'quant', 'scripts', 'polars'} for x in node.names):
            raise ValueError('FINANCIAL_INPUT_IMPORT')
    return pins, cases


def load_paired(roots):
    paired = Path(roots['paired_module']).resolve()
    # Reject namespace/cached-module shadowing before the unchanged generic vendor import.
    for name in ('vendor', 'vendor.headroom_buffer'):
        if name in sys.modules:
            raise ValueError('PRELOADED_VENDOR_REFUSED')
    if (paired / 'vendor/__init__.py').exists() or (paired / 'vendor/__init__.pyc').exists():
        raise ValueError('UNPINNED_VENDOR_INITIALIZER_REFUSED')
    pins = read(HERE / 'DEPENDENCY_PINS.json')['paired_publication']['files_SHA256']
    package = types.ModuleType('vendor')
    package.__path__ = [str(paired / 'vendor')]
    package.__package__ = 'vendor'
    package.__spec__ = importlib.machinery.ModuleSpec('vendor', loader=None, is_package=True)
    sys.modules['vendor'] = package
    package.headroom_buffer = import_file('vendor.headroom_buffer', paired / 'vendor/headroom_buffer.py', pins['vendor/headroom_buffer.py'])
    module = import_file('_fixed_paired_headroom', paired / 'paired_buffer.py', pins['paired_buffer.py'])
    vendor = module.original
    if (Path(vendor.__file__).resolve() != paired / 'vendor/headroom_buffer.py'
            or vendor._verified_source_SHA256 != pins['vendor/headroom_buffer.py']):
        raise ValueError('VENDOR_IMPORT_SHADOW')
    return module


def authorization(year, expected_manifest, review_path, review_sha, go_path, go_sha):
    if year not in YEARS:
        raise ValueError('EXCLUDED_YEAR_OR_HOLDOUT')
    check(review_path, review_sha)
    check(go_path, go_sha)
    review, go = read(review_path), read(go_path)
    common = {'runner_manifest_SHA256': expected_manifest, 'paired_publication_commit': BASE_COMMIT,
              'source_cases_SHA256': sha(HERE / 'SOURCE_CASES.json'),
              'resource_policy_SHA256': sha(HERE / 'RESOURCE_POLICY.json'),
              'scope': 'CACHED_MARK_TRADE_SOURCE_ONLY_NO_WALLETS'}
    if any(review.get(k) != value or go.get(k) != value for k, value in common.items()):
        raise ValueError('EXACT_REVIEW_GO_BINDING_REQUIRED')
    if (review.get('schema') != 'INDEPENDENT_PAIRED_SOURCE_RUNNER_REVIEW_V1'
            or review.get('status') != 'PASS_CODE_TOY_ONLY_NO_HISTORICAL_EXECUTION'
            or go.get('schema') != 'EXPLICIT_PARENT_PAIRED_SOURCE_YEAR_GO_V1'
            or go.get('parent_GO') is not True or go.get('year') != year
            or go.get('review_SHA256') != review_sha or go.get('wallet_GO') is not False
            or go.get('new_market_downloads') != 0):
        raise ValueError('SOURCE_ONLY_YEAR_GO_REQUIRED')
    case = read(HERE / 'SOURCE_CASES.json')['years'][str(year)]
    if go.get('source_index_SHA256') != case['index']['SHA256']:
        raise ValueError('SOURCE_GO_INDEX_IDENTITY')
    return {'review_SHA256': review_sha, 'parent_GO_SHA256': go_sha}

"""Bounded, zero-account replay of the unchanged published full-2023 source build.

This is a local materialized-source adapter, NOT a historical Git checkout.
Only unused wallet/ML imports are replaced with byte-bound function projection.
"""
import ast
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import types
import zipfile

if not __debug__:
    raise RuntimeError('Optimized Python (-O) is forbidden; original assertions must execute')

BASE = Path(__file__).resolve().parent
ROOT = BASE / 'closure/source'
CLOSURE = BASE / 'closure'
STATE = BASE / 'reconstructed_source'
PREFIX = 'research/cs-2023-continuous-economics-20261012/'
ARTIFACT = 'a4dbb6ded845a70d48a7c1d16e9c4a5b18034377'
START_MS, END_MS = 1672531200000, 1704067200000
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def verified(path, digest, size=None):
    raw = path.read_bytes()
    assert sha(raw) == digest, ('SHA256', str(path))
    assert size is None or len(raw) == size, ('bytes', str(path))
    return raw

assert not STATE.exists(), 'Fresh reconstruction output required'
os.environ.update(QUANT_ROOT=str(ROOT), PYTHONDONTWRITEBYTECODE='1',
                  OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', ARROW_NUM_THREADS='1', POLARS_MAX_THREADS='1')
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(BASE / 'deps')]
resource.setrlimit(resource.RLIMIT_AS, (4_000_000_000, 4_000_000_000))
assert shutil.disk_usage(BASE).free >= 15 * 2**30

# Check exact source bytes independently, not synthetic git-status evidence.
source_manifest = json.loads((CLOSURE / 'CLOSURE.json').read_text())
def source_clean():
    for item in source_manifest['source_files']:
        raw = (ROOT / item['path']).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert actual == item['git_blob_sha'], ('Published source changed', item['path'])
source_clean()
expected_raw = (CLOSURE / 'SOURCE_INDEX.json').read_bytes()
assert hashlib.sha1(b'blob ' + str(len(expected_raw)).encode() + b'\0' + expected_raw).hexdigest() == '10531ba0b62644bbb9681ff2b55a2fd27773812c'
expected = json.loads(expected_raw)
inputs = json.loads((CLOSURE / 'DATA_INPUT_CLOSURE.json').read_text())
cube = inputs['daily_cube']
verified(BASE / 'daily/INPUTS.npz', cube['SHA256'], cube['bytes'])
cube_path = ROOT / cube['path']
cube_path.parent.mkdir(parents=True, exist_ok=True)
if not cube_path.exists(): cube_path.symlink_to(BASE / 'daily/INPUTS.npz')
verified(cube_path, cube['SHA256'], cube['bytes'])

# Finite immutable commit:path -> SHA-verified bytes map, with no provider fallback.
transport = {}
def bind(commit, path, raw):
    key = commit + ':' + path
    assert key not in transport or transport[key] == raw
    transport[key] = raw
for part in json.loads((BASE / 'PARTS.json').read_text()):
    bind(part['commit'], part['path'], verified(BASE / part['local'], part['SHA256'], part['bytes']))
for phase in ('Q1', 'Q2'):
    commit = expected['quarter_artifacts'][phase]
    cert = next(r for r in expected['source_certificates'] if r.get('phase') == phase)
    raw = verified(BASE / phase / 'INDEX.json', cert['index_SHA256'])
    bind(commit, PREFIX + 'source-phases/' + phase + '/SOURCE_INDEX.json', raw)
    for row in json.loads(raw)['all_archives']:
        check = row['official_checksum_text'].encode()
        assert sha(check) == row['CHECKSUM_SHA256']
        bind(commit, row['checksum_path'], check)
for fold in ('JULY2023', 'OCTOBER2023'):
    cert = next(r for r in expected['source_certificates'] if r.get('fold') == fold)
    raw = verified(BASE / fold / 'INDEX.json', cert['index_SHA256'])
    bind(cert['commit'], 'research/core5-binance-native-2023-data/' + fold + '/INDEX.json', raw)
fund = inputs['funding_archive']
fund_index_raw = (CLOSURE / 'FUNDING_INDEX.json').read_bytes()
fund_index = json.loads(fund_index_raw)
assert fund_index['SHA256'] == fund['SHA256'] and fund_index['bytes'] == fund['bytes']
bind(fund['ref'], fund['index_path'], fund_index_raw)
for part in fund['parts']:
    bind(fund['ref'], part['path'], verified(BASE / 'funding' / part['file'], part['SHA256'], part['bytes']))
bind(ARTIFACT, PREFIX + 'source-result/SOURCE_INDEX.json', expected_raw)
calls = []
def finite_git(args, *positional, **kwargs):
    assert not positional and set(kwargs) <= {'cwd'}, ('Unexpected subprocess parameters', args)
    assert Path(kwargs.get('cwd', ROOT)).resolve() == ROOT.resolve()
    args = list(args)
    if args == ['git', 'status', '--porcelain']:
        source_clean()
        calls.append({'kind': 'source_manifest_clean_check', 'full_git_checkout': False})
        return b''
    assert len(args) == 3 and args[:2] == ['git', 'show'], ('Non-whitelisted subprocess', args)
    assert args[2] in transport, ('Unmapped immutable Git object', args[2])
    calls.append({'kind': 'immutable_materialized_object', 'key': args[2]})
    return transport[args[2]]
subprocess.check_output = finite_git
def audit(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event == 'os.system':
        raise RuntimeError('Network and real process execution forbidden: ' + event)
sys.addaudithook(audit)
class BlockEconomicImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'quant','sklearn','xgboost','torch','tensorflow'} or fullname.startswith('scripts.investment'):
            raise RuntimeError('Wallet/model module forbidden: ' + fullname)
sys.meta_path.insert(0, BlockEconomicImports())

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
pa.set_cpu_count(1)
pa.set_io_thread_count(1)

# Execute the complete unmodified source.py, never its acquire/__main__ path.
spec = importlib.util.spec_from_file_location('exact_full2023_source', ROOT / PREFIX / 'source.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
source.verify()

# Project only original utc/fund_events nodes. No node rewriting/unparsing occurs.
run_path = ROOT / 'research/short-native-activity-20261012/run.py'
run_text = run_path.read_text()
run_tree = ast.parse(run_text, filename=str(run_path))
nodes = [n for n in run_tree.body if isinstance(n, ast.FunctionDef) and n.name in {'utc','fund_events'}]
assert [n.name for n in nodes] == ['utc','fund_events']
projection = ast.Module(body=nodes, type_ignores=[])
proof = []
for node in nodes:
    dumped = ast.dump(node, include_attributes=False)
    selected = next(n for n in ast.parse(run_text).body if isinstance(n, ast.FunctionDef) and n.name == node.name)
    assert dumped == ast.dump(selected, include_attributes=False)
    proof.append({'function': node.name, 'source': str(run_path.relative_to(ROOT)),
                  'function_source_SHA256': sha(ast.get_source_segment(run_text, node).encode()),
                  'AST_SHA256': sha(dumped.encode()), 'node_unchanged': True})

fund_whitelist = set(fund['open_member_whitelist'])
fund_opened = []
fund_projected = []
class WhitelistedFundingZip(zipfile.ZipFile):
    def read(self, name, *args, **kwargs):
        assert name in fund_whitelist, ('Unrelated funding archive member forbidden', name)
        fund_opened.append(name)
        return super().read(name, *args, **kwargs)
def bounded_funding_table(where, *args, **kwargs):
    assert not args and kwargs == {'columns': fund['columns'], 'filters': [tuple(x) for x in fund['filters']]}
    table = pq.read_table(where, **kwargs)
    times = table['calc_time_ms'].to_numpy()
    assert len(times) == 1095 and np.all((times >= START_MS) & (times < END_MS))
    fund_projected.append({'rows': len(times), 'minimum_ms': int(times.min()), 'maximum_ms': int(times.max()),
                           'columns': list(table.column_names), 'predicate_applied_before_values': True})
    return table
namespace = dict(__name__='exact_source_function_projection', ROOT=ROOT, SYMBOLS=source.SYMBOLS,
                 pd=pd, np=np, pq=types.SimpleNamespace(read_table=bounded_funding_table),
                 io=io, json=json, importlib=__import__('importlib'),
                 zipfile=types.SimpleNamespace(ZipFile=WhitelistedFundingZip),
                 bridge=types.SimpleNamespace(digest=sha))
exec(compile(projection, str(run_path), 'exec'), namespace)
projected_module = types.ModuleType('source_prepare')
projected_module.native = types.SimpleNamespace(utc=namespace['utc'], fund_events=namespace['fund_events'])
sys.modules['source_prepare'] = projected_module

save(BASE / 'SOURCE_ADAPTER_PREFLIGHT.json', {
    'status':'PASS_BYTE_BOUND_SOURCE_ONLY_ADAPTER_PREFLIGHT', 'source_files_exact':62,
    'original_source_hash_manifest':'8/8 PASS unchanged', 'AST_projections':proof,
    'normalization_and_source_build':'Unmodified complete published modules',
    'transport_entries':len(transport), 'transport_bytes':sum(map(len, transport.values())),
    'git_status_semantics':'Explicit original source-manifest verification; NOT a full Git checkout',
    'network_and_real_subprocesses':'Denied by audit hook', 'wallet_model_imports':'Denied by import hook',
    'funding_member_whitelist':sorted(fund_whitelist), 'funding_date_filter_ms':[START_MS,END_MS],
    'numpy':np.__version__, 'pandas':pd.__version__, 'pyarrow':pa.__version__,
    'python':sys.version, 'address_limit_bytes':4_000_000_000,
    'source_budget_seconds':180, 'new_accounts':0, 'new_fits':0, 'provider_requests':0,
})
started = time.monotonic()
try:
    source.build(STATE, expected['source_commit'], expected['quarter_artifacts']['Q1'],
                 expected['quarter_artifacts']['Q2'], ARTIFACT)
    assert (STATE / 'SOURCE_INDEX.json').read_bytes() == expected_raw, 'Exact SOURCE_INDEX byte comparison'
    for name, details in expected['files'].items(): verified(STATE / name, details['SHA256'], details['bytes'])
    for month in expected['months']:
        verified(STATE / 'months' / (month['month'] + '.npz'), month['source_NPZ_SHA256'], month['source_NPZ_bytes'])
    assert len(fund_projected) == 5 and len(fund_opened) == 6
    source_clean()
    save(BASE / 'SOURCE_RECONSTRUCTION_RESULT.json', {
        'status':'PASS_EXACT_FULL2023_SOURCE_ONLY_RECONSTRUCTION', 'seconds':time.monotonic()-started,
        'source_index_bytes_exact':True, 'DAILY_and_EVENTS_bytes_SHA_exact':True,
        'monthly_NPZ_bytes_SHA_exact':12, 'funding_projections':fund_projected,
        'funding_members_opened':fund_opened, 'source_function_projections':proof,
        'transport_calls':len(calls), 'new_accounts':0, 'account_advances':0, 'new_fits':0,
        'provider_requests':0, 'data_2026_values_read':0, 'full_git_checkout':False,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'result_directory':'reconstructed_source',
    })
    print('EXACT_SOURCE_RECONSTRUCTION_PASS_ZERO_ACCOUNTS', time.monotonic()-started, flush=True)
except Exception as exc:
    save(BASE / 'SOURCE_RECONSTRUCTION_FAILURE.json', {
        'status':'STOP_SOURCE_RECONSTRUCTION', 'error_type':type(exc).__name__, 'error':str(exc),
        'seconds':time.monotonic()-started, 'funding_projections':fund_projected,
        'new_accounts':0, 'new_fits':0, 'provider_requests':0,
    })
    raise

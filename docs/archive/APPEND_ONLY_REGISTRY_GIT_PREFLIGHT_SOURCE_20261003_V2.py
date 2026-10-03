import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')


def run(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=ROOT)


aliases = {}
for name in sys.argv[2:]:
    for item in json.loads((ROOT / name).read_text()).get('historical_source_aliases', []):
        allowed = {
            'docs/OPEN_SOURCE_REGISTRY.md': 'docs/archive/OPEN_SOURCE_REGISTRY_',
            'third_party/ts2vec/UPSTREAM.md': 'third_party/ts2vec/UPSTREAM_FR68_CORE_20261001.md',
        }
        if item['original_path'] not in allowed:
            raise ValueError('Only the evolving registry and dated TS2Vec provenance document may resolve to an archive')
        key = (item['original_path'], item['original_sha256'])
        archive = item['archive_path']
        if not archive.startswith(allowed[item['original_path']]):
            raise ValueError('Unexpected historical provenance archive path')
        if hashlib.sha256((ROOT / archive).read_bytes()).hexdigest() != key[1]:
            raise ValueError('Historical registry archive bytes differ')
        if key in aliases and aliases[key] != archive:
            raise ValueError('Conflicting archive resolution')
        aliases[key] = archive
expected = {}
for name in sys.argv[2:]:
    receipt = json.loads((ROOT / name).read_text())
    expected[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    for field in ('source_hashes', 'verified_prior_files'):
        for key, value in receipt.get(field, {}).items():
            key = aliases.get((key, value), key)
            if key in expected and expected[key] != value:
                raise ValueError('Conflicting frozen binding: ' + key)
            expected[key] = value

patterns = (
    re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})'),
    re.compile(rb'AKIA[0-9A-Z]{16}'),
    re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
)
names = run('ls-files', '-z').decode().split('\0')[:-1]
changed = run('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]
if any('\n' in name or '\r' in name for name in names):
    raise ValueError('Unexpected line-bearing Git path')
requested = ''.join(':' + name + '\n' for name in names).encode()
packed = subprocess.check_output(['git', 'cat-file', '--batch'], input=requested, cwd=ROOT)
position = 0
total, matched = 0, {}
for name in names:
    end_header = packed.index(b'\n', position)
    fields = packed[position:end_header].split()
    if len(fields) != 3 or fields[1] != b'blob':
        raise ValueError('Staged blob lookup failed: ' + name)
    size = int(fields[2])
    if size > (8_000_000 if name == 'reports/experiment_registry.jsonl' else 4_000_000):
        raise ValueError('Oversize staged artifact: ' + name)
    position = end_header + 1
    value = packed[position:position + size]
    position += size
    if packed[position:position + 1] != b'\n':
        raise ValueError('Staged batch byte framing failed: ' + name)
    position += 1
    if len(value) != size:
        raise ValueError('Staged size changed: ' + name)
    if any(pattern.search(value) for pattern in patterns):
        raise ValueError('High-confidence credential signature: ' + name)
    if hashlib.sha256((ROOT / name).read_bytes()).digest() != hashlib.sha256(value).digest():
        raise ValueError('Worktree/staged bytes differ: ' + name)
    total += size
    if name in expected:
        digest = hashlib.sha256(value).hexdigest()
        if digest != expected[name]:
            raise ValueError('Frozen staged bytes mismatch: ' + name)
        matched[name] = digest
for name in changed:
    if name.startswith(('.cache/', '.tools/', 'data/', 'state/', 'logs/', 'models/')):
        raise ValueError('Private/runtime changed path: ' + name)
    if Path(name).suffix.lower() in ('.sqlite', '.db', '.vhdx', '.pfx', '.p12', '.pem'):
        raise ValueError('Private/runtime extension: ' + name)
if set(matched) != set(expected):
    raise ValueError('Frozen artifact missing from staged tree')
if position != len(packed):
    raise ValueError('Unexpected trailing Git batch bytes')
result = {
    'status': 'STAGED_MODULE_CHECKPOINT_PASS',
    'created_utc': datetime.now(UTC).isoformat(),
    'staged_tree_before_own_receipt': run('write-tree').decode().strip(),
    'staged_files': len(names), 'staged_bytes': total,
    'changed_paths': changed, 'frozen_blob_hashes': matched,
    'worktree_staged_byte_mismatches': 0, 'high_confidence_secret_pattern_hits': 0,
    'runtime_private_changed_paths': 0,
    'historical_registry_resolution': [
        {'original_path': key[0], 'original_sha256': key[1], 'archive_path': value}
        for key, value in aliases.items()
    ],
    'limitations': 'Primary selected staged byte/signature review; excludes own receipt. '
                   'No market data/state completeness or all-secret-types guarantee.',
}
with (ROOT / sys.argv[1]).open('x') as writer:
    json.dump(result, writer, indent=2)
    writer.write('\n')
print(json.dumps({key: result[key] for key in ('status', 'staged_files', 'staged_bytes')}))

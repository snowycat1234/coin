"""One pinned upstream file; reuse accepted bounded fetch/progress functions."""
import argparse, ast, hashlib, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
VENDOR = ROOT / 'third_party/jesse_example_smacrossover'
PREBIND_SHA = '92bd24b56d831496c09db22395aac8b2ba1b10049801f49d47bbf0bfa7e97e8c'
FETCH_SHA = 'b05184339d48c96285106a2000ba547a966e854836612d7bc0bafa4689321965'
LICENSE_SHA = '80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)

p = argparse.ArgumentParser()
p.add_argument('--run-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
work, output = a.run_dir.resolve(), a.output.resolve()
if (work.exists() or output.exists() or not work.is_relative_to(STATE)
        or not output.is_relative_to(ROOT / 'reports/fast_research')
        or sys.prefix != str(STATE / 'v8-clean-env-20261002-v2')):
    raise ValueError('Fresh source-only STATE/output and accepted clean interpreter required')
work.mkdir()
started = time.monotonic()
binding = dict(task_id=os.environ['COIN_TASK_ID'], helper_source_sha256=sha(__file__),
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    exact_command=shlex.join([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]),
    sys_prefix=sys.prefix, prebind_sha256=PREBIND_SHA, reused_fetch_source_sha256=FETCH_SHA,
    environment_lock_sha256=sha(ROOT / 'environments/v8/uv.lock'))
write(work / 'RUN_BINDING.json', binding)
report = dict(status='FAIL_D038_PINNED_SMA_SOURCE_PROVENANCE', binding=binding,
    run_dir=str(work), market_inputs_read=False, locked_consumed=False,
    models_fit=0, orders_sent=0, GPU=0, new_environment=False, candidate_qualification=False)
try:
    prebind_path = VENDOR / 'DOWNLOAD_PREBIND_20261003_V1.json'
    if sha(prebind_path) != PREBIND_SHA or sha(VENDOR / 'LICENSE') != LICENSE_SHA:
        raise ValueError('Prebound source/license bytes changed')
    spec = json.loads(prebind_path.read_text())
    reused = ROOT / spec['reused_fetch_source_path']
    if sha(reused) != FETCH_SHA:
        raise ValueError('Accepted fetch/progress source changed')
    tree = ast.parse(reused.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('fetch', 'progress')]
    if {node.name for node in functions} != {'fetch', 'progress'} or len(functions) != 2:
        raise ValueError('Exact accepted functions required')
    namespace = dict(urlopen=urlopen, STATE=STATE, os=os, json=json, time=time)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(reused), 'exec'), namespace)
    namespace['progress']('获取固定 MIT SMA 原始策略，不读取行情', 0, 1, '源码')
    payload = namespace['fetch'](spec['source_url'], spec['download_max_bytes'])
    parsed = ast.parse(payload)
    classes = [node for node in parsed.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1 or classes[0].name != 'SMACrossover':
        raise ValueError('Pinned SMACrossover class required')
    methods = {node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)}
    if not {'slow_sma', 'fast_sma', 'should_long', 'should_short', 'go_long',
            'go_short', 'update_position'} <= methods:
        raise ValueError('Original public hooks missing')
    destination = VENDOR / 'smacrossover_original.py'
    with destination.open('xb') as stream:
        stream.write(payload)
    source_sha = sha(destination)
    blob_sha = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    note = ('# Pinned public SMA crossover source\n\n'
        f"Repo: {spec['repo']}\nCommit: `{spec['commit']}`; original `SMACrossover/__init__.py`.\n"
        f'Unchanged strategy: {len(payload)} bytes, SHA256 `{source_sha}`, Git blob `{blob_sha}`.\n'
        f'`LICENSE` reuses the same-commit original MIT bytes, SHA256 `{LICENSE_SHA}`.\n\n'
        'Original class uses SMA50 > SMA200 for long eligibility and < for long liquidation; '
        'equal values preserve existing state. It is a state predicate, not a crossing event. '
        'The upstream class also supports shorts and whole-balance sizing and specifies no timeframe.\n\n'
        'Planned COIN port fixes closed UTC1d, long-only, fresh-flat scoring and shared '
        'capital/risk/latency/Bybit fee proxy accounting. No upstream sizing or short hook is executed. '
        'Raw vendor bytes are unchanged; no Jesse framework/dependency is installed. '
        'This provenance operation does not test a target, account, profitability or future eligibility.\n')
    with (VENDOR / 'UPSTREAM.md').open('x', encoding='utf-8') as stream:
        stream.write(note)
    registry = ROOT / 'docs/OPEN_SOURCE_REGISTRY.md'
    snapshot = ROOT / spec['registry_snapshot_path']
    if sha(registry) != spec['registry_before_sha256'] or sha(snapshot) != sha(registry):
        raise ValueError('Registry changed since exact pre-download snapshot; do not append')
    addition = ('\n\n### 固定公开 SMA50/200 日线来源（D038，收益运行前登记）\n\n'
        '| repo | commit／license | 用途与本地修改 |\n|---|---|---|\n'
        f"| {spec['repo']} | `{spec['commit']}`／MIT | 原 `SMACrossover/__init__.py` "
        f'置 `third_party/jesse_example_smacrossover/smacrossover_original.py`，SHA `{source_sha}`；'
        '原策略及同commit MIT许可字节零修改。COIN将仅移植长仓/退出hook，固定50/200闭合UTC日线，'
        '原short及whole-balance不移植；风险、10k资本、36bp费用与既有proxy账本复用。'
        '不安装新环境，不称原策略回测复现或投资资格。 |\n\n'
        f"追加前原登记字节保存 `{spec['registry_snapshot_path']}`，SHA `{spec['registry_before_sha256']}`；"
        '旧记录及原冻结来源不改写。\n')
    with registry.open('ab') as stream:
        stream.write(addition.encode())
    report.update(status='PASS_D038_PINNED_SMA_SOURCE_BYTES_AND_MIT_PROVENANCE_ONLY',
        source_path=str(destination), source_sha256=source_sha, source_bytes=len(payload),
        git_blob_sha1=blob_sha, license_sha256=LICENSE_SHA, prebind=spec,
        registry_before_sha256=spec['registry_before_sha256'], registry_after_sha256=sha(registry),
        registry_snapshot_sha256=sha(snapshot), raw_upstream_modified=False,
        semantics=dict(fast_period=50, slow_period=200, long='FAST_GT_SLOW',
            exit_long='FAST_LT_SLOW', equality='HOLD_STATE_NO_NEW_ENTRY',
            crossing_event_required=False, original_short=True,
            original_sizing='WHOLE_BALANCE', original_timeframe=None),
        source_hashes={str(destination.relative_to(ROOT)):source_sha,
            str((VENDOR/'LICENSE').relative_to(ROOT)):LICENSE_SHA,
            str(prebind_path.relative_to(ROOT)):PREBIND_SHA,
            str(reused.relative_to(ROOT)):FETCH_SHA,
            spec['registry_snapshot_path']:sha(snapshot),
            str((VENDOR/'UPSTREAM.md').relative_to(ROOT)):sha(VENDOR/'UPSTREAM.md')})
    namespace['progress']('固定源码和许可证已保存，尚未运行新策略', 1, 1, '源码')
except Exception as error:
    report.update(error_type=type(error).__name__, reason=str(error))
    raise
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        owned_bytes=sum(path.stat().st_size for directory in (work,VENDOR)
                        for path in directory.rglob('*') if path.is_file()), resources=resources.status())
    write(output, report)
    print(json.dumps(dict(status=report['status'], output=str(output), sha256=sha(output))))

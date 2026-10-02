"""Thin transport recovery of the preserved V1 probe; no new pipeline."""
from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/mnt/d/codex/coin')
BASE = ROOT / 'scripts/investment/funding_semantics_probe.py'
BASE_SHA256 = 'c433703b696e67b7a279756cee0891cf686111fed24f808e6f0c1992ce5bdf74'
TRANSPORT = ROOT / 'scripts/investment/funding_semantics_windows_transport_v2.ps1'
PROTOCOL = ROOT / 'protocols/FUNDING_SEMANTICS_PROBE_20261003_V2.json'

spec = importlib.util.spec_from_file_location('_coin_funding_semantics_v1', BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.need(base.sha(BASE) == BASE_SHA256, 'Preserved V1 semantics source changed')


def request_once(url, destination, timeout, maximum, is_api=False):
    base.need(is_api and timeout == 20 and maximum == 64000, 'Recovery only two fixed API requests')
    protocol = base.load(PROTOCOL)
    base.need(base.sha(TRANSPORT) == protocol['windows_transport_sha256'], 'Frozen Windows transport changed')
    native_script = subprocess.check_output(['wslpath', '-w', str(TRANSPORT)], text=True).strip()
    native_output = subprocess.check_output(['wslpath', '-w', str(destination)], text=True).strip()
    def quoted(value):
        return "'" + value.replace("'", "''") + "'"
    # Execute these exact pinned local bytes without changing execution policy.
    expression = ("& ([ScriptBlock]::Create([IO.File]::ReadAllText(" + quoted(native_script) + ")))"
                  + " -Url " + quoted(url) + " -OutputPath " + quoted(native_output))
    command = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-NonInteractive',
               '-Command', expression]
    started = time.monotonic()
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
                                check=False, text=True, encoding='utf-8', errors='replace')
        # JSON only, never print response bytes or potentially private transport settings.
        info = json.loads(result.stdout.strip().lstrip('\ufeff'))
        info.update(exact_transport_command=base.shlex.join(command), native_exit_code=result.returncode,
                    requested_at_utc=base.datetime.now(base.UTC).isoformat())
        if destination.exists():
            info.update(raw_path=str(destination), raw_sha256=base.sha(destination), bytes=destination.stat().st_size)
        base.write(destination.with_suffix('.http.json'), info)
        payload = destination.read_bytes() if info['status'] == 'RETRIEVED' else None
        return payload, info
    except Exception as error:
        info = dict(status='NATIVE_TRANSPORT_FAILURE', error_type=type(error).__name__, reason=str(error),
                    url=url, elapsed_seconds=time.monotonic()-started, retries=0,
                    exact_transport_command=base.shlex.join(command))
        base.write(destination.with_suffix('.http.json'), info)
        return None, info


def progress(phase, completed):
    # V1's API loop indices are 3 and 4 after its two document slots. V2 makes
    # zero HTML requests; show the actual two processed API URLs only.
    path = base.STATE / 'task-progress' / ('task-' + os.environ['COIN_TASK_ID'] + '.json')
    value = base.load(path)
    value.update(phase=phase, completed=max(0, completed-2), total=2, unit='固定历史API请求',
                 last_activity_at=time.time())
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(value, ensure_ascii=False)); os.replace(temp, path)


def derived_main_tree():
    node = next(n for n in ast.parse(BASE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    # Preserve comparison/registry logic; bind the exclusive recovery directory,
    # restriction stop and separate Windows resource metadata.
    changes = 0
    restriction_anchors = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value == 'funding-semantics-probe-20261003-v1':
            child.value = 'funding-semantics-probe-20261003-v2'; changes += 1
    base.need(changes == 1, 'Expected one exact V1 exclusive run-directory anchor')
    for child in ast.walk(node):
        if isinstance(child, ast.For):
            revised = []
            for statement in child.body:
                revised.append(statement)
                if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Attribute) and statement.value.func.attr == 'append'
                    and ast.unparse(statement.value.func.value) == "report['requests']"):
                    revised.extend(ast.parse("if receipt.get('http_status') in (403, 451, 418, 429):\n    raise ValueError('Official API access/rate restriction; stop without another request or bypass')").body)
                    restriction_anchors += 1
            child.body = revised
    base.need(restriction_anchors == 2, 'Exact preserved V1 request receipt anchors required')
    final = next(n for n in ast.walk(node) if isinstance(n, ast.Try) and n.finalbody)
    anchor = next(i for i, n in enumerate(final.finalbody)
                  if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                  and ast.unparse(n.value.func) == 'write' and ast.unparse(n.value.args[0]) == 'OUTPUT')
    final.finalbody[anchor:anchor] = ast.parse("""report['transport_resource_accounting'] = {
        'WSL_peak_RSS_scope': 'WSL_PYTHON_PROCESS_ONLY_NOT_WINDOWS_OR_SHARED_TOTAL',
        'WindowsPeakWorkingSet64_max': max((r.get('WindowsPeakWorkingSet64', 0) for r in report['requests']), default=0),
        'Windows_memory_scope': 'MAX_SEQUENTIAL_WINDOWS_TRANSPORT_PROCESS_PEAK_NOT_SHARED_TOTAL',
        'response_body_bytes_total': sum(r.get('response_body_bytes', 0) for r in report['requests']),
        'shared_total_peak_measured': False,
        'Windows_transport_outside_WSL_cgroup': True,
        'maximum_response_bytes_per_request': 64000}
""").body
    tree = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    return tree


def main():
    protocol = base.load(PROTOCOL)
    base.need(protocol['document_urls'] == [], 'Official documents already browsed; do not request HTML again')
    tree = derived_main_tree()
    digest = base.hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()
    base.need(digest == protocol['derived_main_ast_sha256'], 'Only prebound main changes permitted')
    namespace = dict(vars(base), __file__=__file__, PROTOCOL=PROTOCOL,
                     OUTPUT=ROOT/'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json',
                     request_once=request_once, progress=progress)
    exec(compile(tree, str(BASE), 'exec'), namespace)
    return namespace['main']()


if __name__ == '__main__':
    raise SystemExit(main())

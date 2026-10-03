"""Freeze only new October N10 marked-NAV metadata and accepted finance span before payloads."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
CHECKER_SHA = '45fa1ea1e6019d15e37e758b73263a075466075ee5109a54db0b8b675cb14e69'
RUN = STATE / 'd051-october-n10-financial-independent-20261004-v1'
PROTO = 'protocols/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json'
ACTUAL = 'reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_20261004_V1.json'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert os.environ.get('COIN_TASK_ID') and not RUN.exists()
code = ROOT / CHECKER
assert sha(code) == CHECKER_SHA
ast.parse(code.read_bytes())
spec = importlib.util.spec_from_file_location('d051_n10_compile_only_audit', code)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)
symbols = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', '1000PEPEUSDT', 'XRPUSDT', 'WIFUSDT', 'WLDUSDT', 'DOGEUSDT', '1000SATSUSDT', 'ORDIUSDT')
base, _, derivation = checker.prepare_financial(symbols)
guard = base.module(base.GUARD, 'd051_n10_freeze_small_guard', base.GUARD_SHA)
actual, actual_sha = guard.small(ROOT / ACTUAL, '18183c799504658d771fcd94184d37f489ed8ae16365b676c311fbaba9794472')
protocol, proto_sha = guard.small(ROOT / PROTO, 'daf10d160727812ce892f84460bcf0fe78bedb6510d2a1a212b159b3ad6b32d4')
assert actual['binding']['protocol_sha256'] == proto_sha
assert actual['binding']['task_id'] == 'ed878165efff4eb2886a0f4b2fcb1038'
task = guard.closed(actual['binding']['task_id'])
assert actual['completed_cases'] == actual['required_cases'] == actual['complete_calendar_cases'] == 4
assert all(c['symbols'] == list(symbols) and c['pool'] == 'LIQUIDITY_TEN' for c in actual['cases'])
scope = checker.calendar_scope(protocol)
assert scope['period_days'] == 31 and scope['score_month'] == '2024-10'
pins = [CHECKER, checker.REUSE, checker.PATCH,
        'scripts/investment/audit_closing_exempt_research.py',
        'docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py',
        base.REFERENCE, base.GUARD, 'scripts/research_v7/oracle_flow_ceiling.py',
        'scripts/research_v8/registry.py', 'src/quant/resources.py',
        'scripts/with_task_progress.sh', 'scripts/bounded.sh',
        'scripts/task_progress_run.py', 'environments/v8/uv.lock']
hashes = {path: sha(guard.project(path)) for path in pins}
assert hashes[checker.REUSE] == checker.REUSE_SHA and hashes[checker.PATCH] == checker.PATCH_SHA
for path, digest in protocol['source_hashes'].items():
    assert sha(guard.project(path)) == digest
rb, rb_sha = guard.small(Path(actual['run_dir']) / 'RUN_BINDING.json')
assert rb == actual['binding'] and rb['source_hashes'] == protocol['source_hashes']
archive = ROOT / 'docs/archive/MULTI_ASSET_FINANCIAL_AUDIT_USED_OCTOBER_N2_20261004.py'
assert sha(archive) == CHECKER_SHA  # exact already-used October checker; no duplicate code archive
RUN.mkdir()
plan = dict(ready_to_execute=True, checker_sha256=CHECKER_SHA,
    protocol_path=PROTO, protocol_sha256=proto_sha,
    actual_report=ACTUAL, actual_report_sha256=actual_sha,
    actual_task_id=actual['binding']['task_id'], source_hashes=hashes,
    source_archives={}, required_scope=scope,
    tolerances=dict(cash_USDT=1e-7, ratio=1e-10),
    budgets=dict(peak_RSS_bytes=1_000_000_000, wall_seconds=1200, new_owned_bytes=5_000_000),
    metadata_freezer_task_id=os.environ['COIN_TASK_ID'], actual_closed_task=task,
    producer_run_binding_sha256=rb_sha,
    complete_financial_span_compiled_before_arrays=derivation,
    old_QA_or_accounts_replayed=False,
    audit_scope='COMPLETE31D_MARKED_NAV_WITH_ACTUAL_UNREALIZED_INVENTORY_NOT_LIQUIDATED_RETURN',
    liquidated_return='NOT_EVALUABLE', investment_qualification_pass=False)
guard.write(RUN / 'ACTUAL_BINDING.json', plan)
print(json.dumps(dict(ready=True, checker_sha256=CHECKER_SHA,
    ACTUAL_BINDING_sha256=sha(RUN / 'ACTUAL_BINDING.json'), run_dir=str(RUN),
    protocol_sha256=proto_sha, actual_report_sha256=actual_sha, financial_payloads_read=0)))

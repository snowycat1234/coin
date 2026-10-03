"""UNRUN D045 independent date-only adapter; no account/replay/target producer call.

The original audit_case, source payload reader inside window_reader, numeric
helpers and HandLedger remain exact imported references. Only the reader's
fixed-date dictionary is privately replaced before any financial array IO.
A future separately frozen audit main must first validate the94-entry accepted
303D input metadata, new smoke/protocol/actual completed tasks and resources.
"""
import ast
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT=Path('/mnt/d/codex/coin')
FINANCE='docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
FINANCE_SHA='1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
HELPER='docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
HELPER_SHA='f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4'
PERIOD=('303D','2024-09-01T00:00:00+00:00','2025-07-01T00:00:00+00:00',303,436320)


def prepare_financial_adapter():
    """No payload read or financial function execution during compilation."""
    if hashlib.sha256((ROOT/HELPER).read_bytes()).hexdigest()!=HELPER_SHA:
        raise ValueError('Original private independent loader source bytes changed')
    spec=importlib.util.spec_from_file_location('_d045_existing_independent_loader',ROOT/HELPER)
    loader=importlib.util.module_from_spec(spec);sys.modules[spec.name]=loader;spec.loader.exec_module(loader)
    financial=loader.load(FINANCE,FINANCE_SHA,'_d045_unchanged_financial_original')
    tree=ast.parse((ROOT/FINANCE).read_bytes())
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='window_reader']
    loader.need(len(selected)==1,'One original window_reader before any array IO');node=selected[0]
    original_AST=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
    anchors=[n for n in ast.walk(node) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets)]
    loader.need(len(anchors)==1 and isinstance(anchors[0].value,ast.Subscript)
        and isinstance(anchors[0].value.value,ast.Dict)
        and [key.value for key in anchors[0].value.value.keys]==['122D','90D'],
        'Exact original reader date-map anchor; no source/schema/finance transformation')
    anchors[0].value.value=ast.parse("{'303D':('2024-09-01T00:00:00+00:00','2025-07-01T00:00:00+00:00',303)}",mode='eval').body
    namespace=dict(vars(financial))
    exec(compile(ast.fix_missing_locations(ast.Module([node],type_ignores=[])),
        '<D045-private-303-financial-reader>','exec'),namespace)
    loader.need(namespace['audit_case'] is financial.audit_case and namespace['target_reference'] is financial.target_reference
        and financial.CASH_TOL==1e-7 and financial.RATIO_TOL==1e-10,
        'Original account audit/strict independent SMA and all tolerances unchanged')
    proof=dict(original_financial_sha256=FINANCE_SHA,original_reader_AST_sha256=original_AST,
        derived_reader_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        only_changed_anchor='window_reader.expected date dictionary',period=PERIOD,
        original_audit_case_direct_reference=True,original_payload_columns_and_source_paths_unchanged=True,
        HandLedger_sha256=loader.HAND_SHA,tolerances=dict(cash_USDT=1e-7,ratio=1e-10),
        market_arrays_read=False,financial_functions_executed=False)
    return financial,namespace['window_reader'],proof


if __name__=='__main__':
    raise SystemExit('UNRUN_DATE_HELPER_ONLY: future exact accepted metadata/audit main is required; no arrays or financial functions executed')
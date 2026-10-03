"""Only syntax and source identity; no import of audited scientific functions."""
import ast, hashlib, json, os, resource, time
from pathlib import Path
root=Path('/mnt/d/codex/coin')
source=root/'scripts/investment/audit_perpetual_directional_recovery.py'
run=Path('/home/xflops/coin-state/perpetual-recovery-independent-compile-20261003-v3')
run.mkdir();began=time.monotonic();data=source.read_bytes()
receipt=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(source),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),
    status='FAIL_AST_COMPILE_ONLY',scope='NO_IMPORT_PAYLOAD_TEST_FINANCIAL_OR_SOURCE_QA',payload_rows_read=0)
try:
    tree=ast.parse(data,filename=str(source));compile(tree,str(source),'exec')
    receipt['status']='PASS_AST_COMPILE_ONLY'
finally:
    receipt.update(elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (run/'AST_COMPILE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)

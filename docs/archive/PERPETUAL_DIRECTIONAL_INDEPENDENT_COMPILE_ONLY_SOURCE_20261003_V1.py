"""One authorized syntax/metadata operation, no imports of audited science."""
import ast, hashlib, json, os, resource, sys, time
from pathlib import Path

root=Path('/mnt/d/codex/coin')
source=root/'scripts/investment/audit_perpetual_directional.py'
run=Path('/home/xflops/coin-state/perpetual-directional-independent-compile-20261003-v1')
run.mkdir()
began=time.monotonic()
data=source.read_bytes()
receipt=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(source),
    source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),
    scope='AST_COMPILE_ONLY_NO_IMPORT_PAYLOAD_TEST_OR_SCIENCE',payload_rows_read=0,
    sys_prefix=sys.prefix,CPU_threads_requested=2,status='FAIL_AST_COMPILE_ONLY')
try:
    tree=ast.parse(data,filename=str(source))
    compile(tree,str(source),'exec')
    receipt.update(status='PASS_AST_COMPILE_ONLY',top_level_functions=[n.name for n in tree.body if isinstance(n,ast.FunctionDef)])
finally:
    receipt.update(elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (run/'AST_COMPILE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt),flush=True)

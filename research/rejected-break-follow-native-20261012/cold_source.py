"""Run unchanged public source scripts with a fresh-process original-STATE audit."""
import json,runpy,sys
from pathlib import Path
key,state=sys.argv[1],Path(sys.argv[2]);root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;P=json.loads((here/'PROTOCOL.json').read_text());W=P['windows'][key];blocked=[]
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).absolute()
  if any(p.is_relative_to(Path(x)) for x in ('/workspace/rejected-break-follow-native-state/OBSERVED_Y2023','/workspace/rejected-break-follow-native-state/OBSERVED_Y2025','/workspace/cs-2023-state','/workspace/cs-continuous-state','/workspace/portfolio-risk-2025-state','/workspace/portfolio-risk-budget-state','/workspace/quantity-grid-state','/workspace/unified-exit-economics-state')):blocked.append(str(p));raise RuntimeError('Original STATE forbidden in child public source reconstruction')
sys.addaudithook(audit)
if key=='Y2023':
 import subprocess
 ix=json.loads(subprocess.check_output(['git','show',W['source_artifact']+':'+W['source_index_path']],cwd=root));q=ix['quarter_artifacts'];script=root/'research/cs-2023-continuous-economics-20261012/source.py';args=['build','--state',str(state),'--source-commit',ix['source_commit'],'--q1-commit',q['Q1'],'--q2-commit',q['Q2'],'--expected-commit',W['source_artifact']]
else:script=root/'research/portfolio-risk-2025-native-20261012/public_source.py';args=['--state',str(state),'--artifact-commit',W['source_artifact']]
sys.argv=[str(script),*args];sys.path[0]=str(script.parent)
try:runpy.run_path(str(script),run_name='__main__')
finally:(state.parent/'SOURCE_CHILD_AUDIT.json').write_text(json.dumps(dict(original_STATE_open_attempts=len(blocked),blocked=blocked,unchanged_script=str(script),launch='FRESH_NORMAL_MAIN_IMPORTS_WITH_AUDIT_NO_NAMESPACE_PATCH'),indent=2)+'\n')

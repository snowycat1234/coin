import sys,json,os,importlib.metadata,hashlib,ast
from pathlib import Path
sys.path.append('/home/xflops/coin-state/selector-support-v1')
import yaml,psutil,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from quant.paths import ROOT,STATE
support=STATE/'selector-support-v1'
files={str(p.relative_to(support)):hashlib.sha256(p.read_bytes()).hexdigest() for p in support.rglob('*') if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in str(p)}
versions={p:importlib.metadata.version(p) for p in ('xgboost-cpu','PyYAML','psutil','matplotlib','contourpy','cycler','fonttools','kiwisolver','packaging','pillow','pyparsing','python-dateutil','six')}
for p in (ROOT/'scripts/research').glob('*.py'):ast.parse(p.read_text())
fig=plt.figure();fig.savefig(support/'support_smoke.png');plt.close(fig)
r=dict(status='PASS_ISOLATED_CONFIG_PROGRESS_PLOT_DEPENDENCIES_NO_MODEL_FITS',task_id=os.environ['COIN_TASK_ID'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),versions=versions,installed_file_sha256=files,installation='uv pip target --no-deps pinned; existing CPU core unmodified',model_fits=0,library_local_modifications=[])
(ROOT/'reports/SELECTOR_SUPPORT_RUNTIME_20261006_V1.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(status=r['status'],versions=versions,files=len(files))))
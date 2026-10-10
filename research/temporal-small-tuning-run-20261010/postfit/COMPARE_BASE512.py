"""Compare matched baseline512 snapshots with existing512 models; zero fits."""
import json
from pathlib import Path

import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_two_expert.checkpoint import _atomic_json
from modules.temporal_two_expert.exact import sha

root = Path('/workspace/coin-temporal')
out = Path('/workspace/coin-state/work/temporal-two-expert-20261009/small-tuning-run')
torch.set_num_threads(1)
rows=[]
for fold, oldroot in [('FOLD_20240101','temporal-prequential-transfer-20261009'),('FOLD_20240401','temporal-april-transfer-20261009')]:
    folder = out/f'{fold}__BASE_DATE_LR1E3'
    p=json.loads((folder/'MATCHED512.json').read_text())
    oldpath = root/'research'/oldroot/'forward'/fold/'MODEL_ADAM_RNG.pt'
    old=torch.load(oldpath,map_location='cpu',weights_only=True)
    new=torch.load(folder/p['file'],map_location='cpu',weights_only=True)
    if old['step']!=512 or new['step']!=512 or sha(folder/p['file'])!=p['SHA256']:
        raise ValueError('Exact512 snapshot bodies required')
    comparison={k:tree_identity(new[k])==tree_identity(old[k]) for k in ['model','optimizer','rng']}
    rows.append(dict(fold=fold,old_checkpoint_SHA256=sha(oldpath),new_pointer=p,bitwise_model_Adam_RNG=comparison,old_model_identity=old['model_identity'],new_model_identity=new['model_identity']))
_atomic_json(out/'BASE512_OLD_COMPARISON.json',dict(status='COMPLETED_READ_ONLY_COMPARISON',rows=rows,optimizer_updates=0,model_inferences=0,wallet_rollouts=0,reserve_read=False,script_SHA256=sha(Path(__file__))))
print(json.dumps(rows,allow_nan=False))

"""Read-only sigmoid/weight statistics for available frozen512 terminals."""
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_prequential_transfer.protocol import FOLDS,sources
from modules.temporal_prequential_transfer.stage import binding_for,load_fold
from modules.temporal_two_expert.checkpoint import model_identity

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009')
run=state/'prequential-transfer'
records={}
for fold in FOLDS:
    if not (run/fold/'TERMINAL.json').exists():
        continue
    train,forward,prototype,scaler,data,_=load_fold(state,fold)
    model,optimizer=initialize(scaler)
    initial={n:p.detach().clone() for n,p in model.named_parameters()}
    load_checkpoint(run/fold,model,optimizer,binding_for(model,data),sources=sources)
    model.eval()
    before=model_identity(model)
    roles={}
    for role,episodes in [('TRAIN',train),('FORWARD',[forward])]:
        logits={key:[] for key in ('w','s','r')}
        handles=[]
        for key,layer in [('w',model.base.w_head),('s',model.base.s_head),('r',model.r_head)]:
            def hook(module,args,output,key=key):
                logits[key].append(output.detach().numpy().reshape(-1).copy())
            handles.append(layer.register_forward_hook(hook))
        requests=[]
        try:
            for e in episodes:
                with torch.no_grad():
                    requests.append(predict_episode(model,e).numpy())
        finally:
            for h in handles:
                h.remove()
        gates={}
        for key,values in logits.items():
            z=np.concatenate(values)
            p=1/(1+np.exp(-z))
            gates[key]=dict(mean=float(p.mean()),minimum=float(p.min()),maximum=float(p.max()),
                fraction_gt99=float((p>.99).mean()),fraction_lt01=float((p<.01).mean()),
                fraction_derivative_lt001=float((p*(1-p)<.001).mean()))
        roles[role]=dict(gates=gates,request_mean=np.concatenate(requests).mean(0).tolist())
    assert before==model_identity(model)
    delta={n:dict(initial_norm=float(torch.linalg.vector_norm(initial[n])),
        final_norm=float(torch.linalg.vector_norm(p)),delta_norm=float(torch.linalg.vector_norm(p-initial[n])))
        for n,p in model.named_parameters()}
    records[fold]=dict(model_identity=before,initial_investment_gate=.5,initial_pair_gate=.5,
        initial_short_gate=.01,weight_changes=delta,roles=roles)
out=run/'GATE_WEIGHT_STATS.json'
out.write_text(json.dumps(dict(schema='READ_ONLY_FRESH_PREQUENTIAL_GATE_WEIGHT_STATS_V1',optimizer_updates=0,folds=records),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='FROZEN_GATE_WEIGHT_STATS_COMPLETE',folds=len(records))))

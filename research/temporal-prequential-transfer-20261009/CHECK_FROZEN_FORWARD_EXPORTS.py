"""Verify saved frozen forward artifacts; inference and mapper only, no refit."""
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_prequential_transfer.export import verify_bundle
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_prequential_transfer.protocol import FOLDS, sources
from modules.temporal_prequential_transfer.stage import binding_for, load_fold
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.inputs import CORE5, array_digest

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009')
run=state/'prequential-transfer'
records=[]
for fold in FOLDS:
    path=run/'forward'/fold
    if not path.exists():
        continue
    result=verify_bundle(path)
    train,forward,prototype,scaler,data,receipt=load_fold(state,fold)
    model,optimizer=initialize(scaler)
    binding=binding_for(model,data)
    saved=load_checkpoint(run/fold,model,optimizer,binding,sources=sources)
    assert saved['step']==512 and all(float(optimizer.state[p]['step'])==512 for p in model.parameters())
    before=model_identity(model)
    model.eval()
    rng=torch.get_rng_state().clone()
    with torch.no_grad():
        requests=predict_episode(model,forward).numpy()
    with np.load(path/'REQUESTS.npz',allow_pickle=False) as z:
        assert set(z.files)=={'decision_us','symbol_order','expert_order','desired_expert_budget','action_eligible','feature_available_us','request_available_us'}
        np.testing.assert_array_equal(z['desired_expert_budget'],requests)
        np.testing.assert_array_equal(z['decision_us'],forward.windows.decision_us)
        assert tuple(z['symbol_order'])==CORE5
        assert np.all(z['feature_available_us']<=z['decision_us'])
    assert requests.shape==(63,6) and np.isfinite(requests).all()
    assert np.all(requests[:,2:4]==0) and np.allclose(requests.sum(1),1,atol=1e-14,rtol=0)
    assert before==model_identity(model) and torch.equal(rng,torch.get_rng_state())
    targets,mapped=prototype.mapped_path(compress(requests),forward.internal.contexts)
    budget=expand(np.stack([r['budget'] for r in mapped]))
    l1=[float(np.abs(r['budget']-r['released_prior']).sum()) for r in mapped]
    assert max(l1)<=.1+1e-12 and np.all(targets[-1]==0)
    with np.load(path/'PAIRED_PATHS.npz',allow_pickle=False) as z:
        np.testing.assert_array_equal(z['FRESH_GRU_targets'],targets)
        np.testing.assert_array_equal(z['FRESH_GRU_budget'],budget)
    with np.load(path/'CURRENT_CONTEXT63.npz',allow_pickle=False) as z:
        np.testing.assert_array_equal(z['expert_targets'],forward.expert_targets)
        np.testing.assert_array_equal(z['target_available_us'],forward.target_available_us)
        assert bool(z['initial_previous_quote_none']) and bool(z['initial_quote_capacity_zero'])
    assert result['policies']['FRESH_GRU']['paid_terminal_cash']
    record=dict(fold=fold,status='FROZEN_PATH_MODEL_ADAM_SOURCE_CLOCK_MASK_MAPPER_VERIFIED',actual_Adam_steps512=True,
        requests_identity=array_digest(requests),maximum_discretionary_L1=max(l1),
        paid_terminal_cash=True,model_identity=before,forward_PnL=result['policies']['FRESH_GRU']['net_PnL'],
        primary_PnL_excess=result['primary_PnL_excess'],optimizer_updates=0,native_wallets=0,provider_downloads=0)
    records.append(record)
out=run/'FORWARD_EXPORT_CHECK.json'
out.write_text(json.dumps(dict(status='ALL_AVAILABLE_FROZEN_EXPORTS_VERIFIED',records=records),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='ALL_AVAILABLE_FROZEN_EXPORTS_VERIFIED',folds=len(records))))

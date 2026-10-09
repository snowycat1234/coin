"""Read-only audit; no optimization or development economic scoring."""
import copy
import json
import subprocess
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.gradient import episode_diagnostic
from modules.temporal_episode_weighting_v2.snapshot import initialize as warm_initialize
from modules.temporal_episode_weighting_v2.stage import sources as warm_sources, tree_identity
from modules.temporal_expert_input.checkpoint import load_checkpoint
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_expert_input.stage import inputs
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import fit_standardizer

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
repo=Path('/workspace/coin-temporal')
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009')
out=state/'fresh-initialization'
out.mkdir(exist_ok=True)
commit=subprocess.check_output(['git','rev-parse','d3d57332'],cwd=repo,text=True).strip()
prefix='research/temporal-episode-weighting-v2-20261009/native61-requests/EXP_GRU64_WEIGHT_DATE/'
names=('MODEL_ADAM_RNG.pt','RUN.json','TERMINAL.json','REQUESTS.npz','SCALER.npz','MANIFEST.json')
comparator_files={}
for name in names:
    path=repo/(prefix+name)
    assert subprocess.check_output(['git','show',commit+':'+prefix+name],cwd=repo)==path.read_bytes()
    comparator_files[name]=sha(path)
warm_binding=json.loads((repo/(prefix+'RUN.json')).read_text())
assert warm_binding['specification']['algorithm']['arm']=='GRU64_WEIGHT_DATE'
assert warm_binding['specification']['algorithm']['mixing']==0
for name,expected in warm_binding['specification']['algorithm']['versioned_sources'].items():
    assert sha(repo/name)==expected
    assert subprocess.check_output(['git','show',commit+':'+name],cwd=repo)==(repo/name).read_bytes()
train,dev,prototype,dataset,scaler=inputs(state)
assert not dev and [len(e.contexts) for e in train]==[54,88,62,144,430]
assert dataset==warm_binding['specification']['data_split_identity']
refit=fit_standardizer([e.windows for e in train],training_cutoff_us=train[0].split_cutoff_us)
assert refit.identity==scaler.identity and refit.provenance==scaler.provenance
for key in ('mean','scale','count'):
    np.testing.assert_array_equal(getattr(refit,key),getattr(scaler,key))
assert refit.provenance['real_row_count']==907
warm,optimizer,parent,births=warm_initialize(state,scaler)
loaded=load_checkpoint(state/'episode-weighting-v2/GRU64_WEIGHT_DATE',warm,optimizer,warm_binding,sources=warm_sources)
assert loaded['step']==1292 and loaded['checkpoint_SHA256']==comparator_files['MODEL_ADAM_RNG.pt']
assert loaded['model_identity']=='7b0f0a6c58fec8efd2aacec5c5abd41ec2aca68fa4c27432a9770b59acb594fd'
fresh,fresh_optimizer=initialize(refit)
fresh_contract=copy.deepcopy(fresh.contract)
fresh_contract.pop('fresh_initialization')
fresh_contract['initialization']=warm.contract['initialization']
assert fresh_contract==warm.contract
assert [(name,tuple(p.shape),str(p.dtype)) for name,p in fresh.named_parameters()]==[(name,tuple(p.shape),str(p.dtype)) for name,p in warm.named_parameters()]
assert fresh.parameter_count==13699 and not fresh_optimizer.state
assert fresh.base.contract==warm.base.contract
expected=json.loads((repo/'research/temporal-prequential-transfer-20261009/RECEIPT.json').read_text())
assert tree_identity(_rng_state())==expected['same_all_initial_RNG_identity']
assert parameter_identity(fresh)=='0994f7810bad367ba112800f2e3aeea503813094d62bb734c7e489de7bf995f2'
probe,_=initialize(refit)
probe.load_state_dict(warm.state_dict(),strict=True)
probe.eval()
warm.eval()
for e in train:
    with torch.no_grad():
        torch.testing.assert_close(predict_episode(probe,e),predict_episode(warm,e),rtol=0,atol=0)
diag=episode_diagnostic(probe,train,prototype,mixing=0,feature_batch_size=32,snapshot_step=512)
saved_terminal=json.loads((repo/(prefix+'TERMINAL.json')).read_text())
loss=diag['trained_objective_summary']['weighted_mean_loss']
assert abs(loss-saved_terminal['last_diagnostic']['trained_objective_summary']['weighted_mean_loss'])<1e-15
fresh,fresh_optimizer=initialize(refit)
record=dict(
    status='MATCHED_BEFORE_FITTING_NO_UNAVOIDABLE_ECONOMIC_OR_ARCHITECTURE_DIFFERENCE',
    comparator_commit=commit,comparator_files_SHA256=comparator_files,
    comparator_model_identity=loaded['model_identity'],comparator_run_id=warm_binding['run_id'],
    fresh_parameters=13699,training_decisions=778,natural_wallet_lengths=[54,88,62,144,430],
    unique_training_scaler_rows=907,scaler_identity=refit.identity,
    data_identity=dataset,architecture_equal_except_initialization_metadata=True,
    same_supplied_weights_train_requests_bitwise_equal=True,
    copied_warm_state_date_objective_reproduced=loss,
    training_features_targets_clocks_prices_funding_masks_identities_equal=True,
    fresh_parameters_identity=parameter_identity(fresh),fresh_all_RNG_identity=tree_identity(_rng_state()),
    fresh_Adam_empty=True,warm_terminal_base_Adam_age=1292,warm_new_heads_Adam_age=512,
    warm_stage_start_base_Adam_age=780,fresh_terminal_all_Adam_age_target=512,
    intended_difference='prescribed fresh parameters empty Adam seeded RNG versus retained warm parameters base Adam history RNG;not equal lifetime exposure',
    optimizer_updates=0,development_economic_scores=0,provider_downloads=0,native_wallets=0,
    existing_sources_unchanged=True,
)
(out/'COMPARABILITY.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:record[k] for k in ('status','training_decisions','unique_training_scaler_rows','scaler_identity','copied_warm_state_date_objective_reproduced')}))

"""Reconstruct the exact published July episode from its saved numeric inputs.

Source primitive/event reconstruction is REUSED from the pinned producer receipt,
not claimed to be re-executed here. Every restored identity must match the original
paired preflight before either frozen model can run. No network calls.
"""
import json
from pathlib import Path
import numpy as np
from modules.temporal_added_history_july.models import commit_bytes
from modules.temporal_added_history_july.protocol import OLD, ROOT, SCALER, CONTROLS
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_two_expert.exact import Episode, load_prototype, sha
from modules.temporal_two_expert.inputs import FeatureTimeline, DAY_US, CORE5, FEATURE_NAMES, MARKET_CONTEXT, array_digest, digest
from modules.temporal_two_expert.training_packet import named_context

COMMIT='90b8fd65d092b52091b3fee7717c0478b265bc6e'

def inputs(state, economics=None):
    manifest_path=OLD/'MANIFEST.json'
    assert sha(manifest_path)==commit_bytes(COMMIT,str(manifest_path.relative_to(ROOT)))
    manifest=json.loads(manifest_path.read_text())
    required={'INPUT_RECEIPT.json','CURRENT_CONTEXT.npz','FEATURE_ROWS.npz','RESULT.json'}
    assert required <= manifest['files'].keys()
    for name,row in manifest['files'].items():
        path=OLD/name
        assert path.stat().st_size==row['bytes'] and sha(path)==row['SHA256']
        assert sha(path)==commit_bytes(COMMIT,str(path.relative_to(ROOT)))
    receipt=json.loads((OLD/'INPUT_RECEIPT.json').read_text())
    with np.load(OLD/'CURRENT_CONTEXT.npz',allow_pickle=False) as z:
        c={k:z[k].copy() for k in z.files}
    with np.load(OLD/'FEATURE_ROWS.npz',allow_pickle=False) as z:
        f={k:z[k].copy() for k in z.files}
    assert tuple(c['symbol_order'])==tuple(f['symbol_order'])==CORE5
    assert tuple(f['feature_order'])==FEATURE_NAMES and tuple(f['aggregate_order'])==MARKET_CONTEXT
    source_hashes=receipt['primitive_SHA256']
    timeline=FeatureTimeline(f['values'],f['valid'],f['step_valid'],f['completed_us'],np.broadcast_to(f['completed_us'][:,None,None],f['values'].shape).copy(),digest(source_hashes))
    decisions=c['decision_us'];windows=timeline.windows(decisions)
    prototype=load_prototype(Path(state)/'recovery/source/modules/direct_path/prototype.py')
    contexts=tuple(named_context(prototype,int(t),c['expert_targets'][i,[0,1,4]],c['expert_eligible'][i,[0,1,4]],c['past_returns30'][i],np.zeros(13),c['target_available_us'][i,[0,1,4]]) for i,t in enumerate(decisions))
    provenance={k:receipt[k] for k in ('primitive_SHA256','target_adapter_SHA256','risk_sources','short_producer_SHA256','economics')}
    start,end=1719792000000000,1725235200000000
    original=Episode('FIXED_JULY2024_TRANSFER',windows,contexts,c['prices'],c['funding_coeff'],c['outcome_available_us'],start,end,end+DAY_US,'SEEN_VALIDATION',digest(provenance))
    expanded=append_episode(original,c['expert_targets'][:,5:6],c['expert_eligible'][:,5:6],c['target_available_us'][:,5:6],prototype,digest(dict(recipe=receipt['short_producer_SHA256'],source=source_hashes)))
    episode=expose_episode(expanded)
    restored=dict(decision_us=episode.windows.decision_us,expert_targets=episode.expert_targets,expert_eligible=episode.eligible,target_available_us=episode.target_available_us,past_returns30=np.stack([r.past_returns30 for r in episode.contexts]),expert_state=episode.expert_state,expert_input_available_us=episode.expert_input_available_us,prices=episode.prices,funding_coeff=episode.funding_coeff,outcome_available_us=episode.label_available_us)
    for k,v in restored.items():np.testing.assert_array_equal(v,c[k])
    assert episode.identity==manifest['episode_identity']==receipt['episode_identity']
    controls={n:json.loads((OLD/'RESULT.json').read_text())['policies'][n] for n in CONTROLS}
    data=dict(receipt,original_loader_scaler_identity=receipt['scaler_identity'],scaler_identity=SCALER,scaler_rows=907,controls_reused=CONTROLS)
    binding=dict(episode_identity=episode.identity,feature_identity=array_digest(f['values']),feature_clock_identity=array_digest(f['completed_us']),context_identity=digest({k:array_digest(v) for k,v in restored.items()}),control_RESULT_SHA256=sha(OLD/'RESULT.json'),data=data)
    expected=json.loads((ROOT/'research/temporal-added-history-july-20261010/PRESCORE.json').read_text())['input_binding']
    assert binding==expected,'Cached reconstruction must match every original preflight input binding'
    return episode,prototype,data,binding,controls

"""Frozen April interface/provenance counterexamples; never run an account."""
import json,shutil,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import april_native63 as april
STATE=ROOT.parent/'coin-recovery-state'


@pytest.mark.parametrize('bad',['terminal_clock','terminal_price','terminal_funding','expert_clock','warm_start'])
def test_bound_export_semantics_stop_before_account(tmp_path,monkeypatch,bad):
    _,original,_=april.locations(STATE);producer=tmp_path/'producer';shutil.copytree(original,producer)
    manifest=april.read(producer/'MANIFEST.json')
    if bad=='warm_start':
        p=producer/'RUN.json';r=april.read(p);r['specification']['algorithm']['parent']={'fresh':False,'step':780};p.write_text(json.dumps(r))
    else:
        p=producer/'CURRENT_CONTEXT63.npz'
        with np.load(p,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
        if bad=='terminal_clock':a['outcome_available_us'][-1]+=1
        elif bad=='terminal_price':a['surrogate_prices'][-1,0]+=1
        elif bad=='terminal_funding':a['surrogate_funding_coeff'][-1,0]=.00001
        else:a['expert_input_available_us'][0,0]=a['decision_us'][0]+1
        np.savez_compressed(p,**a)
    manifest['files'][p.name]={'bytes':p.stat().st_size,'SHA256':april.sha(p)}
    m=producer/'MANIFEST.json';m.write_text(json.dumps(manifest));monkeypatch.setattr(april,'MANIFEST_SHA',april.sha(m))
    with pytest.raises(ValueError):april.inspect_export(producer)


def test_actual_consumed_prefix_matches_all_five_original_identities():
    cache,producer,_=april.locations(STATE);proof,clocks=april.actual_prefix(STATE,cache,producer)
    run=april.read(producer/'RUN.json')['specification'];assert proof['episode_identities']==run['data_split_identity']['train']
    assert proof['training_samples']==749 and proof['scaler_rows']==878
    assert proof['active_intervals']==744 and proof['known_flat_paid_closes']==5
    assert proof['raw_March31_outcome_consumed'] is False
    assert clocks['label_available_us'][-1]==1711843260000001<april.CAL['start']
    assert proof['scaler_values_bit_identical'] and proof['model_tensors_loaded'] is False

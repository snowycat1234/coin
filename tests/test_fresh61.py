"""Bound fresh512 receipt rejection fixtures; no models or accounts."""
import copy,json,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parents[1]/'research/recover-frozen-runner-20261009';sys.path.insert(0,str(HERE))
import fresh61
STATE=HERE.parents[2]/'coin-recovery-state'


def receipts():
    bundle,evidence=fresh61.locations(STATE)
    return [fresh61.read(bundle/name) for name in ('MANIFEST.json','RUN.json','TERMINAL.json')]+[fresh61.read(evidence/name) for name in ('READY.json','COMPARABILITY.json')]


def test_actual_fresh512_bound_receipts():
    r=fresh61.initialization(*receipts());assert r['parameters']==13699 and r['fresh_all_Adam_age']==512 and not r['equal_lifetime_exposure']


@pytest.mark.parametrize('case',('nonempty_adam','warm_birth','wrong_updates','wrong_dataset'))
def test_receipt_changes_stop_before_account(case):
    m,run,terminal,ready,comparison=copy.deepcopy(receipts())
    if case=='nonempty_adam':ready['empty_Adam']=False
    elif case=='warm_birth':run['specification']['algorithm']['parameter_birth_steps']['base.joint.bias']=780
    elif case=='wrong_updates':terminal['completed_updates']=513
    else:comparison['data_identity']={}
    with pytest.raises(ValueError):fresh61.initialization(m,run,terminal,ready,comparison)

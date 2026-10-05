import pytest
from quant.resources import RAM_LIMIT, status, validate_budget


def fields(limit='8000000000', swap_max='0', swap_current='0'):
    return {'memory.max':limit,'memory.swap.max':swap_max,'memory.swap.current':swap_current}


def test_ram_and_swap_fail_closed():
    validate_budget(fields())
    validate_budget(fields('5000000000'))
    for limit in ('max','8000000001','0'):
        with pytest.raises(RuntimeError):validate_budget(fields(limit))
    for swap_max,swap_current in (('max','0'),('1','0'),('0','1')):
        with pytest.raises(RuntimeError,match='swap'):validate_budget(fields(swap_max=swap_max,swap_current=swap_current))


def test_real_shared_parent_covers_research_and_legacy_collection():
    measured=status()
    assert measured['ram_limit_bytes']==RAM_LIMIT==8_000_000_000
    assert measured['swap_bytes']==0 and measured['gpu_used'] is False
    assert measured['aggregate_cgroup'].endswith('/coin.slice')
    assert '/coin.slice/coin-research.slice/' in measured['task_cgroup']
    assert len(measured['cpu_affinity'])>1

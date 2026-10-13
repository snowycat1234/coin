"""Pure bounded-worker admission; RLIM_INFINITY is negative and never safe."""
from __future__ import annotations
AS_CAP_BYTES=4_000_000_000
CPU_CAP_SECONDS=1200

def require_worker_bounds(affinity, address_space, cpu_time):
    if len(affinity)!=1:
        raise RuntimeError('Exactly one CPU affinity is required')
    for name,pair,cap in (('AS',address_space,AS_CAP_BYTES),('CPU',cpu_time,CPU_CAP_SECONDS)):
        if (not isinstance(pair,(tuple,list)) or len(pair)!=2
                or any(not isinstance(x,int) or isinstance(x,bool) or x<0 or x>cap for x in pair)
                or pair[0]>pair[1]):
            raise RuntimeError(name+' soft/hard limits must both be finite, nonnegative and within the frozen cap')
    return {'status':'PASS_FINITE_ONE_CPU_AS_AND_CPU_BOUNDS','wallets_created':0}

"""Tiny synthetic execution-only probe; no scientific or historical inputs."""
import os
import resource
import time

allocation = bytearray(80_000_000)
for index in range(0, len(allocation), 4096):
    allocation[index] = 7
time.sleep(.3)
assert allocation[-4096] == 0 or allocation[-4096] == 7
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
assert peak >= 80_000_000
assert len(os.sched_getaffinity(0)) == 1
print('SYNTHETIC_ALLOCATION_BYTES', len(allocation), 'KERNEL_SELF_PEAK_BYTES', peak)

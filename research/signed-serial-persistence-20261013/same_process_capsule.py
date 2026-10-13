"""Execution-only guard: run a script in this process, never a shell child.

The historical scientific source remains frozen and untouched. Linux self RSS
is actively sampled; getrusage(RUSAGE_SELF) provides a separate kernel peak.
This is not a cgroup limit and sampled RSS can miss sub-interval spikes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import runpy
import shutil
import signal
import sys
import time
import traceback

ADDRESS = 4_000_000_000
RSS = 2_000_000_000
HOST_USED = 8_000_000_000
DISK_RESERVE = 15 * 1024**3
MAX_SECONDS = 60
SAMPLE_SECONDS = .05
THREAD_VARIABLES = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS',
                    'MKL_NUM_THREADS', 'POLARS_MAX_THREADS',
                    'NUMEXPR_NUM_THREADS', 'RAYON_NUM_THREADS',
                    'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')


class ResourceStop(RuntimeError):
    pass


def read_budget():
    lines = Path('/proc/self/status').read_text().splitlines()
    rss_line = next((line for line in lines if line.startswith('VmRSS:')), None)
    if rss_line is None:
        raise ResourceStop('SELF_RSS_UNAVAILABLE')
    rss = int(rss_line.split()[1]) * 1024
    if rss <= 0:
        raise ResourceStop('SELF_RSS_INVALID')
    mem = {line.split(':')[0]: int(line.split()[1]) * 1024
           for line in Path('/proc/meminfo').read_text().splitlines()}
    used = mem['MemTotal'] - mem['MemAvailable']
    if len(Path('/proc/swaps').read_text().splitlines()) != 1:
        raise ResourceStop('ACTIVE_SWAP')
    return rss, used


def no_children(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty',
                 'os.posix_spawn', 'os.exec'):
        raise ResourceStop('CHILD_PROCESS_FORBIDDEN')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=MAX_SECONDS)
    parser.add_argument('script', type=Path)
    parser.add_argument('script_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not 1 <= args.seconds <= MAX_SECONDS:
        raise ValueError('At most 60 CPU and wall seconds required')
    target = args.script.resolve(strict=True)
    if not target.is_file():
        raise ValueError('One existing Python script required')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the new receipt before execution. A failed attempt cannot replace it.
    with args.report.open('x') as receipt:
        began = time.monotonic()
        peak_rss = peak_host = samples = 0
        code = 1
        reason = error = None
        setup_complete = False
        usage_start = resource.getrusage(resource.RUSAGE_SELF)

        def check(signum=None, frame=None):
            nonlocal peak_rss, peak_host, samples
            rss, host = read_budget()
            peak_rss = max(peak_rss, rss)
            peak_host = max(peak_host, host)
            samples += 1
            if rss > RSS:
                raise ResourceStop('SELF_RSS')
            if host > HOST_USED:
                raise ResourceStop('HOST_USED')
            if shutil.disk_usage(args.report.parent).free < DISK_RESERVE:
                raise ResourceStop('DISK_RESERVE')
            if time.monotonic() - began > args.seconds:
                raise ResourceStop('WALL_TIME')

        def cpu_stop(signum, frame):
            raise ResourceStop('CPU_TIME')

        try:
            for name in THREAD_VARIABLES:
                os.environ[name] = '1'
            os.environ.update(COIN_CLOUD_BOUNDED='1', CUDA_VISIBLE_DEVICES='',
                              PYTHONDONTWRITEBYTECODE='1')
            sys.dont_write_bytecode = True
            resource.setrlimit(resource.RLIMIT_AS, (ADDRESS, ADDRESS))
            resource.setrlimit(resource.RLIMIT_CPU, (max(1, args.seconds - 1), args.seconds))
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
            check()
            sys.addaudithook(no_children)
            signal.signal(signal.SIGALRM, check)
            signal.signal(signal.SIGXCPU, cpu_stop)
            signal.setitimer(signal.ITIMER_REAL, SAMPLE_SECONDS, SAMPLE_SECONDS)
            setup_complete = True
            sys.path.insert(0, str(target.parent))
            sys.argv = [str(target), *args.script_args]
            runpy.run_path(str(target), run_name='__main__')
            check()
            code = 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
            if code:
                error = 'SystemExit: ' + str(exc.code)
        except ResourceStop as exc:
            reason = str(exc)
            code = 124
        except BaseException as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            traceback.print_exc()
            code = 1
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            usage = resource.getrusage(resource.RUSAGE_SELF)
            kernel_peak = int(usage.ru_maxrss) * 1024
            if kernel_peak > RSS and reason is None:
                reason = 'KERNEL_PEAK_RSS'
                code = 124
            report = dict(
                exit_code=code, stop_reason=reason, error=error,
                elapsed_seconds=time.monotonic() - began,
                measured_CPU_seconds=(usage.ru_utime + usage.ru_stime -
                                      usage_start.ru_utime - usage_start.ru_stime),
                maximum_sampled_self_RSS_bytes=peak_rss,
                kernel_self_peak_RSS_bytes=kernel_peak,
                kernel_peak_method='Linux getrusage(RUSAGE_SELF).ru_maxrss * 1024',
                maximum_host_used_bytes=peak_host, RSS_samples=samples,
                RSS_sampling_seconds=SAMPLE_SECONDS,
                peak_is_sampled_not_kernel_peak=False,
                active_RSS_enforcement='SIGALRM self check; sampled, not cgroup',
                self_RSS_stop_bytes=RSS, per_process_address_limit_bytes=ADDRESS,
                host_used_stop_bytes=HOST_USED, disk_reserve_bytes=DISK_RESERVE,
                cpu_soft_limit_seconds=max(1, args.seconds - 1),
                cpu_hard_limit_seconds=args.seconds,
                wall_limit_seconds=args.seconds,
                affinity_cpu_count=len(os.sched_getaffinity(0)),
                thread_limit=1, gpu_enabled=False, swap_active=False,
                setup_complete=setup_complete, child_processes_allowed=False,
                shared_cgroup_enforcement=False,
                script=str(target), script_args=args.script_args,
                script_SHA256=hashlib.sha256(target.read_bytes()).hexdigest(),
                capsule_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
            json.dump(report, receipt, indent=2, allow_nan=False)
            receipt.write('\n')
            receipt.flush()
            os.fsync(receipt.fileno())
    raise SystemExit(code)


if __name__ == '__main__':
    main()

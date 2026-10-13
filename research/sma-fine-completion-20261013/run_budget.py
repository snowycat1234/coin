"""Single-batch budget gate; changing state-root never authorizes reruns."""
from __future__ import annotations
from pathlib import Path

def stop_on_worker_failure(exit_code):
    """Program/resource/integrity failure stops peers; audited economic halt is exit0.

    All fixed cases stay in the experiment. A successfully audited negative
    economic case may be partial and never earns full-calendar/paid-flat status.
    Its return code is still zero so its outcome cannot censor other fixed arms.
    """
    if not isinstance(exit_code,int) or isinstance(exit_code,bool):
        raise ValueError('A completed worker integer exit code is required')
    return exit_code!=0

def ensure_single_unstarted_batch(module_root: Path, requested_root: Path):
    root=Path(module_root).resolve();requested=Path(requested_root)
    if requested.parent.resolve()!=root or not requested.name.startswith('state') or requested.is_symlink():
        raise ValueError('New state* root must be directly under this module')
    if requested.exists(): raise RuntimeError('Requested state root already exists; no rerun or resume')
    for candidate in root.glob('state*'):
        if candidate.is_symlink(): raise RuntimeError('Unknown state symlink prevents a second batch')
        if not candidate.is_dir(): continue
        if ((candidate/'RUN_BINDING.json').exists()
                or any(candidate.glob('*_FINE_ORIGINAL'))
                or any(candidate.glob('*/BINDING.json'))
                or any(candidate.glob('*/recovery/POINTER.json'))):
            raise RuntimeError('Fixed three-wallet historical batch already reserved or started; new state root cannot rerun it')
    return {'status':'PASS_SINGLE_UNSTARTED_BATCH','historical_wallets_created':0}

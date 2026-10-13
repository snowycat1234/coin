"""Single-batch budget gate; changing state-root never authorizes reruns."""
from __future__ import annotations
from pathlib import Path

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
            raise RuntimeError('Fixed six-wallet historical batch already reserved or started; new state root cannot rerun it')
    return {'status':'PASS_SINGLE_UNSTARTED_BATCH','historical_wallets_created':0}

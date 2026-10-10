"""Bounded metadata-only decision after the original six-task controller exits."""
import json
from pathlib import Path

import torch

from RUNTIME_EXTENSION import (
    AUTH_COMMIT,
    AUTH_PUBLIC_PATH,
    prepare_continuation,
    verify_permission,
    verify_prepared,
)
from modules.temporal_two_expert.checkpoint import _atomic_json
from modules.temporal_two_expert.exact import sha


if __name__ == "__main__":
    state = Path('/workspace/coin-state/work/temporal-two-expert-20261009')
    output = state/'small-tuning-run'
    permission_path = Path('/workspace/coin-temporal/research/temporal-small-tuning-run-20261010/RUNTIME_EXTENSION_AUTHORIZATION.json')
    prepared_path = state/'tuning-tools/RUNTIME_EXTENSION_PREPARED.json'
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    permission = verify_permission(permission_path, AUTH_COMMIT, AUTH_PUBLIC_PATH)
    prepared = verify_prepared(
        prepared_path,
        'cb3f8dce53b735581b3c8e87bed3bc3ee0b70a56',
        'research/temporal-small-tuning-run-20261010/runtime-extension/RUNTIME_EXTENSION_PREPARED.json',
        permission,
    )
    preparation = prepare_continuation(output, permission, original_pid=32532)
    if preparation['status'] != 'NO_EXTENSION_NEEDED':
        preparation['prepared_receipt'] = prepared
        _atomic_json(output/'RUNTIME_EXTENSION_5400.json', preparation)
        _atomic_json(output/'RUNTIME_5400_ORIGINALS/RECEIPT.json', preparation)
    decision = dict(
        status=preparation['status'],
        conditional_extension_prepared=preparation['status'] != 'NO_EXTENSION_NEEDED',
        optimizer_updates=0,
        model_inferences=0,
        wallet_rollouts=0,
        permission=permission,
        prepared_receipt=prepared,
        script_SHA256=sha(Path(__file__)),
        reserve_read=False,
    )
    _atomic_json(output/'RUNTIME_EXTENSION_DECISION.json', decision)
    print(json.dumps(dict(status=decision['status'], optimizer_updates=0)))

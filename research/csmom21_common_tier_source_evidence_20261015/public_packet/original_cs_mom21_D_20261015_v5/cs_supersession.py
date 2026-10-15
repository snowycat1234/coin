"""Append-only manual failed-claim supersession under the original global lease.

The evidence packet grants no execution. A fresh exact reviewed financial GO
must authorize its hash. Original claims remain byte-exact; one permanent
exclusive consumption per old claim prevents cross-version/output replay.
"""
import os
from pathlib import Path

import cs_common as c
import cs_process_runtime as r
import cs_entry as entry

SCOPE_SHA = '9a5ef547d61272d5eb0bfb1b61fef8005a752d82f4e0007d18cbe65f06445a8a'
PACKET_SHA = '3adbb11d8fe4950846c641725d3846d4baaf5ef6757f885ab6b6dde9761cb78a'
STABLE_REGISTRY_REL = 'original_cs_mom21_D_20261015_v4/EXECUTION_CLAIMS'
FAILED_CELLS = ('2022_CSMOM21_COMMON_TIER_LOW_D', '2022_CSMOM21_COMMON_TIER_MID_D')


def registry_root():
    return c.ROOT / STABLE_REGISTRY_REL


def packet():
    raw = c.exact(c.HERE / 'FAILED_ATTEMPT_SUPERSESSION_PACKET.json', PACKET_SHA)
    value = c.exact_object(raw)
    if (value.get('schema') != 'EXACT_CSMOM21_FAILED_PREFINANCE_CLAIM_SUPERSESSION_EVIDENCE_V1'
            or value.get('retry_or_claim_supersession_authorized') is not False
            or value.get('financial_execution_authorized') is not False
            or tuple(value['failed_claims']) != FAILED_CELLS
            or value.get('stable_registry') != STABLE_REGISTRY_REL):
        raise ValueError('EXACT_NONAUTHORIZING_FAILED_CLAIM_PACKET_REQUIRED')
    return value


def validate_evidence():
    value = packet()
    for name, pin in value['evidence'].items():
        c.exact(c.ROOT / c.relative(name), pin['SHA256'], pin['bytes'])
    for cell, pin in value['failed_claims'].items():
        raw = c.exact(c.ROOT / c.relative(pin['path']), pin['SHA256'], pin['bytes'])
        old = c.exact_object(raw)
        if (old['cell_id'] != cell or old['root_GO_SHA256'] != value['failed_root_GO_SHA256']
                or old['preparation_SHA256'] != value['preparation_SHA256']):
            raise ValueError('EXACT_PRESERVED_FAILED_CLAIM_REQUIRED')
    return value


def claim_path(cell_id):
    value = packet()
    base = registry_root() / SCOPE_SHA
    if cell_id in FAILED_CELLS:
        return base / 'SUPERSESSION_CONSUMPTIONS' / (value['failed_claims'][cell_id]['SHA256'] + '.json')
    return base / (cell_id + '.json')


def reserve(*, cell_id, metadata, go):
    if cell_id not in entry.tranche_cells(entry.FIRST6):
        raise ValueError('ONLY_EXACT_FIRST6_CLAIMS_ADMITTED')
    value = validate_evidence()
    if (go.get('manual_failed_pre_finance_claim_supersession_authorized') is not True
            or go.get('failed_claim_supersession_packet_SHA256') != PACKET_SHA
            or go.get('stable_cross_version_claim_registry') != STABLE_REGISTRY_REL
            or go.get('automatic_retry_authorized') is not False
            or go.get('preparation_SHA256') != value['preparation_SHA256']):
        raise ValueError('FRESH_ROOT_GO_BOUND_MANUAL_SUPERSESSION_REQUIRED')
    # Caller must hold the same inherited original-D global controller lease.
    fd = r._CONTROLLER_LEASE_FD
    if type(fd) is not int:
        raise ValueError('STABLE_CONTROLLER_LEASE_REQUIRED_BEFORE_CLAIM')
    canonical = (registry_root() / SCOPE_SHA / 'CONTROLLER_LEASE.lock').stat()
    held = os.fstat(fd)
    if (held.st_dev, held.st_ino) != (canonical.st_dev, canonical.st_ino):
        raise ValueError('EXACT_STABLE_CONTROLLER_LEASE_INODE_REQUIRED')
    if cell_id not in FAILED_CELLS:
        return r.claim_launch(registry_root(), cell_id=cell_id, manifest_sha256=SCOPE_SHA, metadata=metadata)
    path = claim_path(cell_id)
    path.parent.mkdir(exist_ok=True)
    record = dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1', manifest_SHA256=SCOPE_SHA,
        cell_id=cell_id, claim_UTC=r.utc(), controller_PID=os.getpid(), status='RESERVED_BEFORE_PROCESS_SPAWN',
        automatic_clear_or_retry=False, financial_snapshot_resume=False, **metadata)
    record.update(superseded_claim_SHA256=value['failed_claims'][cell_id]['SHA256'],
                  failed_claim_supersession_packet_SHA256=PACKET_SHA,
                  one_use_consumption_permanent=True, original_claim_unchanged=True)
    try:
        r.save(path, record)
    except FileExistsError:
        raise RuntimeError('FAILED_CLAIM_SUPERSESSION_ALREADY_CONSUMED_NO_RETRY:' + cell_id)
    directory = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return path

"""One initial-short-prior ablation; all other conditions frozen."""

from pathlib import Path

from modules.temporal_scaler_refit import protocol as prior
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = prior.ROOT
ARM = "NEUTRAL_SHORT1137_TRAIN1273_FRESH256"


def protocol():
    p = dict(prior.protocol())
    p.pop("identity")
    p.update(
        schema="ONE_NEUTRAL_SHORT_INITIALIZATION_V1",
        arm=ARM,
        hypothesis=(
            "Conservative appended-head1% prior restricts short exploration under fresh "
            "low-lr256 training; neutral1/3 prior may improve allocation, profitability "
            "unproven"
        ),
        comparator=(
            "Frozen1137/1273 model at2d280cbba43158157890fd9280a9e1038724696e; reuse "
            "both historical scores"
        ),
        normalization=(
            "Identical1273 training-window valid-only scaler identity "
            "fe3b4cc5f7f58343efa10afc660924f766b8e1c7198c991af1470d5aeb678b55"
        ),
        scaler_refits=0,
        initialization=(
            "Only r_head.bias changes from logit(.01) to logit(1/3); all other "
            "parameter bytes and RNG identical; initial CASH=.5 and VOL=CS=SHORT=1/6"
        ),
        compute=(
            "Same1137 data/256updates/seed/lr/architecture/dateweights/costs/risk, one "
            "fresh fit; no grid or restart"
        ),
        adoption=(
            "Report both seen periods regardless of sign and in-training SHORT "
            "requests. No live promotion, no best-epoch selection, stop this single "
            "initialization ablation after scoring."
        ),
    )
    return dict(p, identity=digest(p))


def task(task_id=ARM):
    if task_id != ARM:
        raise ValueError("Only one neutral short candidate")
    return dict(task_id=ARM, lr=0.0003, wallet_equal_mix=0.0)


def sources():
    return {
        **prior.sources(),
        **{str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


DECISION_SHA = protocol()["identity"]

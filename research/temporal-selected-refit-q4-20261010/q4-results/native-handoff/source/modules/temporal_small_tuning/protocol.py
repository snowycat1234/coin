"""Only the reviewed six tasks and their exact immutable settings."""

import json
from pathlib import Path

from modules.temporal_april_transfer.protocol import sources as original_sources
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "research/temporal-small-tuning-plan-20261010/PLAN.json"
PLAN_COMMIT = "8487347381b5d96f783cb17f6936415f457d0498"
PLAN_SHA = "3413d12255e2adcd7a8c5df28849c50db8ef9476685af59dd29b19dce50e03e1"


def plan():
    if sha(PLAN_PATH) != PLAN_SHA:
        raise ValueError("Reviewed plan bytes changed")
    return json.loads(PLAN_PATH.read_text())


def task(task_id):
    matches = [t for t in plan()["actual_fit_tasks"] if t["task_id"] == task_id]
    if len(matches) != 1:
        raise ValueError("Exactly one approved six-fit task required")
    return matches[0]


def sources():
    extra = [*Path(__file__).parent.rglob("*.py"), PLAN_PATH]
    return {**original_sources(), **{str(p.relative_to(ROOT)): sha(p) for p in extra}}


def protocol():
    p = plan()
    result = {
        k: p[k]
        for k in ("common", "selection", "candidate_settings", "actual_fit_tasks", "compute")
    }
    result.update(
        schema="APPROVED_SIX_FRESH_TEMPORAL_TUNING_V1",
        reviewed_plan_commit=PLAN_COMMIT,
        reviewed_plan_SHA256=PLAN_SHA,
        seed=20261009,
        initial_fits=6,
        final_refit="NOT_RUN; return selected recipe and frozen step count",
        reserve="NO_RESERVED_OUTCOME_READ_OR_SELECTION",
        resource_slice_training_seconds=1100,
        prior_warm_mixed_result="date-502.47/mixed-521.17USDT; old warm negative result retained, no promise of improvement",
    )
    return dict(result, identity=digest(result))

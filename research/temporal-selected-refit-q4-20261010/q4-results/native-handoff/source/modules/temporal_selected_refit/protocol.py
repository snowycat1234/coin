"""One selected recipe; evaluation code is outside this immutable fitting graph."""

import json
from pathlib import Path

from modules.temporal_small_tuning.protocol import sources as frozen_sources
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = ROOT / "research/temporal-selected-refit-q4-20261010/DECISION.json"
DECISION_SHA = "a4938836c495a5f489b05ca1bdc0e6093f35db1c3b4ecba4f53788303b8ffc5f"


def protocol():
    if sha(DECISION_PATH) != DECISION_SHA:
        raise ValueError("Frozen selected decision bytes changed")
    result = json.loads(DECISION_PATH.read_text())
    return dict(result, identity=digest(result))


def task(task_id):
    p = protocol()
    if task_id != p["task_id"]:
        raise ValueError("Only one approved full773 refit task required")
    return {k: p[k] for k in ("task_id", "lr", "wallet_equal_mix")}


def sources():
    paths = [*Path(__file__).parent.glob("*.py"), DECISION_PATH]
    return {**frozen_sources(), **{str(p.relative_to(ROOT)): sha(p) for p in paths}}

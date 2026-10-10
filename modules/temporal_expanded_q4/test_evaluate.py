import json
from types import SimpleNamespace

import numpy as np
import pytest

from . import evaluate
from .evaluate import checked_request, differences


def fixture():
    decisions = np.arange(92, dtype=np.int64) * 86400000000 + 10000000000000
    episode = SimpleNamespace(
        eligible=np.ones((92, 6), dtype=bool),
        windows=SimpleNamespace(
            decision_us=decisions,
            valid=np.ones((92, 64, 5, 24), dtype=bool),
            available_us=np.broadcast_to(decisions[:, None, None, None] - 1, (92, 64, 5, 24)),
            completed_us=np.broadcast_to(decisions[:, None] - 1, (92, 64)),
        ),
        expert_input_available_us=np.broadcast_to(decisions[:, None], (92, 18)),
    )
    model = SimpleNamespace(contract=dict(allowed_actions=["CASH", "VOL_MANAGED_HOLD", "CSMOM21"]))
    request = np.tile([0.1, 0.5, 0, 0, 0.4, 0], (92, 1))
    return episode, model, request


def test_request_enforces_dynamic_masks_causal_clock_and_canonical_order():
    episode, model, request = fixture()
    checked_request(request, episode, model)
    episode.eligible[0, 4] = False
    with pytest.raises(ValueError):
        checked_request(request, episode, model)
    episode.eligible[0, 4] = True
    episode.expert_input_available_us = episode.expert_input_available_us.copy()
    episode.expert_input_available_us[0, 0] += 1
    with pytest.raises(ValueError):
        checked_request(request, episode, model)


def test_saved_comparator_difference_without_wallet_or_inference():
    actual = dict(net_PnL=2, utility_sum=0.2, maximum_daily_drawdown=0.05)
    saved = dict(old=dict(net_PnL=1, utility_sum=0.1, maximum_daily_drawdown=0.08))
    delta = differences(actual, saved)["old"]
    assert delta["net_PnL"] == 1 and delta["utility_sum"] == 0.1
    assert delta["maximum_daily_drawdown"] == pytest.approx(-0.03)


def test_public_source_gate_rejects_changes_before_q4_load(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate, "ROOT", tmp_path)
    expected = {"one.py": "frozen_source_SHA"}
    monkeypatch.setattr(evaluate, "sources", lambda: expected)
    path = "research/temporal-expanded-refit-q4-20261010/frozen/EVALUATION_SOURCES.json"
    (tmp_path / path).parent.mkdir(parents=True)
    (tmp_path / path).write_text(json.dumps(expected))
    terminal = dict(checkpoint_SHA256="frozen_checkpoint_SHA")
    public = dict(
        status="PASS_ALL_PUBLIC_BYTES",
        files=[
            dict(
                path="research/temporal-expanded-refit-q4-20261010/frozen/one.pt",
                SHA256=terminal["checkpoint_SHA256"],
            ),
            dict(path=path, SHA256=evaluate.sha(tmp_path / path)),
        ],
    )
    evaluate.publication_gate(public, terminal, "one.pt")
    monkeypatch.setattr(evaluate, "sources", lambda: {"one.py": "changed_source_SHA"})
    with pytest.raises(ValueError, match="source set changed"):
        evaluate.publication_gate(public, terminal, "one.pt")
    public["files"][-1]["SHA256"] = "not_publicly_verified"
    with pytest.raises(ValueError, match="Published pre-score"):
        evaluate.publication_gate(public, terminal, "one.pt")

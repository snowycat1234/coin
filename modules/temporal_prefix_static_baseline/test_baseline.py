import numpy as np

from modules.temporal_contrast21_probe.probe import DAY_US

from .baseline import EXPERTS, choose, identity


def cache():
    d = np.arange(5, dtype=np.int64) * DAY_US
    return dict(
        train_decisions=d,
        train_label_available=d + 21 * DAY_US + 60000001,
        train_ready=np.ones(5, bool),
        train_y=np.zeros((5, 2)),
    )


def test_strict_maturity_ignores_equal_cutoff_and_later_winner():
    c = cache()
    cutoff = c["train_label_available"][2]
    labels = np.array(
        [[0.01, 0.02, -0.01], [0.01, 0.04, -0.02], [100, 0, 0], [200, 0, 0], [300, 0, 0]]
    )
    selected, means, rows = choose(labels, c, cutoff)
    assert selected == 1 and EXPERTS[selected] == "CSMOM21"
    np.testing.assert_array_equal(rows, [0, 1])
    labels[2:] = [-1e6, 1e6, 1e9]
    repeated, again, _ = choose(labels, c, cutoff)
    assert repeated == selected
    np.testing.assert_array_equal(means, again)


def test_negative_means_still_choose_expert_without_cash_candidate():
    c = cache()
    labels = np.tile([-0.04, -0.02, -0.03], (5, 1))
    selected, _, _ = choose(labels, c, c["train_label_available"][-1] + 1)
    assert selected == 1 and len(EXPERTS) == 3 and "CASH" not in EXPERTS


def test_exact_tie_uses_fixed_order_and_identity_survives_json_roundtrip():
    import json

    c = cache()
    selected, _, _ = choose(np.ones((5, 3)), c, c["train_label_available"][-1] + 1)
    assert selected == 0
    value = dict(selected=EXPERTS[selected], mean=[1.0, 1.0, 1.0])
    assert identity(value) == identity(json.loads(json.dumps(value)))

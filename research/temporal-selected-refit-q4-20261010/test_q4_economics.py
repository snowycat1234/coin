"""Pinned economic reads only; no inference, training or economic wallets."""

from pathlib import Path

import numpy as np
import pytest

from modules.temporal_q4_reserved.data import END, START
from modules.temporal_q4_reserved.economics import economics
from modules.temporal_two_expert.inputs import DAY_US

SOURCE = Path("/workspace/coin-state/work/temporal-two-expert-20261009/selected-refit/q4-economics")


def test_real_unpadded_economics_and_exact_clocks():
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    prices, funding, receipt = economics(SOURCE, decisions)
    assert prices.shape == (92, 5) and funding.shape == (91, 5)
    assert receipt["synthetic_economic_rows"] == 0
    assert receipt["source_commit"] == "152606ad56fe6d8943b27ce89c8c57e2068ee944"
    assert max(receipt["independent_funding_max_error"].values()) < 1e-10
    with pytest.raises(AssertionError):
        economics(SOURCE, decisions + DAY_US)


def test_unknown_or_modified_economics_rejected(tmp_path):
    (tmp_path / "CONSUMER_INDEX.json").write_bytes(b"altered")
    with pytest.raises(ValueError, match="Exact supplied"):
        economics(tmp_path, np.arange(START, END, DAY_US, dtype=np.int64))

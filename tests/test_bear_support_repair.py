"""Hand examples: add observed rows without changing frozen observations."""
import math

import pandas as pd
import pytest

from modules.collector_research.pipeline.normalize import mark_funding
from scripts.research.repair_bear_support import merge_observed


BASE_MS = 1_704_067_200_000


def observed_minutes():
    """Four real-shaped canonical minutes; prices distinguish every row."""
    rows = []
    for minute in range(4):
        stamp = BASE_MS + minute * 60_000
        price = 100.0 + minute
        rows.append(dict(
            symbol='BTCUSDT', timestamp_ms=stamp, open=price,
            high=price + 2.0, low=price - 1.0, close=price + 1.0,
            volume=1.0, close_time_ms=stamp + 59_999,
            quote_volume=100.0, trades=1, taker_buy_volume=.25,
            taker_buy_quote_volume=25.0, ignore=0.0,
            available_us=(stamp + 60_000) * 1_000,
        ))
    return pd.DataFrame(rows)


def test_add_only_a_truly_missing_minute_and_leave_inputs_unchanged():
    expected = observed_minutes().iloc[:3].reset_index(drop=True)
    old = expected.iloc[[2, 0]].copy()
    new = expected.iloc[[1]].copy()
    old_before, new_before = old.copy(deep=True), new.copy(deep=True)

    merged = merge_observed(old, new)

    pd.testing.assert_frame_equal(merged.reset_index(drop=True), expected)
    pd.testing.assert_frame_equal(old, old_before)
    pd.testing.assert_frame_equal(new, new_before)
    assert merged.timestamp_ms.is_unique
    assert merged.timestamp_ms.is_monotonic_increasing


@pytest.mark.parametrize('repeat_new', [False, True])
def test_identical_overlap_is_allowed_without_duplicate_output(repeat_new):
    old = observed_minutes().iloc[:2].copy()
    new = old.iloc[[0]].copy()
    if repeat_new:
        new = pd.concat([new, new], ignore_index=True)
    old_before, new_before = old.copy(deep=True), new.copy(deep=True)

    merged = merge_observed(old, new)

    pd.testing.assert_frame_equal(merged.reset_index(drop=True), old.reset_index(drop=True))
    pd.testing.assert_frame_equal(old, old_before)
    pd.testing.assert_frame_equal(new, new_before)
    assert merged.timestamp_ms.is_unique


@pytest.mark.parametrize('field,replacement', [
    ('close', 101.25),
    # A single floating-point step must not be accepted through allclose.
    ('close', math.nextafter(101.0, math.inf)),
    ('volume', 1.25),
    ('available_us', (BASE_MS + 60_000) * 1_000 + 1),
    ('symbol', 'ETHUSDT'),
])
def test_same_timestamp_conflicting_observation_is_rejected(field, replacement):
    old = observed_minutes().iloc[:2].copy()
    new = old.iloc[[0]].copy()
    new.loc[new.index[0], field] = replacement
    old_before, new_before = old.copy(deep=True), new.copy(deep=True)

    with pytest.raises(ValueError):
        merge_observed(old, new)

    pd.testing.assert_frame_equal(old, old_before)
    pd.testing.assert_frame_equal(new, new_before)


def test_restored_mark_does_not_relax_strict_funding_tie():
    event_ms = BASE_MS + 120_000
    events = pd.DataFrame(dict(calc_time_ms=[event_ms, event_ms + 1]))
    marks = pd.DataFrame(dict(
        available_us=[(BASE_MS + 60_000) * 1_000, event_ms * 1_000],
        close=[100.0, 200.0],
    ))

    result = mark_funding(events, marks)

    # At the exact boundary use the strictly earlier mark; one millisecond
    # later the newly available mark is causal and may be used.
    assert result.past_mark_price.tolist() == [100.0, 200.0]
    assert result.past_mark_available_us.tolist() == marks.available_us.tolist()
    missing_earlier = mark_funding(events, marks.iloc[[1]])
    assert math.isnan(missing_earlier.past_mark_price.iloc[0])
    assert missing_earlier.past_mark_price.iloc[1] == 200.0
    stale_only = mark_funding(events, marks.iloc[[0]])
    assert stale_only.past_mark_price.iloc[0] == 100.0
    assert math.isnan(stale_only.past_mark_price.iloc[1])

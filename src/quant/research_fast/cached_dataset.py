"""Bounded daily cache of the accepted shared dataset; no window materialization."""

from functools import lru_cache

import numpy as np

from .dataset import (
    BAR_US,
    DAY_US,
    LABEL_COLUMNS,
    LABEL_LAG_US,
    PAST_BARS,
    TARGET_STREAMS,
    TASKS,
    FastSequenceDataset,
    _sha,
    day_us,
    feature_matrix,
    label_table,
)


class CachedSequenceDataset(FastSequenceDataset):
    """Reuse all source, split, label, scaler and Torch bridge implementations.

    Store at most 24 daily [bars,F] matrices plus label tables in RAM. The views
    created by normalized() share this cache. Never store [samples,256,F].
    """

    def __init__(self, shards, *, mode="smoke"):
        super().__init__(shards, mode=mode)
        self._cached_day = lru_cache(maxsize=24)(self._build_day)

    def _build_day(self, day):
        first = max(
            min(s.start_us for s in self.shards if s.stream == stream)
            for stream in self.shards_streams
        )
        last = min(
            max(s.end_us for s in self.shards if s.stream == stream)
            for stream in self.shards_streams
        )
        start = max(first, day_us(day) - PAST_BARS * BAR_US)
        end = min(last, day_us(day) + DAY_US + LABEL_LAG_US)
        joint = self.joint_rows(start, end)
        x, labels = feature_matrix(joint), label_table(joint)
        x.flags.writeable = False
        return start, x, labels

    @property
    def shards_streams(self):
        return {s.stream for s in self.shards}

    def __getitem__(self, index):
        if self.index is None or not 0 <= index < len(self.index):
            raise IndexError("No such prepared common endpoint")
        decision = int(self.index[index])
        if self.normalizer is not None:
            lower, upper, mature_by = self.fold.interval(self.split)
            if not lower <= decision < upper or decision + LABEL_LAG_US > mature_by:
                raise ValueError("Endpoint outside bound fold/split or label maturity")
        day = next(day for day in self.days if day_us(day) <= decision < day_us(day) + DAY_US)
        lower, upper = decision - PAST_BARS * BAR_US, decision + LABEL_LAG_US
        # A cached result must not conceal a replaced source file.
        for source in self.shards:
            if source.start_us < upper and source.end_us > lower:
                actual = source.path.stat()
                if (actual.st_size, actual.st_mtime_ns) != self._stats[source.path]:
                    raise ValueError("Cached source file changed")
        start, values, all_labels = self._cached_day(day)
        position = (decision - start) // BAR_US
        x = values[position - PAST_BARS : position].copy()
        labels = all_labels.row(position - 1, named=True)
        if x.shape != (PAST_BARS, 68) or not labels["label_valid"]:
            raise ValueError("Cached shared window/label no longer valid")
        if self.normalizer is not None:
            if self.split != "train" and self.normalizer.fit_last_us >= decision:
                raise ValueError("Scaler contains current/future inference information")
            x = self.normalizer.transform(x)
        y = np.array([labels[name] for name in LABEL_COLUMNS], np.float32).reshape(
            len(TARGET_STREAMS), len(TASKS)
        )
        transformed = (
            self.target_normalizer.transform(y).astype(np.float32)
            if self.target_normalizer
            else y.copy()
        )
        return {
            "sample_id": _sha((self.contract_sha256, decision)),
            "decision_us": decision,
            "x": x,
            "y": transformed,
            "y_raw": y,
            "target_units": "standardized" if self.target_normalizer else "original",
            "label_available_us": labels["label_available_us"],
            "qa": {
                k: v
                for k, v in labels.items()
                if k not in LABEL_COLUMNS and k not in {"decision_us", "label_valid"}
            },
            "status": "FORMAL_DATA_READY" if self.mode == "formal" else "SMOKE_ONLY",
        }

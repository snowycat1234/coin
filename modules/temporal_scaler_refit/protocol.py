"""One controlled training-union normalization change, no search or clipping."""

from pathlib import Path

from modules.temporal_cached_july.protocol import sources as cached_sources
from modules.temporal_expanded_refit import protocol as prior
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = Path(__file__).resolve().parents[2]
ARM = "EXPANDED1137_TRAIN1273_FRESH256"
SOURCE_COMMIT = prior.SOURCE_COMMIT
CONSUMER_SHA = prior.CONSUMER_SHA


def protocol():
    p = dict(prior.protocol())
    p.pop("identity")
    p.update(
        schema="ONE_EXPANDED1137_TRAIN1273_FRESH256_V1",
        arm=ARM,
        normalization=(
            "same mean/std valid-only shared-assets ddof0 algorithm; refit exactly1273 "
            "unique rows in six preMay training windows; no clipping/no reserve"
        ),
        scaler_identity="bound_in_prefit_READY_and_SCALER",
        scaler_rows=1273,
        scaler_refits=1,
        comparator=(
            "same1137data fixed907 scaler fresh256 "
            "at0e5f41c255f315dccdd922de9a4ce762a1f40771; saved July/Q4 controls reused"
        ),
        hypothesis=(
            "2021 tail shift causes GRU gate saturation under old907 normalization; "
            "economic effect unproven"
        ),
        compute=(
            "same data, updates, seed, lr, architecture, costs and weights; "
            "normalization buffers alone change at initialization"
        ),
        Q4=(
            "one frozen candidate on same seen Q4 and July periods after terminal "
            "publication; no untouched OOS claim"
        ),
        native="no new native wallet in this module",
        adoption="report both periods and risk; no live promotion; no second recipe if negative",
    )
    return dict(p, identity=digest(p))


def task(task_id=ARM):
    if task_id != ARM:
        raise ValueError("Only one train1273 normalization candidate")
    return dict(task_id=ARM, lr=0.0003, wallet_equal_mix=0.0)


def sources():
    return {
        **prior.sources(),
        **cached_sources(),
        **{
            str(p.relative_to(ROOT)): sha(p)
            for folder in (Path(__file__).parent, ROOT / "modules/temporal_q4_reserved")
            for p in sorted(folder.glob("*.py"))
        },
    }


DECISION_SHA = protocol()["identity"]

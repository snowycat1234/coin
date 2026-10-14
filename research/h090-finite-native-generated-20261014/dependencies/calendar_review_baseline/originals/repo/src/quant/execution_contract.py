"""One causal timing and cost contract for V2 research and paper engines.

Decision time is the complete bar's logical availability, distinct from the wall
time when a live packet was received. Receipt guards still apply to every live fill.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

MINUTE_US = 60_000_000


@dataclass(frozen=True)
class ExecutionContractV2:
    version: str = "execution_v2"
    cost_version: str = "spot_taker_proxy_cost_v1"
    risk_version: str = "spot_long_cash_risk_v1"
    latency_minutes: int = 1
    max_order_wait_minutes: int = 5
    fee_bps: float = 10.0
    half_spread_floor_bps: float = 1.0
    extra_slippage_bps: float = 4.0
    participation_rate: float = 0.001
    max_weight: float = 0.30
    max_gross: float = 0.60
    annual_vol_target: float = 0.10
    min_notional: float = 10.0

    def __post_init__(self) -> None:
        canonical = (
            self.version == "execution_v2"
            and self.cost_version == "spot_taker_proxy_cost_v1"
            and self.risk_version == "spot_long_cash_risk_v1"
            and self.latency_minutes == 1 and self.max_order_wait_minutes == 5
            and self.fee_bps == 10 and self.half_spread_floor_bps == 1
            and self.extra_slippage_bps == 4 and self.participation_rate == 0.001
            and self.max_weight == 0.30 and self.max_gross == 0.60
            and self.annual_vol_target == 0.10 and self.min_notional == 10
        )
        if not canonical:
            raise ValueError("ExecutionContractV2 canonical parameters are frozen")

    def digest(self) -> str:
        payload = {**asdict(self), "source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest()}
        return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()

    def earliest_execution_us(self, decision_us: int, *, extra_delay_minutes: int = 0) -> int:
        if (not isinstance(decision_us, int) or isinstance(decision_us, bool)
                or decision_us < 0):
            raise ValueError("decision_us must be a nonnegative integer")
        if (not isinstance(extra_delay_minutes, int) or isinstance(extra_delay_minutes, bool)
                or extra_delay_minutes < 0):
            raise ValueError("stress delay must be a nonnegative integer")
        return ((decision_us + MINUTE_US - 1) // MINUTE_US
                + self.latency_minutes + extra_delay_minutes) * MINUTE_US

    def capacity_minute_us(self, execution_us: int) -> int:
        if not isinstance(execution_us, int) or execution_us < MINUTE_US:
            raise ValueError("execution timestamp has no previous complete minute")
        return execution_us // MINUTE_US * MINUTE_US - MINUTE_US

    def expiry_us(self, decision_us: int, *, extra_delay_minutes: int = 0) -> int:
        return (self.earliest_execution_us(decision_us, extra_delay_minutes=extra_delay_minutes)
                + self.max_order_wait_minutes * MINUTE_US)

    def order_times_ms(self, decision_us: int, received_ms: int) -> dict[str, int | str]:
        if received_ms * 1000 < decision_us:
            raise ValueError("signal cannot be received before logical availability")
        return {
            "decision_ms": decision_us // 1000,
            "decision_us": decision_us,
            "signal_received_ms": received_ms,
            "not_before_ms": self.earliest_execution_us(decision_us) // 1000,
            "expires_ms": self.expiry_us(decision_us) // 1000,
            "execution_contract_version": self.version,
        }

    @staticmethod
    def execution_rate(half_spread_bps: float, extra_slippage_bps: float) -> float:
        if any(not math.isfinite(value) or value < 0
               for value in (half_spread_bps, extra_slippage_bps)):
            raise ValueError("execution costs must be finite and nonnegative")
        return (half_spread_bps + extra_slippage_bps) / 10_000

    @staticmethod
    def rebalance_buffer(execution_rate: float, fee_rate: float, max_gross: float) -> float:
        """Fee is charged on the actual fill price, including the spread/slippage."""
        return max(0.0, 1 - 2 * max_gross * (
            execution_rate + (1 + execution_rate) * fee_rate))

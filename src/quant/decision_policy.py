"""Fixed alpha holding policy, measured from actual first fill in either engine."""

from .execution_contract import MINUTE_US


def holding_period_complete(now_us: int, first_fill_us: int, hold_minutes: int,
                            risk_forced_exit: bool) -> bool:
    if hold_minutes not in (0, 120) or not isinstance(risk_forced_exit, bool):
        raise ValueError("Only reference/no-hold or preregistered two-hour alpha policy allowed")
    return (risk_forced_exit or hold_minutes == 0
            or now_us - first_fill_us >= hold_minutes * MINUTE_US)

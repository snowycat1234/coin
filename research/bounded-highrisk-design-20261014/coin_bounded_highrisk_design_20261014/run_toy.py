"""Fixed generated tests only. No data/file/market arguments are accepted."""
import json
from source_preflight import verify
from toy_fixtures import generated_case, generated_finite_program

NAMES = (
    "BENIGN_PAID_TERMINAL", "CORRELATED_ADVERSE_GAP", "FUNDING_DRAIN",
    "SHORT_ISOLATED_LIQUIDATION_GAP", "SHORT_ISOLATED_BANKRUPTCY_GAP",
    "ZERO_LIQUIDITY_TERMINAL", "LATE_PARTIAL_TERMINAL",
)


def run():
    verify()
    cases = [generated_case(name) for name in NAMES]
    return dict(status="SYNTHETIC_MECHANISM_TEST_ONLY_NOT_HISTORICAL_GO",
                historical_wallets=0, market_reads=0, downloads=0,
                higher_risk_stage="H090_ISOLATED1X", actual_leverage=1,
                financial_account_methods_unchanged=True,
                scenario_cases=cases, finite_program=generated_finite_program(),
                real_world_ruin_probability="NOT_ESTIMATED",
                real_world_liquidation_probability="NOT_ESTIMATED",
                long_term_APR="NOT_EVALUABLE", native_scheduler_adapter="NOT_IMPLEMENTED",
                ai_predictive_model="NOT_IMPLEMENTED_OR_VERIFIED")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 1:
        raise SystemExit("No historical data path or run arguments are supported")
    print(json.dumps(run(), indent=2, sort_keys=True))

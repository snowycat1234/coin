"""Fixed generated fixtures only. No historical arguments accepted."""
import json
import sys
from decimal import Decimal
from grid_policy import CompletedClose, CompletedMinute, FixedGrid, MINUTE_US, compose_target
from risk_gate import assess_intent_envelope, certify_risk_match, path_metrics


def generated_closes(decision):
    return [CompletedClose(decision-(29-i)*1440*MINUTE_US,
                           Decimal(90 if i%2 == 0 else 110),
                           decision-(29-i)*1440*MINUTE_US) for i in range(30)]


def observation(price,clock):
    return CompletedMinute(clock,Decimal(str(price)),clock)


def main():
    if len(sys.argv) != 1:
        raise SystemExit("synthetic-only demo accepts no data/source/history arguments")
    t = 100*1440*MINUTE_US
    grid = FixedGrid(generated_closes(t),t,observation(100,t),200)
    fills=[]
    for n,price in enumerate((100,95,100,105,110,105,95,90,60)):
        clock=t+n*2*MINUTE_US
        for intent in grid.intents(clock,observation(price,clock)):
            # Generated fill callback demonstrates state transitions ONLY.
            # Price touches are not venue fills, and this callback isn't an engine.
            grid.on_fill(intent.slot,intent.quantity,intent.not_before_us,
                         order_id=intent.order_id,side=intent.side,fill_id=intent.order_id+":fill")
            fills.append({"side":intent.side,"qty":str(intent.quantity),"toy_price":price})
    q=grid.inventory()
    # Independent toy cash/inventory identity, not a margin-account simulator:
    # a profitable 90->95 closed grid cycle cannot hide a remaining 100->60 loss.
    cycle_cash=95-90
    floating=60-100
    accounting_counterexample={"closed_cycle_gain":cycle_cash,
                               "floating_inventory_pnl":floating,
                               "total_pnl":cycle_cash+floating,
                               "classification":"TOY_IDENTITY_NOT_PERFORMANCE"}
    cov=tuple(tuple(.04 if i==j else 0. for j in range(5)) for i in range(5))
    base=(.2,.1,-.1,0.,0.)
    retained=((.18,.1,-.1,0.,0.),)
    risk=assess_intent_envelope(original_weights=base,retained_legs=retained,
        grid_owned_weight=(0.,)*5,grid_unfilled_buy_weight=(.02,0.,0.,0.,0.),
        annual_covariance=cov,previous_quote_volume=(1e6,)*5,
        requested_notional=(200.,0.,0.,0.,0.),free_cash=6000.,reserved_cash=201.,valuation_nav=10000.)
    fake={"evidence_origin":"SYNTHETIC_FIXTURE", "complete_calendar":True,"paid_flat":True}
    print(json.dumps({"candidate":"CSH_BTC_GRID_REPLACE10","stage":"SYNTHETIC_ONLY",
        "historical_wallets":0,"ai_algorithm_reproduced":False,
        "grid_qty_per_slot":str(grid.quantity),"owned_after_out_of_range":str(q),
        "terminal_expiry_owned_not_free_cleared":str(grid.expire(grid.last_clock)),
        "toy_fill_callbacks":fills,"accounting_counterexample":accounting_counterexample,
        "intent_envelope":risk.__dict__,
        "generated_daily_metrics":path_metrics([10000.+10*i-30*(i%4) for i in range(40)]),
        "risk_certification":certify_risk_match(fake,fake)},indent=2))


if __name__ == "__main__":
    main()

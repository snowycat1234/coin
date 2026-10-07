"""Hand-calculated checks for the new read-only diagnosis, no old reruns."""
from decimal import Decimal
from scripts.research.diagnose_short_routing import journal_bridge

def leg(before, after, price, stamp):
    fields = dict(quantity_before=str(before), quantity_after=str(after),
        position_delta=str(Decimal(str(after))-Decimal(str(before))),
        mid_price=str(price), fill_price=str(price), fee_amount='0', execution_cost='0')
    return dict(event_us=stamp, leg='OPEN' if before == 0 else 'CLOSE', decimal_strings=fields)

def funding(stamp, quantity, rate, amount):
    return dict(event_us=stamp, quantity=quantity, signed_funding_USDT=amount,
        raw_rate=rate, assumed_fraction_decimal=str(rate), mark_close_us=stamp-1,
        decimal_strings=dict(quantity=str(quantity),mark_price='100',rate_fraction=str(rate),signed_funding_USDT=str(amount)))

def test_short_profit_loss_and_partial_close():
    for price, expected in ((90,10),(110,-10)):
        totals, episodes = journal_bridge([leg(0,-1,100,1),leg(-1,0,price,3)],[], 'RAW_AS_FRACTION','BASE27')
        assert totals['SHORT']['net'] == expected and len(episodes) == 1
    totals, episodes = journal_bridge([leg(0,-1,100,1),leg(-1,-.5,90,2),leg(-.5,0,90,3)],[], 'RAW_AS_FRACTION','BASE27')
    assert totals['SHORT']['net'] == 10 and len(episodes) == 1

def test_funding_cash_sign_and_same_time_ownership():
    trades = [leg(0,-1,100,1),leg(-1,0,90,3)]
    for rate, cash in ((.01,1),(-.01,-1)):
        totals, episodes = journal_bridge(trades,[funding(2,-1,rate,cash)],'RAW_AS_FRACTION','BASE27')
        assert totals['SHORT']['net'] == 10+cash and episodes[0]['funding'] == cash
    totals, episodes = journal_bridge(trades,[funding(1,0,.01,0),funding(3,-1,.01,1)],'RAW_AS_FRACTION','BASE27')
    assert totals['SHORT']['net'] == 11 and episodes[0]['funding'] == 1

def test_equal_family_prior_cannot_short_but_dynamic_weights_can():
    hold=.3; trends=[-.3]*6
    assert abs(hold/3+sum(trends)/18) < 1e-14
    assert .8*trends[0]+.2*hold < 0  # No such theorem for dynamic weights.

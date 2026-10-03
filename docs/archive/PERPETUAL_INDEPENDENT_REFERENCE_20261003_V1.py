"""UNRUN independent Decimal hand-ledger primitives for a linear USDT contract.

No producer import, market IO, strategy, order API, financial replay or claimed
margin/fee/funding certification.  Inputs are explicit synthetic strings.
Wallet includes committed margin; margin reservation is NOT spent principal.
The eventual production contract must separately pin timing, margin mode,
parameters, source/fee units, capacity, risk and failure semantics.
"""
from dataclasses import dataclass, field
from decimal import Decimal, localcontext


def dec(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not an amount')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Finite explicit synthetic amount required')
    return result


def sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


@dataclass
class HandLedger:
    """Single signed base-quantity position, quote wallet, weighted entry fill."""
    wallet: Decimal
    quantity: Decimal = Decimal(0)
    entry_fill: Decimal = Decimal(0)
    realized: Decimal = Decimal(0)
    fees: Decimal = Decimal(0)
    funding_cash: Decimal = Decimal(0)
    fills: list = field(default_factory=list)

    def fill(self, signed_delta, price, fee_fraction):
        change, price, rate = map(dec, (signed_delta, price, fee_fraction))
        if change == 0 or price <= 0 or not 0 <= rate < 1:
            raise ValueError('Nonzero signed fill, positive price, explicit fee fraction')
        with localcontext() as context:
            context.prec = 50
            old_q, old_entry = self.quantity, self.entry_fill
            closed = min(abs(old_q), abs(change)) if sign(old_q) * sign(change) < 0 else Decimal(0)
            realized = closed * sign(old_q) * (price - old_entry)
            fee = abs(change) * price * rate
            new_q = old_q + change
            if not new_q:
                new_entry = Decimal(0)
            elif not old_q or sign(new_q) != sign(old_q):
                new_entry = price  # A flip opens only the residual at this fill.
            elif sign(change) == sign(old_q):
                new_entry = (abs(old_q) * old_entry + abs(change) * price) / abs(new_q)
            else:
                new_entry = old_entry  # Partial close never re-bases the remainder.
            # No +/- trade notional in a linear derivative quote wallet.
            self.wallet += realized - fee
            self.quantity, self.entry_fill = new_q, new_entry
            self.realized += realized
            self.fees += fee
            row = dict(old_quantity=old_q, signed_delta=change, new_quantity=new_q,
                closing_quantity=closed, realized_PnL=realized, fee=fee,
                new_entry_fill=new_entry, wallet=self.wallet)
            self.fills.append(row)
            return row

    def funding(self, mark, rate_fraction, *, rate_unit, signed_quantity_before_event):
        if rate_unit != 'EXPLICIT_SYNTHETIC_FRACTION':
            raise ValueError('This hand example does not certify any real funding unit')
        mark, rate, owned_q = map(dec, (mark, rate_fraction, signed_quantity_before_event))
        if mark <= 0 or owned_q != self.quantity:
            raise ValueError('Positive synthetic mark and exact event-owned signed position')
        amount = -owned_q * mark * rate
        self.wallet += amount
        self.funding_cash += amount
        return amount

    def unrealized(self, mark):
        mark = dec(mark)
        if mark <= 0:
            raise ValueError('Positive valuation mark')
        return self.quantity * (mark - self.entry_fill)

    def equity(self, mark):
        return self.wallet + self.unrealized(mark)

    def bridge(self, initial_wallet, mark):
        # Actual fills already embed spread/slippage; do NOT debit those again.
        expected = dec(initial_wallet) + self.realized + self.unrealized(mark) + self.funding_cash - self.fees
        return self.equity(mark) - expected


# Hand-derived numbers, not values returned by a producer or a market replay.
# The fee fraction below is a declared synthetic 0.00055; it is not proof of
# the account's actual fee rate or the historical fee table.
HAND_EXPECTED = {
    'SHORT': dict(initial='1000', entry_delta='-1', entry_fill='99',
        wallet_after_entry='999.94555', mark='90', equity_before_funding='1008.94555',
        funding_fraction='0.001', funding_cash='0.09', equity_after_funding='1009.03555',
        exit_delta='1', exit_fill='91', realized='8', fees='0.10450', final_equity='1007.98550'),
    'LONG': dict(initial='1000', entry_delta='1', entry_fill='101',
        wallet_after_entry='999.94445', mark='90', equity_before_funding='988.94445',
        funding_fraction='0.001', funding_cash='-0.09', equity_after_funding='988.85445',
        exit_delta='-1', exit_fill='89', realized='-12', fees='0.10450', final_equity='987.80550'),
    'FLIP': dict(initial='1000', initial_short_delta='-1', initial_fill='100', fee_fraction='0.0005',
        opposite_fill_delta='2', opposite_fill='110', closing_quantity='1', realized='-10',
        remaining_quantity='1', remaining_entry_fill='110', wallet_after_flip='989.84',
        final_mark='120', equity_after_flip='999.84'),
}


def hand_reference_checks():
    """Future authorized synthetic-only call; not executed during preparation."""
    for name in ('SHORT', 'LONG'):
        expected = HAND_EXPECTED[name]
        ledger = HandLedger(dec(expected['initial']))
        ledger.fill(expected['entry_delta'], expected['entry_fill'], '0.00055')
        assert ledger.wallet == dec(expected['wallet_after_entry'])
        assert ledger.equity(expected['mark']) == dec(expected['equity_before_funding'])
        funded = ledger.funding(expected['mark'], expected['funding_fraction'],
            rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=ledger.quantity)
        assert funded == dec(expected['funding_cash'])
        assert ledger.equity(expected['mark']) == dec(expected['equity_after_funding'])
        ledger.fill(expected['exit_delta'], expected['exit_fill'], '0.00055')
        assert ledger.realized == dec(expected['realized']) and ledger.fees == dec(expected['fees'])
        assert ledger.quantity == 0 and ledger.wallet == dec(expected['final_equity'])
        assert ledger.bridge(expected['initial'], expected['mark']) == 0
    expected = HAND_EXPECTED['FLIP']
    ledger = HandLedger(dec(expected['initial']))
    ledger.fill(expected['initial_short_delta'], expected['initial_fill'], expected['fee_fraction'])
    row = ledger.fill(expected['opposite_fill_delta'], expected['opposite_fill'], expected['fee_fraction'])
    for key in ('closing_quantity',):
        assert row[key] == dec(expected[key])
    assert ledger.realized == dec(expected['realized'])
    assert ledger.quantity == dec(expected['remaining_quantity'])
    assert ledger.entry_fill == dec(expected['remaining_entry_fill'])
    assert ledger.wallet == dec(expected['wallet_after_flip'])
    assert ledger.equity(expected['final_mark']) == dec(expected['equity_after_flip'])
    assert ledger.bridge(expected['initial'], expected['final_mark']) == 0
    return {'scope': 'SYNTHETIC_LINEAR_QUOTE_WALLET_ONLY_NOT_EXECUTION_OR_MARGIN_CERTIFICATION',
            'hand_cases': ['SHORT', 'LONG', 'FLIP'], 'market_inputs_read': False}

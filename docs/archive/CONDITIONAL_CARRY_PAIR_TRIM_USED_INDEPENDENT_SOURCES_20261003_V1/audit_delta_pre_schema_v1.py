"""Unexecuted pair-trim audit delta; final schema/entry waits for protocol and actual0.

Reuse the accepted independent checker, not the account simulator. This draft
contains only the changed transaction/ownership invariants; it does not read
prices, invoke the old checker main, run an audit, or claim acceptance.
"""
import hashlib, importlib.util
from pathlib import Path
CORE_PATH=Path('/mnt/d/codex/coin/docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py')


def load_primitives(expected_sha256):
    actual=hashlib.sha256(CORE_PATH.read_bytes()).hexdigest()
    if actual!=expected_sha256:raise AssertionError('Accepted independent primitives changed')
    spec=importlib.util.spec_from_file_location('accepted_carry_decimal_core',CORE_PATH)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    return core  # Its __main__ entry is never called.


def frozen_keep(core,signal_nav,signal_spot,signal_mark,held_quantity):
    """Freeze from actually available signal observations, never execution prices."""
    nav,spot,mark=(core.number(v) for v in (signal_nav,signal_spot,signal_mark))
    core.need(nav>0 and spot>0 and mark>0 and held_quantity>0,'Positive available signal state')
    keep=min(held_quantity,core.D('.25')*nav/(spot+mark))
    core.need(0<keep<=held_quantity,'No enlargement or negative signal-frozen inventory')
    return keep


def eligible_quantity(core,stamp,entry_us,hard_exit_us,current_quantity,pending_trim=None):
    """Continuing slice keeps original entry ownership; closing slice excluded at tie.

    pending_trim contains execution_us and frozen_keep for this symbol only.
    The protocol must bind this precise tie rule before account execution.
    Events keep their original integer microsecond timestamp without jitter fixes.
    """
    if not entry_us<stamp<hard_exit_us:return core.ZERO
    if pending_trim is not None and stamp==pending_trim['execution_us']:
        return min(current_quantity,pending_trim['frozen_keep'])
    return current_quantity


def wallet_class(core):
    class PartialWallet(core.Wallet):
        def apply_partial_close(self,row,original_mid,expected_closed_quantity):
            """Independent fee/PnL math; keep original entry fill and remaining reserve."""
            s=row['symbol'];product=row['product'];side=row['side'];p=self.p[s]
            core.need((product,side) in (('SPOT','sell'),('PERP','buy')),'Only matched pair reductions')
            quantity=core.number(row['gross_quantity']);mid=core.number(original_mid)
            core.close(row['gross_quantity'],expected_closed_quantity,core.QTY_TOL)
            inventory=p['spot'] if product=='SPOT' else p['short']
            core.need(0<quantity<inventory,'Partial close leaves strictly positive inventory')
            expectation=core.expected_fill(s,product,side,quantity,mid)
            core.close(row['cash_before'],self.cash)
            for key,value in expectation.items():
                if key=='fee_asset':core.need(row[key]==value,'Received-asset fee denomination differs')
                else:core.close(row[key],value,core.QTY_TOL if key=='base_position_delta' else core.USDT_TOL)
            core.close(row['mid_proxy'],mid)
            old_entry,old_margin=p['entry'],p['margin']
            fee_free=fee_margin=realized=realized_free=realized_margin=core.ZERO
            if product=='SPOT':
                p['spot']-=quantity;self.cash+=expectation['spot_quote_delta']
                core.need(p['spot']>0,'No dust-zero reset for partial Spot sale')
            else:
                fee_free,fee_margin=self.debit(s,expectation['fee_USDT'])
                realized=quantity*(old_entry-expectation['fill_price'])
                if realized>=0:self.cash+=realized
                else:realized_free,realized_margin=self.debit(s,-realized)
                p['short']-=quantity
                core.need(p['short']>0 and p['entry']==old_entry,'Surviving short entry cannot be reseeded')
            core.need(self.cash>=0,'No implicit negative-cash borrowing')
            core.need(p['margin']==old_margin-fee_margin-realized_margin,
                      'No proportional reserve release/reset; only actual own-margin debits')
            self.fees+=expectation['fee_USDT'];self.spread+=expectation['spread_USDT']
            self.slippage+=expectation['slippage_USDT'];self.turnover+=quantity*mid/core.CAPITAL
            expected=dict(cash_after=self.cash,perp_realized_PnL_USDT=realized,
                fee_free_cash_debit=fee_free,fee_isolated_balance_debit=fee_margin,
                realized_free_cash_debit=realized_free,realized_isolated_balance_debit=realized_margin)
            for key,value in expected.items():core.close(row[key],value)
            core.need(row['no_short_sale_proceeds'] is True and row['fractional_quantity_proxy'] is True,
                      'No short-sale proceeds or native venue-filter proof')

        def apply_owned_funding_slice(self,row,original_rate,past_mark,eligible_q):
            """No inventory change on cash settlement; eligible_q is independently causal."""
            s=row['symbol'];core.need(core.ZERO<=eligible_q<=self.p[s]['short'],'Eligible funding slice bounds')
            core.close(row['raw_rate'],core.number(original_rate),core.QTY_TOL)
            amount=eligible_q*core.number(past_mark)*core.number(original_rate) if eligible_q else core.ZERO
            free=margin=core.ZERO
            if amount>=0:self.cash+=amount
            else:free,margin=self.debit(s,-amount)
            self.funding+=amount;core.need(self.cash>=0,'No negative cash funding debit')
            for key,value in [('signed_funding_USDT',amount),('free_cash_debit',free),
                ('isolated_balance_debit',margin),('cumulative_funding_USDT',self.funding)]:core.close(row[key],value)
            core.need(row['funding_unit_certified'] is False and row['charge_mark_or_native_settlement_certified'] is False,
                      'Conditional slice math is not native unit/availability proof')
    return PartialWallet


if __name__=='__main__':
    raise SystemExit('PREPARED_UNRUN_DELTA: final schema and actual0 required; no audit executed')
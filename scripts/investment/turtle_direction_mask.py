"""Direction and proactive ADD permission over the shared Turtle state bridge.

Allowed entry predicates call the original hooks; disabling long never creates
a short signal. Original exits, protective stops and reduce-only dispatch stay
active even for inventory whose direction is not permitted to increase. This
is a direction ablation, not another Turtle rule or financial account.
"""
from __future__ import annotations

from functools import partial
from types import MethodType

from scripts.investment import turtle_perpetual_bridge as original
from scripts.investment import perpetual_closing_exempt_account as closing

VERSION = 'TURTLE_CONFIGURED_DIRECTION_PERMISSION_BRIDGE_V2'
MODES = ('LONG_ONLY', 'SHORT_ONLY', 'LONG_SHORT', 'CASH')
STRATEGY_ID = 'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'
RULES = dict(mode_permission_only=True, mirrored_short_signal=False,
    allowed_entry_hooks='ORIGINAL_SHOULD_LONG_OR_SHOULD_SHORT_AND_FIXED_MODE_PERMISSION',
    held_update='ORIGINAL_UPDATE_POSITION_THEN_DISCARD_ONLY_PROHIBITED_INCREASE',
    exits_stops_risk_terminal_callbacks_unchanged=True,
    reduce_existing_inventory_allowed_in_all_modes=True,
    snapshot_mode_identity_required=True, new_financial_account_body=False,
    account_filter_profile_id=closing.FILTER_PROFILE_ID)


def _allowed(mode, side):
    return mode == 'LONG_SHORT' or mode == 'LONG_ONLY' and side == 'BUY' or mode == 'SHORT_ONLY' and side == 'SELL'


class TurtlePerpetualBridge(original.TurtlePerpetualBridge):
    def __init__(self, account, mode='LONG_SHORT', *, allow_pyramiding=True, _restoring=False):
        original.require(mode in MODES and isinstance(account, closing.USDTLinearPerpetualAccount)
            and account.contract_metadata()['filter_profile_id'] == closing.FILTER_PROFILE_ID
            and account.contract_metadata()['closing_min_notional_exempt'] is True,
            'Declared direction mode and exact conditional closing account profile')
        self._direction_mode = mode
        super().__init__(account, allow_pyramiding=allow_pyramiding, _restoring=_restoring)
        for obj in self.rules.values():
            raw_class = type(obj)

            def should_long(rule, raw=raw_class, permission=mode):
                return _allowed(permission, 'BUY') and bool(raw.should_long(rule))

            def should_short(rule, raw=raw_class, permission=mode):
                return _allowed(permission, 'SELL') and bool(raw.should_short(rule))

            def update_position(rule, raw=raw_class, permission=mode):
                result = raw.update_position(rule)
                if not _allowed(permission, 'BUY'):
                    rule.buy = None
                if not _allowed(permission, 'SELL'):
                    rule.sell = None
                return result

            obj.should_long = MethodType(should_long, obj)
            obj.should_short = MethodType(should_short, obj)
            obj.update_position = MethodType(update_position, obj)
        self.source_receipt = dict(self.source_receipt, direction_mask=dict(version=VERSION, mode=mode, rules=RULES))

    @property
    def direction_mode(self):
        return self._direction_mode

    def _new(self, symbol, side, quantity, signal, kind, **kwargs):
        original.require(symbol in self.symbols and kind in original.KINDS and side in ('BUY', 'SELL')
            and original.decimal(quantity) > 0, 'Known positive original intent')
        if kind in ('ENTRY', 'ADD') and not _allowed(self.direction_mode, side):
            self.journal.append(dict(event='DIRECTION_MASK_BLOCKED_INCREASE', mode=self.direction_mode,
                symbol=symbol, side=side, kind=kind, signal_us=original.timestamp(signal)))
            return None
        return super()._new(symbol, side, quantity, signal, kind, **kwargs)

    def targets_frame(self):
        return super().targets_frame().with_columns(original.pl.lit(self.direction_mode).alias('mode'))

    def meta(self):
        value = super().meta()
        value.update(strategy_id=STRATEGY_ID, direction_mode=self.direction_mode,
            direction_mask_version=VERSION, direction_mask_rules=RULES,
            original_raw_entry_exit_and_callback_hooks_used=True,
            only_prohibited_new_direction_increases_masked=True,
            proactive_ADD_permission=self.allow_pyramiding)
        return value

    def snapshot(self):
        return dict(version=VERSION, direction_mode=self.direction_mode,
            allow_pyramiding=self.allow_pyramiding,
            account_filter_profile_id=closing.FILTER_PROFILE_ID, bridge=super().snapshot())

    @classmethod
    def from_snapshot(cls, account, snapshot, *, mode, allow_pyramiding=True):
        original.require(set(snapshot) == {'version', 'direction_mode', 'allow_pyramiding', 'account_filter_profile_id', 'bridge'}
            and snapshot['version'] == VERSION and mode in MODES and snapshot['direction_mode'] == mode
            and type(allow_pyramiding) is bool and snapshot['allow_pyramiding'] is allow_pyramiding
            and snapshot['account_filter_profile_id'] == closing.FILTER_PROFILE_ID,
            'Snapshot direction/version/account-profile mismatch')
        # Reuse every original receipt, callback, protection and dedup check.
        # The constructor factory supplies the explicit mode to the unchanged
        # classmethod body; it returns an instance of this class, not a clone.
        factory = partial(cls, mode=mode)
        result = original.TurtlePerpetualBridge.from_snapshot.__func__(factory, account,
            snapshot['bridge'], allow_pyramiding=allow_pyramiding)
        for intent in result.intents.values():
            original.require(intent['kind'] in original.REDUCING or _allowed(mode, intent['side']),
                'Snapshot contains historical or active increases prohibited by this mode')
        return result

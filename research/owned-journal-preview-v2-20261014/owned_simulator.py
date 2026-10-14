"""Explicit generated simulator variant; no native/historical identity override."""
from native_control import NATIVE
from owned_journals import OwnedFineGridAccount,admit_owned_account,fork_owned_account,export_tree,JOURNAL_MAPS


class OwnedNativeSimulator(NATIVE):
    """Native scheduler plus explicit owned-journal initialization/serialization."""
    def __init__(self,*args,generated_only=False,**kwargs):
        if generated_only is not True:raise ValueError('GENERATED_ONLY_OWNED_SIMULATOR_REQUIRED')
        if 'account_factory' in kwargs:raise ValueError('OWNED_FACTORY_IS_EXPLICIT_VARIANT_IDENTITY')
        super().__init__(*args,account_factory=OwnedFineGridAccount,**kwargs)
    def _bare_checkpoint_boundary(self):
        if 'schedule' in vars(self) or 'attempt' in vars(self):
            raise RuntimeError('UNINSTALL_ADAPTER_BEFORE_NATIVE_FORK_OR_STATE_HASH')
    def fork(self):
        self._bare_checkpoint_boundary()
        return super().fork()
    def state_hash(self):
        self._bare_checkpoint_boundary()
        # The original state_hash accepts exact dict/list protocols. Adapt only
        # an independent serialization shadow, never replace the live journals.
        # This explicit checkpoint operation remains O(history), outside guards.
        shadow=object.__new__(NATIVE);vars(shadow).update(vars(self))
        shadow.account=fork_owned_account(self.account)
        for name in JOURNAL_MAPS:object.__setattr__(shadow.account,name,export_tree(getattr(shadow.account,name)))
        return NATIVE.state_hash(shadow)
    @classmethod
    def from_snapshot(cls,snapshot,window,*,generated_only=False,**kwargs):
        if generated_only is not True:raise ValueError('GENERATED_ONLY_OWNED_RECOVERY_REQUIRED')
        native=NATIVE.from_snapshot(snapshot,window,account_class=OwnedFineGridAccount)
        result=object.__new__(cls);vars(result).update(vars(native));result._bind_callback();return result

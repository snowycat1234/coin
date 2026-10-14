"""Exact charged previews over explicitly owned generated live journals.

The public account snapshot API always exports full native containers. Only this
private proxy supplies exact immutable-root tokens to unchanged frozen preview
assertions. Returned charged probes are unwrapped real owned accounts.
"""
from copy import deepcopy
from native_preview import ChargedPreview
from causal_adapter import FreshExecutionPreview
from owned_journals import OwnedFineGridAccount,fork_owned_account


class _TokenView:
    __slots__=('__dict__',)
    def __init__(self,owned):
        if type(owned) is not OwnedFineGridAccount:raise TypeError('EXPLICIT_OWNED_ACCOUNT_REQUIRED')
        owned.preview_state_token();self._owned=owned
    def __getattr__(self,name):return getattr(object.__getattribute__(self,'_owned'),name)
    def __deepcopy__(self,memo):
        result=object.__new__(type(self));memo[id(self)]=result
        result._owned=fork_owned_account(self._owned,memo=memo);return result
    def snapshot(self):return self._owned.preview_state_token()


class BoundedChargedPreview(ChargedPreview):
    def __init__(self,account,**kwargs):super().__init__(_TokenView(account),**kwargs)
    def _charged(self,target,tag):
        probe,witness=super()._charged(target,tag)
        return (probe._owned if probe is not None else None),witness


class BoundedFreshExecutionPreview(FreshExecutionPreview):
    def __init__(self,account,**kwargs):super().__init__(_TokenView(account),**kwargs)
    def _charged(self,target,tag):
        probe,witness=super()._charged(target,tag)
        return (probe._owned if probe is not None else None),witness

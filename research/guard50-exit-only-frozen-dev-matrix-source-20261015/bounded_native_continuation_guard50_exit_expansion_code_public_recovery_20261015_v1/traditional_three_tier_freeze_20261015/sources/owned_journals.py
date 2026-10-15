"""Explicit generated-only persistent journal ownership, not a native drop-in.

Immutable AVL roots provide O(log n) append/identity lookup and O(1) forks.
Native financial methods are inherited. Full snapshots remain plain native
containers; compact exact tokens are a distinct internal guard API.
"""
from collections.abc import Mapping, MutableMapping, MutableSequence
from copy import deepcopy
from dataclasses import dataclass
from itertools import chain
from decimal import Decimal
from types import MappingProxyType

from fine_account import FineGridAccount
from shared_journal_preview import (_FrozenMap, _FrozenList, _deny,
    UnsupportedJournalMutation, JOURNAL_LISTS, JOURNAL_MAPS, JOURNALS, _NATIVE_FIELDS)


def _freeze_owned(value,active=None):
    """Commit detached safe values, including forged mutable-backed wrappers."""
    if type(value) in (type(None),bool,int,float,str,Decimal):return value
    if active is None:active=set()
    if id(value) in active:raise TypeError('CYCLIC_OWNED_JOURNAL_GRAPH_UNSUPPORTED')
    active.add(id(value))
    try:
        if type(value) in (dict,_FrozenMap):
            if type(value) is _FrozenMap and type(value._data) not in (dict,MappingProxyType):
                raise TypeError('UNSUPPORTED_FROZEN_MAPPING_BACKING')
            if any(type(key) is not str for key in value):raise TypeError('NATIVE_STRING_JOURNAL_KEYS_REQUIRED')
            return _FrozenMap(MappingProxyType({key:_freeze_owned(item,active) for key,item in value.items()}))
        if type(value) in (list,_FrozenList):
            if type(value) is _FrozenList and type(value._items) not in (list,tuple):
                raise TypeError('UNSUPPORTED_FROZEN_SEQUENCE_BACKING')
            return _FrozenList(tuple(_freeze_owned(item,active) for item in value))
        raise TypeError('UNSUPPORTED_OWNED_JOURNAL_VALUE:'+type(value).__name__)
    finally:active.remove(id(value))


@dataclass(frozen=True, eq=False, slots=True)
class _Node:
    key: object
    value: object
    left: object = None
    right: object = None
    height: int = 1


def _height(node): return 0 if node is None else node.height

def _node(key,value,left=None,right=None):
    return _Node(key,value,left,right,max(_height(left),_height(right))+1)

def _right(node):
    left=node.left
    return _node(left.key,left.value,left.left,_node(node.key,node.value,left.right,node.right))

def _left(node):
    right=node.right
    return _node(right.key,right.value,_node(node.key,node.value,node.left,right.left),right.right)

def _put(node,key,value):
    if node is None:return _Node(key,value)
    if key==node.key:raise UnsupportedJournalMutation('PERSISTENT_IDENTITY_OVERWRITE_FORBIDDEN')
    if key<node.key:result=_node(node.key,node.value,_put(node.left,key,value),node.right)
    else:result=_node(node.key,node.value,node.left,_put(node.right,key,value))
    balance=_height(result.left)-_height(result.right)
    if balance>1:
        if key>result.left.key:result=_node(result.key,result.value,_left(result.left),result.right)
        return _right(result)
    if balance < -1:
        if key<result.right.key:result=_node(result.key,result.value,result.left,_right(result.right))
        return _left(result)
    return result

def _get(node,key):
    while node is not None:
        if key==node.key:return node.value
        node=node.left if key<node.key else node.right
    raise KeyError(key)

def _values(node):
    stack=[]
    while stack or node is not None:
        while node is not None:stack.append(node);node=node.left
        node=stack.pop();yield node.value;node=node.right


def export_tree(value,memo=None):
    """Ordinary mutable native snapshot/receipt export, deliberately O(history)."""
    if type(value) in (type(None),bool,int,float,str,Decimal):return value
    if memo is None:memo={}
    if id(value) in memo:return memo[id(value)]
    if isinstance(value,Mapping):
        result={};memo[id(value)]=result
        for key,item in value.items():result[key]=export_tree(item,memo)
        return result
    if isinstance(value,(list,_FrozenList,PersistentList)):
        result=[];memo[id(value)]=result
        result.extend(export_tree(item,memo) for item in value);return result
    return deepcopy(value,memo)


class PersistentList(MutableSequence):
    __slots__=('_root','_size')
    def __init__(self,values=()):
        self._root=None;self._size=0
        for value in values:self.append(value)
    def fork(self):
        result=object.__new__(type(self));result._root=self._root;result._size=self._size;return result
    def token(self):return (self._root,self._size)
    def __deepcopy__(self,memo):
        result=self.fork();memo[id(self)]=result;return result
    def __len__(self):return self._size
    def __iter__(self):return _values(self._root)
    def __getitem__(self,index):
        if isinstance(index,slice):return [export_tree(self[i]) for i in range(*index.indices(len(self)))]
        if not isinstance(index,int):raise TypeError('integer or slice required')
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        return _get(self._root,index)
    def append(self,value):
        frozen=_freeze_owned(value);self._root=_put(self._root,self._size,frozen);self._size+=1
    def extend(self,values):
        for value in tuple(values) if values is self else values:self.append(value)
    def insert(self,index,value):
        if index<len(self):_deny()
        self.append(value)
    def __eq__(self,other):
        if self is other:return True
        if not isinstance(other,(list,tuple,_FrozenList,PersistentList)):return False
        if len(self)!=len(other):return False
        if isinstance(other,PersistentList) and self._root is other._root:return True
        return all(a==b for a,b in zip(self,other))
    def __add__(self,other):
        if not isinstance(other,(list,PersistentList)):return NotImplemented
        return export_tree(self)+export_tree(other)
    def __radd__(self,other):
        if not isinstance(other,list):return NotImplemented
        return export_tree(other)+export_tree(self)
    def __iadd__(self,other):self.extend(other);return self
    def copy(self):return export_tree(self)
    __setitem__=__delitem__=clear=pop=remove=reverse=sort=__imul__=_deny


class PersistentMap(MutableMapping):
    __slots__=('_root','_order','_size')
    def __init__(self,values=()):
        self._root=None;self._order=None;self._size=0
        for key,value in dict(values).items():self[key]=value
    def fork(self):
        result=object.__new__(type(self));result._root=self._root;result._order=self._order;result._size=self._size;return result
    def token(self):return (self._root,self._order,self._size)
    def __deepcopy__(self,memo):
        result=self.fork();memo[id(self)]=result;return result
    def __len__(self):return self._size
    def __iter__(self):return (key for key,value in _values(self._order))
    def items(self):return _values(self._order)
    def values(self):return (value for key,value in _values(self._order))
    def __getitem__(self,key):return _get(self._root,key)
    def __setitem__(self,key,value):
        if type(key) is not str:raise TypeError('NATIVE_STRING_JOURNAL_KEYS_REQUIRED')
        if key in self:_deny()
        frozen=_freeze_owned(value)
        root=_put(self._root,key,frozen);order=_put(self._order,self._size,(key,frozen))
        self._root=root;self._order=order;self._size+=1
    def __eq__(self,other):
        if self is other:return True
        if isinstance(other,PersistentMap) and self._root is other._root:return True
        return isinstance(other,Mapping) and len(self)==len(other) and all(k in other and v==other[k] for k,v in self.items())
    def copy(self):return export_tree(self)
    __delitem__=clear=pop=popitem=_deny


class OwnedFineGridAccount(FineGridAccount):
    """Explicit new generated live-container contract; original finance inherited."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name in JOURNAL_LISTS:object.__setattr__(self,name,PersistentList())
        for name in JOURNAL_MAPS:object.__setattr__(self,name,PersistentMap())
    def __setattr__(self,name,value):
        if name in JOURNALS and name in vars(self):
            raise UnsupportedJournalMutation('OWNED_JOURNAL_REPLACEMENT_FORBIDDEN_USE_VALIDATED_RECOVERY')
        object.__setattr__(self,name,value)
    def __delattr__(self,name):
        if name in JOURNALS:raise UnsupportedJournalMutation('OWNED_JOURNAL_DELETION_FORBIDDEN')
        object.__delattr__(self,name)
    def __deepcopy__(self,memo):return fork_owned_account(self,memo=memo)
    def snapshot(self):return export_tree(super().snapshot())
    def preview_state_token(self):
        """Exact finite-state copy + immutable roots, not a portable snapshot."""
        allowed=_NATIVE_FIELDS|{'execute_fill','liquidation_callback'}
        if set(vars(self))-allowed or not _NATIVE_FIELDS<=set(vars(self)):
            raise TypeError('EXACT_REVIEWED_OWNED_ACCOUNT_FIELDS_REQUIRED')
        if any(type(getattr(self,n)) is not PersistentList for n in JOURNAL_LISTS) or any(type(getattr(self,n)) is not PersistentMap for n in JOURNAL_MAPS):
            raise TypeError('PERMANENT_OWNED_JOURNALS_REQUIRED')
        # Invoke the unchanged native snapshot builder, whose journal deepcopy
        # calls now fork immutable roots. Keep every native finite field exactly,
        # including Decimal string representation and current contract metadata.
        state=FineGridAccount.snapshot(self)
        for name in JOURNALS:state[name]=getattr(self,name).token()
        return state
    @classmethod
    def from_snapshot(cls,snapshot,**kwargs):
        original=FineGridAccount.from_snapshot(snapshot,**kwargs)
        return admit_owned_account(original,generated_only=True)


def admit_owned_account(account,*,generated_only):
    if generated_only is not True:raise ValueError('GENERATED_ONLY_OWNERSHIP_ADMISSION_REQUIRED')
    if type(account) is not FineGridAccount:raise TypeError('EXACT_NATIVE_ACCOUNT_REQUIRED_AT_OWNERSHIP_BOUNDARY')
    if set(vars(account))-_NATIVE_FIELDS-{'execute_fill','liquidation_callback'}:raise TypeError('UNREVIEWED_ACCOUNT_FIELDS')
    result=object.__new__(OwnedFineGridAccount)
    memo={id(account.instrument_profiles):account.instrument_profiles}
    callback=getattr(account,'liquidation_callback',None)
    if callback is not None:memo[id(callback)]=None
    for name,value in vars(account).items():
        if name=='execute_fill':continue
        if name in JOURNAL_LISTS:copied=PersistentList(value)
        elif name in JOURNAL_MAPS:copied=PersistentMap(value)
        else:copied=deepcopy(value,memo)
        object.__setattr__(result,name,copied)
    result.preview_state_token()
    return result


def fork_owned_account(account,memo=None):
    if type(account) is not OwnedFineGridAccount:raise TypeError('EXACT_OWNED_ACCOUNT_REQUIRED')
    account.preview_state_token()  # Fails closed on unsupported fields/containers.
    if memo is None:memo={}
    result=object.__new__(OwnedFineGridAccount);memo[id(account)]=result
    memo[id(account.instrument_profiles)]=account.instrument_profiles
    callback=getattr(account,'liquidation_callback',None)
    if callback is not None:memo[id(callback)]=None
    for name,value in vars(account).items():
        if name=='execute_fill':continue
        object.__setattr__(result,name,deepcopy(value,memo))
    return result
